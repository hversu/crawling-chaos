#!/bin/bash
# Refresh Jobs Script
# Deletes all jobs, reloads from jobs folder, and restarts API

set -e  # Exit on any error

echo "🗑️  Deleting all existing jobs..."
docker exec crawling-chaos-db psql -U postgres -d crawling_chaos -c "DELETE FROM jobs;" > /dev/null

echo "📁 Loading jobs from jobs folder..."
job_count=0
for job_file in api/jobs/*.json; do
    if [ -f "$job_file" ]; then
        job_name=$(basename "$job_file")
        echo "  ✓ Loading $job_name"
        curl -s -X POST http://localhost:5000/api/jobs \
          -H "Content-Type: application/json" \
          -d @"$job_file" > /dev/null
        ((job_count++))
    fi
done

echo "✅ Loaded $job_count job(s)"

echo "🔄 Restarting API..."
docker-compose restart api > /dev/null 2>&1

echo "⏳ Waiting for API to start..."
sleep 5

echo "🚀 Triggering jobs manually..."
for i in $(seq 1 $job_count); do
    curl -s -X POST http://localhost:5000/api/jobs/$i/execute > /dev/null 2>&1
done

echo "🎉 Done! Jobs refreshed and running"
echo "📊 Watch logs with: docker logs -f crawling-chaos-api"
