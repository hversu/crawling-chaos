"""
Flask API Server for Crawling Chaos News Analysis
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import json

from handlers.job_handler import JobHandler
from handlers.db_handler import DatabaseHandler

app = Flask(__name__, static_folder='../interface', static_url_path='')
CORS(app)

# Initialize handlers
job_handler = JobHandler()
db_handler = DatabaseHandler()
db_handler.connect()


@app.route('/')
def index():
    """Serve the main frontend page"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'crawling-chaos-api'
    })


# Job Management Endpoints
@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get all active jobs"""
    try:
        jobs = db_handler.get_active_jobs()
        return jsonify({
            'status': 'success',
            'jobs': jobs
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Create a new job"""
    try:
        job_config = request.json
        result = job_handler.create_job(job_config)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/jobs/<int:job_id>/execute', methods=['POST'])
def execute_job(job_id):
    """Execute a specific job manually"""
    try:
        result = job_handler.execute_job(job_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/jobs/status', methods=['GET'])
def job_status():
    """Get job scheduler status"""
    try:
        status = job_handler.get_job_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/scheduler/start', methods=['POST'])
def start_scheduler():
    """Start the job scheduler"""
    try:
        result = job_handler.start_scheduler()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """Stop the job scheduler"""
    try:
        result = job_handler.stop_scheduler()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Data Retrieval Endpoints for Frontend
@app.route('/api/data/news', methods=['GET'])
def get_news_data():
    """Get latest news results for frontend"""
    try:
        limit = request.args.get('limit', 100, type=int)
        news = db_handler.get_latest_news_results(limit=limit)
        return jsonify({
            'status': 'success',
            'data': news,
            'count': len(news)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/data/claude', methods=['GET'])
def get_claude_data():
    """Get latest Claude analyses for frontend"""
    try:
        limit = request.args.get('limit', 100, type=int)
        analyses = db_handler.get_latest_claude_analysis(limit=limit)
        return jsonify({
            'status': 'success',
            'data': analyses,
            'count': len(analyses)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/data/gpt', methods=['GET'])
def get_gpt_data():
    """Get latest GPT analyses for frontend"""
    try:
        limit = request.args.get('limit', 100, type=int)
        analyses = db_handler.get_latest_gpt_analysis(limit=limit)
        return jsonify({
            'status': 'success',
            'data': analyses,
            'count': len(analyses)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Template loading
@app.route('/api/templates/<template_name>', methods=['GET'])
def get_template(template_name):
    """Load a job template"""
    try:
        template_path = os.path.join('templates', f'{template_name}.json')
        with open(template_path, 'r') as f:
            template = json.load(f)
        return jsonify({
            'status': 'success',
            'template': template
        })
    except FileNotFoundError:
        return jsonify({
            'status': 'error',
            'message': 'Template not found'
        }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


if __name__ == '__main__':
    # Auto-start scheduler on startup
    print("Starting job scheduler...")
    job_handler.start_scheduler()

    # Run Flask app
    port = int(os.getenv('API_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
