#!/bin/bash

# Tech Tracker Setup Script
# Containerized setup using Docker Compose

set -e

echo "🚀 Setting up Tech Tracker - AI-Powered Code Trend Analysis..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
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

print_header() {
    echo -e "${PURPLE}[TECH TRACKER]${NC} $1"
}

# Check if Docker and Docker Compose are installed
check_docker() {
    print_status "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed and running"
}

# Check environment file
check_environment() {
    print_status "Checking environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            print_warning ".env file not found. Copying from env.example..."
            cp env.example .env
            print_warning "Please edit .env file with your API keys before starting the services."
        else
            print_error ".env file not found and no env.example available."
            exit 1
        fi
    fi
    
    # Check for required environment variables
    source .env 2>/dev/null || true
    
    if [ -z "$OPENAI_API_KEY" ]; then
        print_warning "OPENAI_API_KEY not set in .env file. This is required for the AI agents."
    fi
    
    if [ -z "$GITHUB_TOKEN" ]; then
        print_warning "GITHUB_TOKEN not set in .env file. GitHub MCP server may have limited functionality."
    fi
    
    print_success "Environment configuration checked"
}

# Build and start all services
start_services() {
    print_header "Starting Tech Tracker services..."
    
    # Build the main application
    print_status "Building Tech Tracker application..."
    docker-compose build tech-tracker
    
    # Start all services
    print_status "Starting all services..."
    docker-compose up -d
    
    print_success "All services started successfully!"
}

# Wait for services to be healthy
wait_for_services() {
    print_status "Waiting for services to be healthy..."
    
    # Wait for main application
    local max_attempts=60
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s http://localhost:8000/health >/dev/null 2>&1; then
            print_success "Tech Tracker application is healthy!"
            break
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "Tech Tracker application failed to become healthy"
        docker-compose logs tech-tracker
        exit 1
    fi
}

# Show service status
show_status() {
    print_header "Tech Tracker Service Status"
    echo ""
    
    # Check Docker Compose services
    docker-compose ps
    
    echo ""
    print_status "Service URLs:"
    echo "┌─────────────────────────┬──────┬─────────────────────────────┐"
    echo "│ Service                 │ Port │ URL                         │"
    echo "├─────────────────────────┼──────┼─────────────────────────────┤"
    
    services=(
        "Tech Tracker App:8000:http://localhost:8000"
        "API Documentation:8000:http://localhost:8000/docs"
        "Brave Search MCP:3001:http://localhost:3001"
        "GitHub MCP:3002:http://localhost:3002"
        "Hacker News MCP:3003:http://localhost:3003"
        "Filesystem MCP:3004:http://localhost:3004"
    )
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r service_name port url <<< "$service_info"
        printf "│ %-23s │ %-4s │ %-27s │\n" "$service_name" "$port" "$url"
    done
    
    echo "└─────────────────────────┴──────┴─────────────────────────────┘"
    echo ""
    
    # Test main application
    if curl -f -s http://localhost:8000/health >/dev/null 2>&1; then
        print_success "✅ Tech Tracker is running and healthy!"
        echo ""
        print_status "Try these commands to test the API:"
        echo "  curl http://localhost:8000/health"
        echo "  curl -X POST http://localhost:8000/api/v1/trends \\"
        echo "    -H 'Content-Type: application/json' \\"
        echo "    -d '{\"query\": \"Python AI frameworks\", \"limit\": 5}'"
    else
        print_warning "⚠️  Tech Tracker may still be starting up..."
    fi
}

# Stop all services
stop_services() {
    print_status "Stopping Tech Tracker services..."
    docker-compose down
    print_success "All services stopped"
}

# Clean up everything
cleanup_services() {
    print_status "Cleaning up Tech Tracker services..."
    docker-compose down -v --remove-orphans
    docker-compose rm -f
    
    # Remove images if requested
    if [ "${1:-}" = "--images" ]; then
        print_status "Removing Docker images..."
        docker-compose down --rmi all
    fi
    
    print_success "Cleanup completed"
}

# View logs
view_logs() {
    local service="${1:-}"
    
    if [ -n "$service" ]; then
        print_status "Viewing logs for $service..."
        docker-compose logs -f "$service"
    else
        print_status "Viewing logs for all services..."
        docker-compose logs -f
    fi
}

# Restart services
restart_services() {
    print_status "Restarting Tech Tracker services..."
    docker-compose restart
    print_success "Services restarted"
}

# Show help
show_help() {
    echo "Tech Tracker - Docker Compose Management Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start     - Start all Tech Tracker services"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  status    - Show service status and URLs"
    echo "  logs      - View logs (optionally specify service name)"
    echo "  cleanup   - Stop and remove all containers and volumes"
    echo "  build     - Rebuild the Tech Tracker application"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 logs tech-tracker        # View Tech Tracker app logs"
    echo "  $0 cleanup --images         # Cleanup including Docker images"
    echo ""
    echo "Environment:"
    echo "  Make sure to configure your .env file with required API keys:"
    echo "  - OPENAI_API_KEY (required)"
    echo "  - GITHUB_TOKEN (optional, for enhanced GitHub features)"
    echo "  - BRAVE_API_KEY (optional, for enhanced search features)"
}

# Main function
main() {
    local command="${1:-start}"
    
    case "$command" in
        "start")
            check_docker
            check_environment
            start_services
            wait_for_services
            show_status
            print_success "🎉 Tech Tracker is ready!"
            echo ""
            print_status "Next steps:"
            echo "  1. Visit http://localhost:8000/docs for API documentation"
            echo "  2. Try the web interface at http://localhost:8000"
            echo "  3. Run '$0 logs' to monitor application logs"
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            wait_for_services
            show_status
            ;;
        "status")
            show_status
            ;;
        "logs")
            view_logs "${2:-}"
            ;;
        "cleanup")
            cleanup_services "${2:-}"
            ;;
        "build")
            check_docker
            print_status "Rebuilding Tech Tracker application..."
            docker-compose build tech-tracker
            print_success "Build completed"
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"

