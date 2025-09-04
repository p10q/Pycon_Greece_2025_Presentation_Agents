#!/bin/bash
# Quick activation script for the HN GitHub Agents project

echo "🚀 Activating HN GitHub Agents environment..."

# Activate virtual environment
source .venv/bin/activate

echo "✅ Virtual environment activated!"
echo "📍 Current directory: $(pwd)"
echo "🐍 Python version: $(python --version)"
echo "📦 FastAPI version: $(python -c "import fastapi; print(fastapi.__version__)" 2>/dev/null || echo 'Not installed')"

echo ""
echo "Ready to run:"
echo "  python -m app.main              # Start the application"
echo "  python scripts/verify_setup.py  # Verify setup"
echo "  ./scripts/setup_mcp_servers.sh  # Setup MCP servers"
echo ""

# Keep the shell active with the virtual environment
exec $SHELL

