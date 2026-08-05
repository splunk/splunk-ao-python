#!/bin/bash

# Startup Simulator 3000 - Quick Start Script
# This script helps you get the application running quickly

echo "🚀 Startup Simulator 3000 - Quick Start"
echo "========================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10+ first."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python version $python_version is too old. Please install Python 3.10+"
    exit 1
fi

echo "✅ Python $python_version detected"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found!"
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "🔑 Please edit .env file with your API keys:"
    echo "   - OPENAI_API_KEY (required)"
    echo "   - NEWS_API_KEY (for serious mode)"
    echo "   - SPLUNK_AO_API_KEY (optional, for observability)"
    echo ""
    echo "You can edit it with: nano .env"
    echo ""
    read -p "Press Enter after you've configured your API keys..."
fi

# Check if OpenAI API key is set
if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
    echo "❌ OPENAI_API_KEY not properly configured in .env file"
    echo "Please edit .env and add your OpenAI API key"
    exit 1
fi

echo "✅ Environment configured"

# Start the application
echo "🌐 Starting Startup Simulator 3000..."
echo "📱 Open your browser to: http://localhost:2021"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

python app.py 