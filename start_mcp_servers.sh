#!/bin/bash

# Start MCP servers for the demo

echo "🚀 Starting MCP servers..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Kill any existing servers on these ports
echo "Stopping any existing servers..."
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
lsof -ti:3002 | xargs kill -9 2>/dev/null || true
lsof -ti:3003 | xargs kill -9 2>/dev/null || true

# Start servers in background
echo "Starting Brave Search MCP Server on port 3001..."
python mcp_servers/brave_search_server.py &
BRAVE_PID=$!

echo "Starting GitHub MCP Server on port 3002..."
python mcp_servers/github_server.py &
GITHUB_PID=$!

echo "Starting Hacker News MCP Server on port 3003..."
python mcp_servers/hacker_news_server.py &
HN_PID=$!

echo ""
echo "✅ MCP servers started!"
echo "   - Brave Search: http://localhost:3001 (PID: $BRAVE_PID)"
echo "   - GitHub: http://localhost:3002 (PID: $GITHUB_PID)"
echo "   - Hacker News: http://localhost:3003 (PID: $HN_PID)"
echo ""
echo "To stop servers, run: kill $BRAVE_PID $GITHUB_PID $HN_PID"
echo ""

# Keep script running
wait