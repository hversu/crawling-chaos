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
from handlers.template_handler import TemplateHandler


class JobHandler:
    """Manages and executes data collection and analysis jobs"""

    def __init__(self):
        """Initialize job handler"""
        self.db = DatabaseHandler()
        self.db.connect()

        self.template_handler = TemplateHandler()
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

        # Execute the job
        if job.get('template_name'):
            result = self._execute_templated_job(job_id, job)
        else:
            result = self._execute_legacy_job(job_id, job)

        # After successful execution, trigger any dependent jobs
        if result.get('status') == 'success':
            self._trigger_dependent_jobs(job_id)

        return result

    def _trigger_dependent_jobs(self, parent_job_id: int):
        """Trigger jobs that depend on the completed parent job"""
        dependent_jobs = self.db.get_dependent_jobs(parent_job_id)

        if dependent_jobs:
            print(f"  Triggering {len(dependent_jobs)} dependent job(s)...")

            for dep_job in dependent_jobs:
                dep_job_id = dep_job['id']
                dep_job_name = dep_job['name']
                print(f"  -> Executing dependent job: {dep_job_name} (ID: {dep_job_id})")

                try:
                    self.execute_job(dep_job_id)
                except Exception as e:
                    print(f"  ERROR executing dependent job {dep_job_id}: {e}")

    def _execute_templated_job(self, job_id: int, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a job using a template

        Args:
            job_id: Job ID
            job: Job configuration with template_name and parameters

        Returns:
            Execution result dictionary
        """
        print(f"  Using template: {job['template_name']}")

        # Load template
        template = self.template_handler.load_template(job['template_name'])
        if not template:
            return {
                'status': 'error',
                'message': f"Template not found: {job['template_name']}"
            }

        # Check if this is a deep_dive template (requires parent job analysis)
        workflow = template.get('workflow', {})
        input_source = workflow.get('input_source', {})

        if input_source.get('type') == 'parent_job_analysis':
            return self._execute_deep_dive_job(job_id, job, template)
        else:
            return self._execute_standard_templated_job(job_id, job, template)

    def _execute_standard_templated_job(self, job_id: int, job: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a standard templated job (news_analysis type)"""

        results = {
            'job_id': job_id,
            'started_at': datetime.utcnow().isoformat(),
            'news_collected': 0,
            'claude_analyses': 0,
            'gpt_analyses': 0,
            'errors': []
        }

        try:
            # Get job parameters
            parameters = job.get('parameters', {})

            # Step 1: Run collectors
            articles = []
            collectors = self.template_handler.get_collectors(template)

            for collector_config in collectors:
                collector_type = collector_config.get('type')

                if collector_type == 'google_news':
                    query = parameters.get('google_search_query')
                    days_to_lookback = parameters.get('days_to_lookback')
                    max_results = parameters.get('max_articles', 10)

                    print(f"  Collecting news for query: {query}")
                    print(f"  Max articles: {max_results}")
                    if days_to_lookback:
                        print(f"  Looking back {days_to_lookback} days")

                    news_result = self.google_collector.collect(
                        query=query,
                        max_results=max_results,
                        days_to_lookback=days_to_lookback
                    )

                    if news_result['status'] == 'success':
                        articles.extend(news_result.get('articles', []))
                    else:
                        results['errors'].append(f"News collection failed: {news_result.get('error')}")

            results['news_collected'] = len(articles)

            # Save articles to database
            if articles:
                article_ids = self.db.save_news_results(job_id, articles)
                print(f"  Saved {len(article_ids)} articles")

                # Step 2: Run analyzers
                analyzers = self.template_handler.get_analyzers(template)

                for analyzer_config in analyzers:
                    analyzer_type = analyzer_config.get('type')

                    if analyzer_type == 'claude' and self.claude_handler:
                        self._run_claude_analysis(
                            job_id=job_id,
                            articles=articles,
                            article_ids=article_ids,
                            system_prompt=analyzer_config.get('system_prompt'),
                            user_prompt_template=analyzer_config.get('user_prompt_template'),
                            results=results
                        )

                    elif analyzer_type == 'gpt' and self.gpt_handler:
                        self._run_gpt_analysis(
                            job_id=job_id,
                            articles=articles,
                            article_ids=article_ids,
                            system_prompt=analyzer_config.get('system_prompt'),
                            user_prompt_template=analyzer_config.get('user_prompt_template'),
                            results=results
                        )

            # Update job last run time
            self.db.update_job_last_run(job_id)

            results['status'] = 'success'
            results['completed_at'] = datetime.utcnow().isoformat()

        except Exception as e:
            results['status'] = 'error'
            results['errors'].append(str(e))
            print(f"  Job execution error: {e}")

        return results

    def _execute_deep_dive_job(self, job_id: int, job: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a deep_dive template job that takes parent analysis as input"""
        results = {
            'job_id': job_id,
            'started_at': datetime.utcnow().isoformat(),
            'queries_generated': 0,
            'searches_performed': 0,
            'results_collected': 0,
            'errors': []
        }

        try:
            # Get parent job ID from dependencies
            parent_job_id = job.get('depends_on_job_id')
            if not parent_job_id:
                return {
                    'status': 'error',
                    'message': 'Deep dive job requires depends_on_job_id'
                }

            print(f"  Deep dive triggered by parent job {parent_job_id}")

            # Get latest Claude analysis from parent job
            parent_analysis = self.db.get_latest_claude_analysis_by_job(parent_job_id)
            if not parent_analysis:
                return {
                    'status': 'error',
                    'message': f'No Claude analysis found for parent job {parent_job_id}'
                }

            analysis_text = parent_analysis.get('analysis_text', '')
            analysis_id = parent_analysis.get('id')
            print(f"  Using parent analysis ID {analysis_id}")

            # Get analyzers from template
            analyzers = self.template_handler.get_analyzers(template)
            query_generator = next((a for a in analyzers if a.get('name') == 'query_generator'), None)

            if not query_generator or not self.claude_handler:
                return {
                    'status': 'error',
                    'message': 'Query generator not found in template or Claude handler not available'
                }

            # Generate search queries using Claude
            print(f"  Generating search queries from analysis...")
            query_result = self.claude_handler.generate_search_queries(
                analysis_text=analysis_text,
                system_prompt=query_generator.get('system_prompt'),
                user_prompt_template=query_generator.get('user_prompt_template')
            )

            if query_result['status'] != 'success':
                return {
                    'status': 'error',
                    'message': f"Query generation failed: {query_result.get('error')}"
                }

            queries = query_result.get('queries', [])
            justification = query_result.get('justification', '')
            print(f"  Generated {len(queries)} search queries")

            # Save search queries to database
            query_id = self.db.save_search_queries(
                job_id=job_id,
                parent_analysis_id=analysis_id,
                queries=queries,
                justification=justification,
                raw_response=query_result.get('raw_response', {})
            )
            results['queries_generated'] = len(queries)

            # Execute SerpAPI searches for each query
            from collectors.serpapi import SerpAPICollector

            try:
                serpapi_collector = SerpAPICollector()

                for query_obj in queries:
                    query_text = query_obj.get('query', '')
                    print(f"  Searching: {query_text}")

                    search_result = serpapi_collector.collect(
                        query=query_text,
                        max_results=10,
                        search_type='organic'
                    )

                    if search_result['status'] == 'success':
                        # Save search results to collections
                        search_results = search_result.get('results', [])
                        if search_results:
                            collection_ids = self.db.save_collection(
                                job_id=job_id,
                                collection_type='serpapi',
                                items=search_results
                            )
                            results['results_collected'] += len(collection_ids)
                            results['searches_performed'] += 1
                    else:
                        error_msg = f"SerpAPI search failed for '{query_text}': {search_result.get('error')}"
                        print(f"  ERROR: {error_msg}")
                        results['errors'].append(error_msg)

            except Exception as e:
                error_msg = f"SerpAPI collector error: {str(e)}"
                print(f"  ERROR: {error_msg}")
                results['errors'].append(error_msg)

            # Update job last run time
            self.db.update_job_last_run(job_id)

            results['status'] = 'success'
            results['completed_at'] = datetime.utcnow().isoformat()

            print(f"  Deep dive complete: {results['queries_generated']} queries, {results['searches_performed']} searches, {results['results_collected']} results")

            return results

        except Exception as e:
            error_msg = f"Deep dive job error: {str(e)}"
            print(f"  ERROR: {error_msg}")
            results['errors'].append(error_msg)
            results['status'] = 'error'
            return results

    def _execute_legacy_job(self, job_id: int, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a job using legacy direct configuration (backward compatibility)

        Args:
            job_id: Job ID
            job: Job configuration with embedded prompts

        Returns:
            Execution result dictionary
        """
        print(f"  Using legacy job configuration")

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
                self._run_claude_analysis(
                    job_id=job_id,
                    articles=articles,
                    article_ids=article_ids,
                    system_prompt=job['claude_sys_prompt'],
                    user_prompt_template=job['claude_user_prompt'],
                    results=results
                )

            # Step 4: Run GPT batch analysis if configured
            if job.get('gpt_sys_prompt') and self.gpt_handler and articles:
                self._run_gpt_analysis(
                    job_id=job_id,
                    articles=articles,
                    article_ids=article_ids,
                    system_prompt=job['gpt_sys_prompt'],
                    user_prompt_template=job['gpt_user_prompt'],
                    results=results
                )

            # Update job last run time
            self.db.update_job_last_run(job_id)

            results['status'] = 'success'
            results['completed_at'] = datetime.utcnow().isoformat()

        except Exception as e:
            results['status'] = 'error'
            results['errors'].append(str(e))
            print(f"  Job execution error: {e}")

        return results

    def _run_claude_analysis(
        self,
        job_id: int,
        articles: List[Dict],
        article_ids: List[int],
        system_prompt: str,
        user_prompt_template: str,
        results: Dict[str, Any]
    ):
        """
        Run Claude analysis on articles

        Args:
            job_id: Job ID
            articles: List of article dictionaries
            article_ids: List of saved article IDs
            system_prompt: System prompt for Claude
            user_prompt_template: User prompt template
            results: Results dictionary to update
        """
        print(f"  Running Claude batch analysis on {len(articles)} articles...")

        try:
            claude_result = self.claude_handler.analyze_batch(
                system_prompt=system_prompt,
                articles=articles,
                user_prompt_template=user_prompt_template
            )

            print(f"  Claude result status: {claude_result.get('status')}")

            if claude_result['status'] == 'success':
                analysis_id = self.db.save_claude_analysis(
                    job_id=job_id,
                    collection_id=article_ids[0] if article_ids else None,
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

    def _run_gpt_analysis(
        self,
        job_id: int,
        articles: List[Dict],
        article_ids: List[int],
        system_prompt: str,
        user_prompt_template: str,
        results: Dict[str, Any]
    ):
        """
        Run GPT analysis on articles

        Args:
            job_id: Job ID
            articles: List of article dictionaries
            article_ids: List of saved article IDs
            system_prompt: System prompt for GPT
            user_prompt_template: User prompt template
            results: Results dictionary to update
        """
        print(f"  Running GPT batch analysis on {len(articles)} articles...")

        try:
            gpt_result = self.gpt_handler.analyze_batch(
                system_prompt=system_prompt,
                articles=articles,
                user_prompt_template=user_prompt_template
            )

            print(f"  GPT result status: {gpt_result.get('status')}")

            if gpt_result['status'] == 'success':
                analysis_id = self.db.save_gpt_analysis(
                    job_id=job_id,
                    collection_id=article_ids[0] if article_ids else None,
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

    def schedule_jobs(self):
        """Schedule all active jobs based on their frequency"""
        jobs = self.db.get_active_jobs()

        # Clear existing schedule
        schedule.clear()

        for job in jobs:
            frequency = job['frequency_minutes']
            job_id = job['id']
            depends_on = job.get('depends_on_job_id')

            # Skip jobs that are dependency-driven only (no frequency)
            if frequency is None:
                if depends_on:
                    print(f"Job {job_id} ({job['name']}) is dependency-driven, will run after job {depends_on}")
                else:
                    print(f"WARNING: Job {job_id} ({job['name']}) has no frequency and no dependency")
                continue

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

        # Check if there are any jobs
        jobs = self.db.get_active_jobs()
        if len(jobs) == 0:
            print("No jobs found. Use refresh_jobs script to load jobs from api/jobs/ folder.")
        else:
            print(f"Found {len(jobs)} active job(s)")

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
