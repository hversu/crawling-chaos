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
        """Create a new job (supports both template-based and legacy formats)"""
        try:
            with self.conn.cursor() as cur:
                # Check if this is a template-based job or legacy job
                if 'template' in job_config:
                    # Resolve depends_on_job_name to depends_on_job_id if provided
                    depends_on_job_id = job_config.get('depends_on_job_id')

                    if not depends_on_job_id and job_config.get('depends_on_job_name'):
                        parent_job_name = job_config.get('depends_on_job_name')
                        cur.execute("""
                            SELECT id FROM jobs WHERE name = %s LIMIT 1
                        """, (parent_job_name,))
                        result = cur.fetchone()
                        if result:
                            depends_on_job_id = result[0]
                            print(f"Resolved parent job '{parent_job_name}' to ID {depends_on_job_id}")
                        else:
                            print(f"WARNING: Parent job '{parent_job_name}' not found")

                    # New template-based job
                    cur.execute("""
                        INSERT INTO jobs (
                            name, template_name, parameters,
                            frequency_minutes, depends_on_job_id, is_active
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        job_config.get('name'),
                        job_config.get('template'),
                        Json(job_config.get('parameters', {})),
                        job_config.get('frequency_minutes'),
                        depends_on_job_id,
                        job_config.get('is_active', True)
                    ))
                else:
                    # Legacy job with embedded prompts
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

    def get_dependent_jobs(self, parent_job_id: int) -> List[Dict[str, Any]]:
        """Get all active jobs that depend on the specified parent job"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM jobs
                    WHERE is_active = true AND depends_on_job_id = %s
                    ORDER BY id
                """, (parent_job_id,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error fetching dependent jobs: {e}")
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

    # Collections (Generic storage for all collector types)
    def save_collection(self, job_id: int, collection_type: str, items: List[Dict[str, Any]]) -> List[int]:
        """Save collection items to database (news, serpapi, scraped pages, etc.)"""
        collection_ids = []
        try:
            with self.conn.cursor() as cur:
                for item in items:
                    cur.execute("""
                        INSERT INTO collections (
                            job_id, collection_type, data
                        ) VALUES (%s, %s, %s)
                        RETURNING id
                    """, (
                        job_id,
                        collection_type,
                        Json(item)
                    ))
                    collection_ids.append(cur.fetchone()[0])
                self.conn.commit()
        except Exception as e:
            print(f"Error saving collection ({collection_type}): {e}")
            self.conn.rollback()
        return collection_ids

    # Legacy method for backward compatibility
    def save_news_results(self, job_id: int, articles: List[Dict[str, Any]]) -> List[int]:
        """Save news articles (legacy wrapper around save_collection)"""
        return self.save_collection(job_id, 'news', articles)

    # Claude Analysis
    def save_claude_analysis(
        self,
        job_id: int,
        collection_id: int,
        analysis_text: str,
        raw_response: Dict[str, Any]
    ) -> Optional[int]:
        """Save Claude analysis"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO claude_analysis (
                        job_id, collection_id, analysis_text, raw_response
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (job_id, collection_id, analysis_text, Json(raw_response)))
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
        collection_id: int,
        analysis_text: str,
        raw_response: Dict[str, Any]
    ) -> Optional[int]:
        """Save GPT analysis"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO gpt_analysis (
                        job_id, collection_id, analysis_text, raw_response
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (job_id, collection_id, analysis_text, Json(raw_response)))
                analysis_id = cur.fetchone()[0]
                self.conn.commit()
                return analysis_id
        except Exception as e:
            print(f"Error saving GPT analysis: {e}")
            self.conn.rollback()
            return None

    # Data Retrieval for Frontend
    def get_latest_collections(self, collection_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest collections for frontend (optionally filtered by type)"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                if collection_type:
                    cur.execute("""
                        SELECT c.id, c.job_id, c.collection_type, c.data,
                               c.collected_at, j.name as job_name
                        FROM collections c
                        JOIN jobs j ON c.job_id = j.id
                        WHERE c.collection_type = %s
                        ORDER BY c.collected_at DESC
                        LIMIT %s
                    """, (collection_type, limit))
                else:
                    cur.execute("""
                        SELECT c.id, c.job_id, c.collection_type, c.data,
                               c.collected_at, j.name as job_name
                        FROM collections c
                        JOIN jobs j ON c.job_id = j.id
                        ORDER BY c.collected_at DESC
                        LIMIT %s
                    """, (limit,))

                results = []
                for row in cur.fetchall():
                    item = dict(row)
                    # Extract commonly used fields from JSONB for convenience
                    data = item.get('data', {})
                    if collection_type == 'news':
                        item['title'] = data.get('title')
                        item['summary'] = data.get('summary')
                        item['url'] = data.get('url')
                        item['publish_date'] = data.get('publish_date')
                    results.append(item)

                return results
        except Exception as e:
            print(f"Error fetching collections: {e}")
            return []

    # Legacy method for backward compatibility
    def get_latest_news_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest news results (legacy wrapper)"""
        return self.get_latest_collections(collection_type='news', limit=limit)

    def get_latest_claude_analysis(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest Claude analyses for frontend"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT ca.id, ca.job_id, ca.collection_id, ca.analysis_text,
                           ca.created_at, j.name as job_name
                    FROM claude_analysis ca
                    JOIN jobs j ON ca.job_id = j.id
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
                    SELECT ga.id, ga.job_id, ga.collection_id, ga.analysis_text,
                           ga.created_at, j.name as job_name
                    FROM gpt_analysis ga
                    JOIN jobs j ON ga.job_id = j.id
                    ORDER BY ga.created_at DESC
                    LIMIT %s
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error fetching GPT analysis: {e}")
            return []

    # Search Queries
    def save_search_queries(
        self,
        job_id: int,
        parent_analysis_id: int,
        queries: List[Dict[str, Any]],
        justification: str,
        raw_response: Dict[str, Any]
    ) -> Optional[int]:
        """Save search queries generated by Claude"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO search_queries (
                        job_id, parent_analysis_id, queries, justification, raw_response
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (job_id, parent_analysis_id, Json(queries), justification, Json(raw_response)))
                query_id = cur.fetchone()[0]
                self.conn.commit()
                return query_id
        except Exception as e:
            print(f"Error saving search queries: {e}")
            self.conn.rollback()
            return None

    def get_latest_search_queries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest search queries for frontend with parent analysis"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT sq.id, sq.job_id, sq.parent_analysis_id, sq.queries,
                           sq.justification, sq.created_at, j.name as job_name,
                           ca.analysis_text as parent_analysis_text,
                           ca.job_id as parent_job_id,
                           pj.name as parent_job_name
                    FROM search_queries sq
                    JOIN jobs j ON sq.job_id = j.id
                    LEFT JOIN claude_analysis ca ON sq.parent_analysis_id = ca.id
                    LEFT JOIN jobs pj ON ca.job_id = pj.id
                    ORDER BY sq.created_at DESC
                    LIMIT %s
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error fetching search queries: {e}")
            return []

    def get_latest_claude_analysis_by_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recent Claude analysis for a specific job"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT ca.id, ca.job_id, ca.collection_id, ca.analysis_text,
                           ca.raw_response, ca.created_at, j.name as job_name
                    FROM claude_analysis ca
                    JOIN jobs j ON ca.job_id = j.id
                    WHERE ca.job_id = %s
                    ORDER BY ca.created_at DESC
                    LIMIT 1
                """, (job_id,))
                result = cur.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"Error fetching Claude analysis by job: {e}")
            return None


if __name__ == '__main__':
    # Test database connection
    with DatabaseHandler() as db:
        if db.conn:
            print("Database connection successful!")
            jobs = db.get_active_jobs()
            print(f"Found {len(jobs)} active jobs")
