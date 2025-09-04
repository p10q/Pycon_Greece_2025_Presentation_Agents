#!/bin/bash

# Tech Tracker - Simple Docker Stop Script

echo "🛑 Stopping Tech Tracker..."

# Stop and remove containers
docker-compose -f docker-compose.minimal.yml down

echo "✅ Tech Tracker stopped successfully!"


