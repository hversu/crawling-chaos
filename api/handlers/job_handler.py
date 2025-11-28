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
            days_to_lookback = job.get('days_to_lookback')
            print(f"  Collecting news for query: {job['google_search_query']}")
            if days_to_lookback:
                print(f"  Looking back {days_to_lookback} days")

            news_result = self.google_collector.collect(
                query=job['google_search_query'],
                max_results=10,
                days_to_lookback=days_to_lookback
            )

            if news_result['status'] != 'success':
                results['errors'].append(f"News collection failed: {news_result.get('error')}")
                return results

            articles = news_result.get('articles', [])
            results['news_collected'] = len(articles)

            # Step 2: Save news to database
            article_ids = self.db.save_news_results(job_id, articles)
            print(f"  Saved {len(article_ids)} articles")

            # Step 3: Run Claude batch analysis if configured
            if job.get('claude_sys_prompt') and self.claude_handler and articles:
                print(f"  Running Claude batch analysis on {len(articles)} articles...")

                try:
                    # Use batch analysis to process all articles together
                    claude_result = self.claude_handler.analyze_batch(
                        system_prompt=job['claude_sys_prompt'],
                        articles=articles,
                        user_prompt_template=job['claude_user_prompt']
                    )

                    print(f"  Claude result status: {claude_result.get('status')}")

                    if claude_result['status'] == 'success':
                        # Save the batch analysis result
                        # Use the first article_id as the primary reference
                        analysis_id = self.db.save_claude_analysis(
                            job_id=job_id,
                            news_result_id=article_ids[0] if article_ids else None,
                            analysis_text=claude_result['analysis'],
                            raw_response=claude_result.get('raw_response', {})
                        )
                        if analysis_id:
                            results['claude_analyses'] = 1
                            print(f"  Completed Claude batch analysis (ID: {analysis_id})")
                        else:
                            error_msg = "Failed to save Claude analysis to database"
                            print(f"  ERROR: {error_msg}")
                            results['errors'].append(error_msg)
                    else:
                        error_msg = f"Claude batch analysis failed: {claude_result.get('error')}"
                        print(f"  ERROR: {error_msg}")
                        results['errors'].append(error_msg)
                except Exception as e:
                    error_msg = f"Claude analysis exception: {str(e)}"
                    print(f"  ERROR: {error_msg}")
                    results['errors'].append(error_msg)

            # Step 4: Run GPT batch analysis if configured
            if job.get('gpt_sys_prompt') and self.gpt_handler and articles:
                print(f"  Running GPT batch analysis on {len(articles)} articles...")

                try:
                    # Use batch analysis to process all articles together
                    gpt_result = self.gpt_handler.analyze_batch(
                        system_prompt=job['gpt_sys_prompt'],
                        articles=articles,
                        user_prompt_template=job['gpt_user_prompt']
                    )

                    print(f"  GPT result status: {gpt_result.get('status')}")

                    if gpt_result['status'] == 'success':
                        # Save the batch analysis result
                        # Use the first article_id as the primary reference
                        analysis_id = self.db.save_gpt_analysis(
                            job_id=job_id,
                            news_result_id=article_ids[0] if article_ids else None,
                            analysis_text=gpt_result['analysis'],
                            raw_response=gpt_result.get('raw_response', {})
                        )
                        if analysis_id:
                            results['gpt_analyses'] = 1
                            print(f"  Completed GPT batch analysis (ID: {analysis_id})")
                        else:
                            error_msg = "Failed to save GPT analysis to database"
                            print(f"  ERROR: {error_msg}")
                            results['errors'].append(error_msg)
                    else:
                        error_msg = f"GPT batch analysis failed: {gpt_result.get('error')}"
                        print(f"  ERROR: {error_msg}")
                        results['errors'].append(error_msg)
                except Exception as e:
                    error_msg = f"GPT analysis exception: {str(e)}"
                    print(f"  ERROR: {error_msg}")
                    results['errors'].append(error_msg)

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

    def start_scheduler(self, run_immediately: bool = True):
        """
        Start the job scheduler in a background thread

        Args:
            run_immediately: If True, runs all jobs once immediately on startup
        """
        if self.running:
            return {'status': 'error', 'message': 'Scheduler already running'}

        self.running = True

        # Check if there are any jobs, if not, create a default one
        jobs = self.db.get_active_jobs()
        if len(jobs) == 0:
            print("No jobs found. Creating default job from template...")
            try:
                template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'news_analysis_job.json')
                with open(template_path, 'r') as f:
                    template = json.load(f)

                # Remove description field as it's not in the database schema
                if 'description' in template:
                    del template['description']

                result = self.create_job(template)
                if result['status'] == 'success':
                    print(f"Created default job with ID: {result['job_id']}")
                    jobs = self.db.get_active_jobs()  # Refresh jobs list
                else:
                    print(f"Failed to create default job: {result.get('message')}")
            except Exception as e:
                print(f"Error creating default job: {e}")

        self.schedule_jobs()

        # Run all jobs immediately on startup
        if run_immediately:
            jobs = self.db.get_active_jobs()
            print(f"Running {len(jobs)} jobs immediately on startup...")
            for job in jobs:
                try:
                    self.execute_job(job['id'])
                except Exception as e:
                    print(f"Error running job {job['id']} on startup: {e}")

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
