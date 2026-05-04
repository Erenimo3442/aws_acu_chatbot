#!/bin/bash
# Helper script to run tests locally

set -e

echo "🧪 Running AWS ACU Chatbot Tests"
echo "================================"

# Check if services are running
if ! docker compose ps | grep -q "Up"; then
    echo "⚠️  Docker services not running. Starting them..."
    docker compose up -d
    echo "⏳ Waiting for services to be ready..."
    sleep 5
fi

# Backend tests
echo ""
echo "📦 Running Backend Tests..."
docker compose exec backend python manage.py test

# Frontend - install dependencies if needed
echo ""
echo "📦 Installing Frontend Dependencies..."
docker compose exec frontend npm install

# Frontend linting
echo ""
echo "🔍 Running Frontend Linter..."
docker compose exec frontend npm run lint

# Frontend tests
echo ""
echo "⚛️  Running Frontend Tests..."
docker compose exec frontend npm run test

echo ""
echo "✅ All tests passed!"
