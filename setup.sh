#!/bin/bash
# Quick setup script for Crawling Chaos

echo "========================================="
echo "Crawling Chaos - Setup Script"
echo "========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys:"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - OPENAI_API_KEY"
    echo ""
    read -p "Press Enter when you've added your API keys..."
fi

# Start Docker services
echo "Starting Docker services..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✓ Services are running!"
    echo ""
    echo "Creating default job from template..."

    # Create job
    curl -X POST http://localhost:5000/api/jobs \
      -H "Content-Type: application/json" \
      -d @api/templates/news_analysis_job.json \
      -s | python -m json.tool

    echo ""
    echo "Starting job scheduler..."
    curl -X POST http://localhost:5000/api/scheduler/start -s | python -m json.tool

    echo ""
    echo "========================================="
    echo "Setup Complete!"
    echo "========================================="
    echo ""
    echo "Dashboard: http://localhost:5000"
    echo "API Health: http://localhost:5000/api/health"
    echo ""
    echo "Jobs will run automatically based on their frequency."
    echo "Refresh the dashboard to see new data as it's collected."
    echo ""
else
    echo "❌ Error: Services failed to start"
    echo "Check logs with: docker-compose logs"
fi
