#!/bin/bash

# Tech Tracker - Simple Docker Start Script
# This script starts Tech Tracker in containerized mode

set -e

echo "🚀 Starting Tech Tracker - AI-Powered Code Trend Analysis..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Copying from env.example..."
    cp env.example .env
    print_warning "Please edit .env file with your API keys."
fi

# Build and start Tech Tracker
print_status "Building and starting Tech Tracker..."
docker-compose -f docker-compose.yml up --build -d

# Wait for the service to be ready
print_status "Waiting for Tech Tracker to be ready..."
sleep 10

# Test if the service is healthy
if curl -f -s http://localhost:8000/health >/dev/null 2>&1; then
    print_success "✅ Tech Tracker is running successfully!"
    echo ""
    echo "🌐 Web Interface: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo "🔍 Health Check: http://localhost:8000/health"
    echo ""
    print_status "Try this API test:"
    echo "curl -X POST http://localhost:8000/api/v1/trends \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"query\": \"Python AI frameworks\", \"limit\": 5}'"
    echo ""
    print_status "To stop Tech Tracker:"
    echo "./docker-stop.sh"
else
    print_error "❌ Tech Tracker failed to start properly"
    echo ""
    print_status "Check logs with:"
    echo "docker-compose -f docker-compose.yml logs"
    exit 1
fi


