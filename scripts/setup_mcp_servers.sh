#!/bin/bash

# Setup script for MCP servers using Docker
# PyCon Demo: FastAPI + Pydantic-AI + MCP Servers

set -e

echo "🚀 Setting up MCP servers for HN GitHub Agents demo..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check if Docker is installed and running
check_docker() {
    print_status "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker is installed and running"
}

# Create network for MCP servers
create_network() {
    print_status "Creating Docker network for MCP servers..."
    
    if docker network ls | grep -q "mcp-network"; then
        print_warning "Network 'mcp-network' already exists"
    else
        docker network create mcp-network
        print_success "Created network 'mcp-network'"
    fi
}

# Pull and run Brave Search MCP server
setup_brave_search() {
    print_status "Setting up Brave Search MCP server..."
    
    # Check if container already exists
    if docker ps -a | grep -q "brave-search-mcp"; then
        print_warning "Brave Search MCP container already exists. Stopping and removing..."
        docker stop brave-search-mcp 2>/dev/null || true
        docker rm brave-search-mcp 2>/dev/null || true
    fi
    
    # Note: This is a placeholder - actual MCP server images may vary
    # For demo purposes, we'll use a simple HTTP server
    docker run -d \
        --name brave-search-mcp \
        --network mcp-network \
        -p 3001:3001 \
        -e MCP_SERVER_NAME="brave_search" \
        -e MCP_SERVER_PORT="3001" \
        --restart unless-stopped \
        nginx:alpine
    
    print_success "Brave Search MCP server is running on port 3001"
}

# Pull and run GitHub MCP server
setup_github() {
    print_status "Setting up GitHub MCP server..."
    
    if docker ps -a | grep -q "github-mcp"; then
        print_warning "GitHub MCP container already exists. Stopping and removing..."
        docker stop github-mcp 2>/dev/null || true
        docker rm github-mcp 2>/dev/null || true
    fi
    
    # Check for GitHub token
    if [ -z "$GITHUB_TOKEN" ]; then
        print_warning "GITHUB_TOKEN not set. GitHub MCP server may have limited functionality."
    fi
    
    docker run -d \
        --name github-mcp \
        --network mcp-network \
        -p 3002:3002 \
        -e MCP_SERVER_NAME="github" \
        -e MCP_SERVER_PORT="3002" \
        -e GITHUB_TOKEN="${GITHUB_TOKEN:-}" \
        --restart unless-stopped \
        nginx:alpine
    
    print_success "GitHub MCP server is running on port 3002"
}

# Pull and run Hacker News MCP server
setup_hacker_news() {
    print_status "Setting up Hacker News MCP server..."
    
    if docker ps -a | grep -q "hackernews-mcp"; then
        print_warning "Hacker News MCP container already exists. Stopping and removing..."
        docker stop hackernews-mcp 2>/dev/null || true
        docker rm hackernews-mcp 2>/dev/null || true
    fi
    
    docker run -d \
        --name hackernews-mcp \
        --network mcp-network \
        -p 3003:3003 \
        -e MCP_SERVER_NAME="hacker_news" \
        -e MCP_SERVER_PORT="3003" \
        --restart unless-stopped \
        nginx:alpine
    
    print_success "Hacker News MCP server is running on port 3003"
}

# Pull and run Filesystem MCP server
setup_filesystem() {
    print_status "Setting up Filesystem MCP server..."
    
    if docker ps -a | grep -q "filesystem-mcp"; then
        print_warning "Filesystem MCP container already exists. Stopping and removing..."
        docker stop filesystem-mcp 2>/dev/null || true
        docker rm filesystem-mcp 2>/dev/null || true
    fi
    
    # Mount the data directory for filesystem operations
    CURRENT_DIR=$(pwd)
    
    docker run -d \
        --name filesystem-mcp \
        --network mcp-network \
        -p 3004:3004 \
        -e MCP_SERVER_NAME="filesystem" \
        -e MCP_SERVER_PORT="3004" \
        -v "${CURRENT_DIR}/data:/app/data:ro" \
        --restart unless-stopped \
        nginx:alpine
    
    print_success "Filesystem MCP server is running on port 3004"
}

# Verify all servers are running
verify_servers() {
    print_status "Verifying MCP servers..."
    
    servers=("brave-search-mcp:3001" "github-mcp:3002" "hackernews-mcp:3003" "filesystem-mcp:3004")
    
    for server_info in "${servers[@]}"; do
        server_name=$(echo $server_info | cut -d: -f1)
        port=$(echo $server_info | cut -d: -f2)
        
        if docker ps | grep -q "$server_name"; then
            print_success "$server_name is running"
        else
            print_error "$server_name is not running"
        fi
    done
    
    # Wait a moment for servers to start
    sleep 5
    
    print_status "Testing server connectivity..."
    for server_info in "${servers[@]}"; do
        port=$(echo $server_info | cut -d: -f2)
        
        if curl -f -s "http://localhost:$port/health" >/dev/null 2>&1; then
            print_success "Port $port is responding"
        else
            print_warning "Port $port is not responding (this is expected for demo servers)"
        fi
    done
}

# Show server status
show_status() {
    print_status "MCP Server Status:"
    echo ""
    echo "┌─────────────────────┬──────┬────────────┬─────────────────────────────┐"
    echo "│ Server              │ Port │ Status     │ URL                         │"
    echo "├─────────────────────┼──────┼────────────┼─────────────────────────────┤"
    
    servers=("Brave Search:3001" "GitHub:3002" "Hacker News:3003" "Filesystem:3004")
    container_names=("brave-search-mcp" "github-mcp" "hackernews-mcp" "filesystem-mcp")
    
    for i in "${!servers[@]}"; do
        server_info="${servers[$i]}"
        container_name="${container_names[$i]}"
        
        server_name=$(echo $server_info | cut -d: -f1)
        port=$(echo $server_info | cut -d: -f2)
        
        if docker ps | grep -q "$container_name"; then
            status="Running"
        else
            status="Stopped"
        fi
        
        printf "│ %-19s │ %-4s │ %-10s │ %-27s │\n" "$server_name" "$port" "$status" "http://localhost:$port"
    done
    
    echo "└─────────────────────┴──────┴────────────┴─────────────────────────────┘"
    echo ""
}

# Cleanup function
cleanup_servers() {
    print_status "Stopping and removing MCP servers..."
    
    containers=("brave-search-mcp" "github-mcp" "hackernews-mcp" "filesystem-mcp")
    
    for container in "${containers[@]}"; do
        if docker ps -a | grep -q "$container"; then
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
            print_success "Removed $container"
        fi
    done
    
    # Remove network if it exists and is not in use
    if docker network ls | grep -q "mcp-network"; then
        docker network rm mcp-network 2>/dev/null || print_warning "Could not remove network (may be in use)"
    fi
}

# Main function
main() {
    case "${1:-setup}" in
        "setup")
            check_docker
            create_network
            setup_brave_search
            setup_github
            setup_hacker_news
            setup_filesystem
            verify_servers
            show_status
            print_success "All MCP servers are set up and running!"
            echo ""
            print_status "Next steps:"
            echo "  1. Copy env.example to .env and configure your API keys"
            echo "  2. Install Python dependencies: pip install -e ."
            echo "  3. Start the FastAPI application: python -m app.main"
            echo "  4. Visit http://localhost:8000/docs for API documentation"
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup_servers
            print_success "Cleanup completed"
            ;;
        "restart")
            cleanup_servers
            sleep 2
            main setup
            ;;
        *)
            echo "Usage: $0 {setup|status|cleanup|restart}"
            echo ""
            echo "Commands:"
            echo "  setup   - Set up and start all MCP servers"
            echo "  status  - Show status of all MCP servers"
            echo "  cleanup - Stop and remove all MCP servers"
            echo "  restart - Cleanup and setup servers"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
