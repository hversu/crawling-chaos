@echo off
REM Quick setup script for Crawling Chaos (Windows)

echo =========================================
echo Crawling Chaos - Setup Script
echo =========================================
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo WARNING: Please edit .env and add your API keys:
    echo    - ANTHROPIC_API_KEY
    echo    - OPENAI_API_KEY
    echo.
    pause
)

REM Start Docker services
echo Starting Docker services...
docker-compose up -d

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Create job
echo Creating default job from template...
curl -X POST http://localhost:5000/api/jobs -H "Content-Type: application/json" -d @api/templates/news_analysis_job.json

echo.
echo Starting job scheduler...
curl -X POST http://localhost:5000/api/scheduler/start

echo.
echo =========================================
echo Setup Complete!
echo =========================================
echo.
echo Dashboard: http://localhost:5000
echo API Health: http://localhost:5000/api/health
echo.
echo Jobs will run automatically based on their frequency.
echo Refresh the dashboard to see new data as it's collected.
echo.
pause
