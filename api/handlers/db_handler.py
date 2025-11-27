"""
Database Handler
Manages PostgreSQL connections and data operations
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class DatabaseHandler:
    """Handles all database operations"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None
    ):
        """
        Initialize database connection

        Args:
            host: Database host (default from DB_HOST env var)
            port: Database port (default from DB_PORT env var)
            database: Database name (default from DB_NAME env var)
            user: Database user (default from DB_USER env var)
            password: Database password (default from DB_PASSWORD env var)
        """
        self.host = host or os.getenv('DB_HOST', 'localhost')
        self.port = port or int(os.getenv('DB_PORT', 5432))
        self.database = database or os.getenv('DB_NAME', 'crawling_chaos')
        self.user = user or os.getenv('DB_USER', 'postgres')
        self.password = password or os.getenv('DB_PASSWORD', 'postgres')

        self.conn = None

    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    # Job Management
    def create_job(self, job_config: Dict[str, Any]) -> Optional[int]:
        """Create a new job"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO jobs (
                        name, google_search_query, claude_sys_prompt,
                        claude_user_prompt, gpt_sys_prompt, gpt_user_prompt,
                        frequency_minutes, is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    job_config.get('name'),
                    job_config.get('google_search_query'),
                    job_config.get('claude_sys_prompt'),
                    job_config.get('claude_user_prompt'),
                    job_config.get('gpt_sys_prompt'),
                    job_config.get('gpt_user_prompt'),
                    job_config.get('frequency_minutes'),
                    job_config.get('is_active', True)
                ))
                job_id = cur.fetchone()[0]
                self.conn.commit()
                return job_id
        except Exception as e:
            print(f"Error creating job: {e}")
            self.conn.rollback()
            return None

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get all active jobs"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM jobs WHERE is_active = true
                    ORDER BY id
                """)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error fetching jobs: {e}")
            return []

    def update_job_last_run(self, job_id: int):
        """Update job's last run timestamp"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE jobs SET last_run = %s WHERE id = %s
                """, (datetime.utcnow(), job_id))
                self.conn.commit()
        except Exception as e:
            print(f"Error updating job: {e}")
            self.conn.rollback()

    # News Results
    def save_news_results(self, job_id: int, articles: List[Dict[str, Any]]) -> List[int]:
        """Save news articles to database"""
        article_ids = []
        try:
            with self.conn.cursor() as cur:
                for article in articles:
                    cur.execute("""
                        INSERT INTO news_results (
                            job_id, title, summary, url, publish_date, raw_data
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        job_id,
                        article.get('title'),
                        article.get('summary'),
                        article.get('url'),
                        article.get('publish_date'),
                        Json(article)
                    ))
                    article_ids.append(cur.fetchone()[0])
                self.conn.commit()
        except Exception as e:
            print(f"Error saving news results: {e}")
            self.conn.rollback()
        return article_ids

    # Claude Analysis
    def save_claude_analysis(
        self,
        job_id: int,
        news_result_id: int,
        analysis_text: str,
        raw_response: Dict[str, Any]
    ) -> Optional[int]:
        """Save Claude analysis"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO claude_analysis (
                        job_id, news_result_id, analysis_text, raw_response
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (job_id, news_result_id, analysis_text, Json(raw_response)))
                analysis_id = cur.fetchone()[0]
                self.conn.commit()
                return analysis_id
        except Exception as e:
            print(f"Error saving Claude analysis: {e}")
            self.conn.rollback()
            return None

    # GPT Analysis
    def save_gpt_analysis(
        self,
        job_id: int,
        news_result_id: int,
        analysis_text: str,
        raw_response: Dict[str, Any]
    ) -> Optional[int]:
        """Save GPT analysis"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO gpt_analysis (
                        job_id, news_result_id, analysis_text, raw_response
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (job_id, news_result_id, analysis_text, Json(raw_response)))
                analysis_id = cur.fetchone()[0]
                self.conn.commit()
                return analysis_id
        except Exception as e:
            print(f"Error saving GPT analysis: {e}")
            self.conn.rollback()
            return None

    # Data Retrieval for Frontend
    def get_latest_news_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest news results for frontend"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, title, summary, url, publish_date, collected_at
                    FROM news_results
                    ORDER BY collected_at DESC
                    LIMIT %s
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error fetching news results: {e}")
            return []

    def get_latest_claude_analysis(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest Claude analyses for frontend"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT ca.id, ca.news_result_id, ca.analysis_text,
                           ca.created_at, nr.title as news_title
                    FROM claude_analysis ca
                    JOIN news_results nr ON ca.news_result_id = nr.id
                    ORDER BY ca.created_at DESC
                    LIMIT %s
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error fetching Claude analysis: {e}")
            return []

    def get_latest_gpt_analysis(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest GPT analyses for frontend"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT ga.id, ga.news_result_id, ga.analysis_text,
                           ga.created_at, nr.title as news_title
                    FROM gpt_analysis ga
                    JOIN news_results nr ON ga.news_result_id = nr.id
                    ORDER BY ga.created_at DESC
                    LIMIT %s
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error fetching GPT analysis: {e}")
            return []


if __name__ == '__main__':
    # Test database connection
    with DatabaseHandler() as db:
        if db.conn:
            print("Database connection successful!")
            jobs = db.get_active_jobs()
            print(f"Found {len(jobs)} active jobs")
