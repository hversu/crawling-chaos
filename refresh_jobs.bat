@echo off
REM Refresh Jobs Script (Windows)
REM Deletes all jobs, reloads from jobs folder, and restarts API

echo Deleting all existing jobs...
docker exec crawling-chaos-db psql -U postgres -d crawling_chaos -c "DELETE FROM jobs;" >nul 2>&1

echo Loading jobs from jobs folder...
set job_count=0
for %%f in (api\jobs\*.json) do (
    echo   Loading %%~nxf
    curl -s -X POST http://localhost:5000/api/jobs -H "Content-Type: application/json" -d @%%f >nul 2>&1
    set /a job_count+=1
)

echo Loaded %job_count% job(s)

echo Restarting API...
docker-compose restart api >nul 2>&1

echo Done! Jobs refreshed and API restarted
echo Watch logs with: docker logs -f crawling-chaos-api
