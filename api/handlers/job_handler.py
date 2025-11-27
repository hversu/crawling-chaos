"""
Job Handler
Orchestrates job execution: collecting news, running AI analysis, and storing results
"""
import os
import time
import schedule
import threading
from typing import Dict, Any, List
from datetime import datetime
import json

from collectors.google_news import GoogleNewsCollector
from handlers.claude_handler import ClaudeHandler
from handlers.gpt_handler import GPTHandler
from handlers.db_handler import DatabaseHandler


class JobHandler:
    """Manages and executes data collection and analysis jobs"""

    def __init__(self):
        """Initialize job handler"""
        self.db = DatabaseHandler()
        self.db.connect()

        self.google_collector = GoogleNewsCollector()

        # Initialize AI handlers (with error handling for missing keys)
        try:
            self.claude_handler = ClaudeHandler()
        except ValueError:
            print("Warning: Claude API key not found")
            self.claude_handler = None

        try:
            self.gpt_handler = GPTHandler()
        except ValueError:
            print("Warning: OpenAI API key not found")
            self.gpt_handler = None

        self.running = False
        self.scheduler_thread = None

    def create_job(self, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new job

        Args:
            job_config: Job configuration dictionary

        Returns:
            Result dictionary with job_id
        """
        job_id = self.db.create_job(job_config)

        if job_id:
            return {
                'status': 'success',
                'job_id': job_id,
                'message': 'Job created successfully'
            }
        else:
            return {
                'status': 'error',
                'message': 'Failed to create job'
            }

    def execute_job(self, job_id: int) -> Dict[str, Any]:
        """
        Execute a single job

        Args:
            job_id: ID of the job to execute

        Returns:
            Execution result dictionary
        """
        print(f"[{datetime.utcnow().isoformat()}] Executing job {job_id}")

        # Get job details
        jobs = self.db.get_active_jobs()
        job = next((j for j in jobs if j['id'] == job_id), None)

        if not job:
            return {'status': 'error', 'message': 'Job not found'}

        results = {
            'job_id': job_id,
            'started_at': datetime.utcnow().isoformat(),
            'news_collected': 0,
            'claude_analyses': 0,
            'gpt_analyses': 0,
            'errors': []
        }

        try:
            # Step 1: Collect news
            print(f"  Collecting news for query: {job['google_search_query']}")
            news_result = self.google_collector.collect(
                query=job['google_search_query'],
                max_results=10
            )

            if news_result['status'] != 'success':
                results['errors'].append(f"News collection failed: {news_result.get('error')}")
                return results

            articles = news_result.get('articles', [])
            results['news_collected'] = len(articles)

            # Step 2: Save news to database
            article_ids = self.db.save_news_results(job_id, articles)
            print(f"  Saved {len(article_ids)} articles")

            # Step 3: Run Claude analysis if configured
            if job.get('claude_sys_prompt') and self.claude_handler:
                print(f"  Running Claude analysis...")
                for article, article_id in zip(articles, article_ids):
                    # Format user prompt with article data
                    user_prompt = job['claude_user_prompt'].format(
                        title=article.get('title', ''),
                        summary=article.get('summary', ''),
                        url=article.get('url', ''),
                        source=article.get('source', '')
                    )

                    claude_result = self.claude_handler.analyze(
                        system_prompt=job['claude_sys_prompt'],
                        user_prompt=user_prompt
                    )

                    if claude_result['status'] == 'success':
                        self.db.save_claude_analysis(
                            job_id=job_id,
                            news_result_id=article_id,
                            analysis_text=claude_result['analysis'],
                            raw_response=claude_result.get('raw_response', {})
                        )
                        results['claude_analyses'] += 1
                    else:
                        results['errors'].append(f"Claude analysis failed: {claude_result.get('error')}")

                print(f"  Completed {results['claude_analyses']} Claude analyses")

            # Step 4: Run GPT analysis if configured
            if job.get('gpt_sys_prompt') and self.gpt_handler:
                print(f"  Running GPT analysis...")
                for article, article_id in zip(articles, article_ids):
                    # Format user prompt with article data
                    user_prompt = job['gpt_user_prompt'].format(
                        title=article.get('title', ''),
                        summary=article.get('summary', ''),
                        url=article.get('url', ''),
                        source=article.get('source', '')
                    )

                    gpt_result = self.gpt_handler.analyze(
                        system_prompt=job['gpt_sys_prompt'],
                        user_prompt=user_prompt
                    )

                    if gpt_result['status'] == 'success':
                        self.db.save_gpt_analysis(
                            job_id=job_id,
                            news_result_id=article_id,
                            analysis_text=gpt_result['analysis'],
                            raw_response=gpt_result.get('raw_response', {})
                        )
                        results['gpt_analyses'] += 1
                    else:
                        results['errors'].append(f"GPT analysis failed: {gpt_result.get('error')}")

                print(f"  Completed {results['gpt_analyses']} GPT analyses")

            # Update job last run time
            self.db.update_job_last_run(job_id)

            results['status'] = 'success'
            results['completed_at'] = datetime.utcnow().isoformat()

        except Exception as e:
            results['status'] = 'error'
            results['errors'].append(str(e))
            print(f"  Job execution error: {e}")

        return results

    def schedule_jobs(self):
        """Schedule all active jobs based on their frequency"""
        jobs = self.db.get_active_jobs()

        # Clear existing schedule
        schedule.clear()

        for job in jobs:
            frequency = job['frequency_minutes']
            job_id = job['id']

            # Schedule job
            schedule.every(frequency).minutes.do(self.execute_job, job_id=job_id)
            print(f"Scheduled job {job_id} ({job['name']}) to run every {frequency} minutes")

    def start_scheduler(self):
        """Start the job scheduler in a background thread"""
        if self.running:
            return {'status': 'error', 'message': 'Scheduler already running'}

        self.running = True
        self.schedule_jobs()

        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(1)

        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()

        return {'status': 'success', 'message': 'Scheduler started'}

    def stop_scheduler(self):
        """Stop the job scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

        return {'status': 'success', 'message': 'Scheduler stopped'}

    def get_job_status(self) -> Dict[str, Any]:
        """Get current scheduler and job status"""
        jobs = self.db.get_active_jobs()

        return {
            'scheduler_running': self.running,
            'active_jobs': len(jobs),
            'jobs': [
                {
                    'id': job['id'],
                    'name': job['name'],
                    'frequency_minutes': job['frequency_minutes'],
                    'last_run': job['last_run'].isoformat() if job['last_run'] else None
                }
                for job in jobs
            ]
        }


if __name__ == '__main__':
    # Test job handler
    handler = JobHandler()
    status = handler.get_job_status()
    print(json.dumps(status, indent=2))
