@echo off
REM Startup Simulator 3000 - Quick Start Script for Windows
REM This script helps you get the application running quickly on Windows

echo 🚀 Startup Simulator 3000 - Quick Start
echo ========================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH. Please install Python 3.10+ first.
    pause
    exit /b 1
)

echo ✅ Python detected

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Check if .env file exists
if not exist ".env" (
    echo ⚠️  No .env file found!
    echo 📝 Creating .env file from template...
    copy .env.example .env
    echo 🔑 Please edit .env file with your API keys:
    echo    - OPENAI_API_KEY (required)
    echo    - NEWS_API_KEY (for serious mode)
    echo    - SPLUNK_AO_API_KEY (optional, for observability)
    echo.
    echo You can edit it with: notepad .env
    echo.
    pause
)

REM Check if OpenAI API key is set
findstr /C:"OPENAI_API_KEY=sk-" .env >nul 2>&1
if errorlevel 1 (
    echo ❌ OPENAI_API_KEY not properly configured in .env file
    echo Please edit .env and add your OpenAI API key
    pause
    exit /b 1
)

echo ✅ Environment configured

REM Start the application
echo 🌐 Starting Startup Simulator 3000...
echo 📱 Open your browser to: http://localhost:2021
echo 🛑 Press Ctrl+C to stop the server
echo.

python app.py 