# Crawling Chaos - News Analysis Dashboard

An AI-powered news analysis web application that collects news from Google News, analyzes it using Claude and GPT, and displays the results in an interactive dashboard.

## Features

- **Google News Collection**: Automatically fetches news articles based on search queries
- **Dual AI Analysis**: Analyzes news using both Anthropic's Claude and OpenAI's GPT
- **Interactive Dashboard**: Displays news and analyses in a randomized 3-column grid
- **Scheduled Jobs**: Configure automated data collection at custom intervals
- **PostgreSQL Storage**: All data stored with timestamps for historical analysis
- **Docker-based**: Easy deployment with Docker Compose

## Architecture

### Backend (API)
- **Flask REST API** for all operations
- **Collectors**: `google_news` - RSS feed parser for Google News
- **Handlers**:
  - `claude_handler` - Interfaces with Anthropic API
  - `gpt_handler` - Interfaces with OpenAI API
  - `db_handler` - PostgreSQL database operations
  - `job_handler` - Job scheduling and orchestration

### Database
- **PostgreSQL** with tables for:
  - Jobs configuration
  - News results
  - Claude analyses
  - GPT analyses

### Frontend
- **Vanilla JavaScript** with dynamic panel generation
- **3xN Grid Layout** with randomized order on each page load
- **Three Panel Types**:
  1. News (title, summary, publish date)
  2. Claude Analysis
  3. GPT Analysis

## Prerequisites

- Docker and Docker Compose
- Anthropic API key (for Claude)
- OpenAI API key (for GPT)

## Quick Start

### 1. Clone and Setup

```bash
cd crawling-chaos
cp .env.example .env
```

### 2. Configure API Keys

Edit `.env` and add your API keys:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database on port 5432
- Flask API on port 5000
- Web interface accessible at http://localhost:5000

### 4. Create a Job

Create a job using the template:

```bash
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d @api/templates/news_analysis_job.json
```

Or customize your own job:

```bash
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech News Analysis",
    "google_search_query": "artificial intelligence breakthrough",
    "claude_sys_prompt": "You are a tech analyst...",
    "claude_user_prompt": "Analyze: {title}\n{summary}",
    "gpt_sys_prompt": "You are a tech commentator...",
    "gpt_user_prompt": "Comment on: {title}\n{summary}",
    "frequency_minutes": 60,
    "is_active": true
  }'
```

### 5. Start the Scheduler

```bash
curl -X POST http://localhost:5000/api/scheduler/start
```

### 6. View Dashboard

Open http://localhost:5000 in your browser to see the dashboard.

## Nginx Reverse Proxy Setup

For production deployment on servers with Nginx, the application runs in Docker on `localhost:5000`, and you configure Nginx on your host system to proxy requests to it.

**Security Note:** The nginx configuration restricts public access to read-only endpoints. Administrative API endpoints (job management, scheduler control) are only accessible from localhost. See [SECURITY.md](SECURITY.md) for details.

**Quick Setup:**

1. Deploy the application with Docker:
```bash
docker-compose up -d
```
This runs the Flask app on `localhost:5000` (not publicly accessible).

2. Configure Nginx on your host system using the provided templates:
```bash
# Copy the configuration template
sudo cp nginx/crawling-chaos.conf.template /etc/nginx/sites-available/news.example.com.conf

# Edit and replace DOMAIN_NAME with your actual domain
sudo sed -i 's/DOMAIN_NAME/news.example.com/g' /etc/nginx/sites-available/news.example.com.conf

# Obtain SSL certificate
sudo certbot certonly --nginx -d news.example.com

# Enable the site
sudo ln -s /etc/nginx/sites-available/news.example.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Your application is now accessible at `https://news.example.com` with security headers, rate limiting, and SSL.

**What's Publicly Accessible:**
- ✅ Dashboard frontend (read-only view)
- ✅ `/api/data/*` - News and analysis data
- ❌ `/api/jobs` - Job management (localhost only)
- ❌ `/api/scheduler` - Scheduler control (localhost only)
- ❌ Database (localhost only)

See [NGINX_DEPLOYMENT.md](NGINX_DEPLOYMENT.md) for detailed configuration and [SECURITY.md](SECURITY.md) for security model details.

## API Endpoints

### Job Management
- `GET /api/jobs` - List all jobs
- `POST /api/jobs` - Create new job
- `POST /api/jobs/<id>/execute` - Manually execute a job
- `GET /api/jobs/status` - Get scheduler status
- `POST /api/scheduler/start` - Start job scheduler
- `POST /api/scheduler/stop` - Stop job scheduler

### Data Retrieval
- `GET /api/data/news` - Get latest news results
- `GET /api/data/claude` - Get latest Claude analyses
- `GET /api/data/gpt` - Get latest GPT analyses

### Templates
- `GET /api/templates/<name>` - Load a job template

## Job Configuration

Jobs are configured with the following parameters:

```json
{
  "name": "Job Name",
  "google_search_query": "search terms",
  "claude_sys_prompt": "System prompt for Claude",
  "claude_user_prompt": "User prompt template with {title}, {summary}, {url}, {source}",
  "gpt_sys_prompt": "System prompt for GPT",
  "gpt_user_prompt": "User prompt template with {title}, {summary}, {url}, {source}",
  "frequency_minutes": 60,
  "is_active": true
}
```

## Project Structure

```
crawling-chaos/
├── api/
│   ├── collectors/
│   │   └── google_news.py
│   ├── handlers/
│   │   ├── claude_handler.py
│   │   ├── gpt_handler.py
│   │   ├── db_handler.py
│   │   └── job_handler.py
│   ├── templates/
│   │   └── news_analysis_job.json
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── database/
│   ├── init.sql
│   └── Dockerfile
├── interface/
│   ├── index.html
│   ├── styles.css
│   └── panel_populator.js
├── docker-compose.yaml
├── .env.example
└── README.md
```

## Development

### Running Without Docker

1. Install PostgreSQL locally
2. Create database: `createdb crawling_chaos`
3. Initialize schema: `psql crawling_chaos < database/init.sql`
4. Install Python dependencies: `pip install -r api/requirements.txt`
5. Set environment variables from `.env`
6. Run API: `python api/app.py`

### Testing Individual Components

Each module can be tested standalone:

```bash
# Test Google News collector
cd api
python collectors/google_news.py

# Test Claude handler
python handlers/claude_handler.py

# Test GPT handler
python handlers/gpt_handler.py
```

## Customization

### Adding New Collectors
Create a new collector in `api/collectors/` following the pattern:

```python
def collect(query: str) -> Dict[str, Any]:
    return {
        'status': 'success',
        'data': [...],
        'collected_at': datetime.utcnow().isoformat()
    }
```

### Custom Panel Styles
Edit `interface/styles.css` to customize panel appearance. Each panel type has its own class:
- `.panel.news`
- `.panel.claude`
- `.panel.gpt`

### Modifying Grid Layout
Edit `PANELS_PER_ROW` in `interface/panel_populator.js` to change column count.

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL container is healthy: `docker-compose ps`
- Check logs: `docker-compose logs postgres`

### API Not Starting
- Check API logs: `docker-compose logs api`
- Verify API keys are set in `.env`

### No Data Appearing
- Verify jobs are created: `curl http://localhost:5000/api/jobs`
- Check scheduler is running: `curl http://localhost:5000/api/jobs/status`
- Manually execute a job: `curl -X POST http://localhost:5000/api/jobs/1/execute`

### Frontend Not Loading Data
- Check browser console for errors
- Verify API is accessible: `curl http://localhost:5000/api/health`
- Check CORS settings if running on different domains

## License

MIT

## Contributing

Pull requests welcome! Please ensure:
- Code follows existing patterns
- All handlers return consistent response formats
- Database operations use transactions appropriately
- Frontend updates maintain 3xN grid structure
