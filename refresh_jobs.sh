 # Reload jobs with new date windows
  docker exec crawling-chaos-db psql -U postgres -d crawling_chaos -c "DELETE FROM jobs;"

  curl -X POST http://localhost:5000/api/jobs -H "Content-Type:application/json" -d @api/jobs/chaos_treasury.json
  curl -X POST http://localhost:5000/api/jobs -H "Content-Type:application/json" -d @api/jobs/agent_of_chaos.json
  curl -X POST http://localhost:5000/api/jobs -H "Content-Type:application/json" -d @api/jobs/deep_dive.json
  # Restart and watch the new logging
  docker compose restart api
  docker logs -f crawling-chaos-api