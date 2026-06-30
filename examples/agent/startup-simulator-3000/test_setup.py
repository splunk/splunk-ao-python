#!/usr/bin/env python3
"""
Test script to verify Startup Simulator 3000 setup
Run this script to check if everything is configured correctly
"""

import os
import sys
import importlib
from dotenv import load_dotenv


def test_python_version():
    """Test if Python version is compatible"""
    print("🐍 Testing Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} is too old. Need Python 3.8+")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True


def test_dependencies():
    """Test if all required dependencies are installed"""
    print("\n📦 Testing dependencies...")
    required_packages = [
        "flask",
        "openai",
        "galileo",
        "requests",
        "python-dotenv",
        "aiohttp",
        "langchain",
    ]

    missing_packages = []
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - not installed")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("✅ All dependencies installed")
    return True


def test_environment():
    """Test environment configuration"""
    print("\n🔧 Testing environment configuration...")

    # Load .env file
    load_dotenv()

    # Check required environment variables
    required_vars = ["OPENAI_API_KEY"]
    optional_vars = ["NEWS_API_KEY", "SPLUNK_AO_API_KEY", "SPLUNK_AO_PROJECT"]

    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == f"your-{var.lower().replace('_', '-')}-here":
            print(f"❌ {var} - not set or using placeholder")
            missing_required.append(var)
        else:
            print(f"✅ {var} - configured")

    if missing_required:
        print(f"\n⚠️  Missing required environment variables: {', '.join(missing_required)}")
        print("Please edit .env file with your API keys")
        return False

    # Check optional variables
    for var in optional_vars:
        value = os.getenv(var)
        if value and value != f"your {var.lower().replace('_', ' ')} here":
            print(f"✅ {var} - configured")
        else:
            print(f"⚠️  {var} - not set (optional)")

    return True


def test_imports():
    """Test if all project modules can be imported"""
    print("\n📚 Testing project imports...")

    try:
        from agent_framework.llm.openai_provider import OpenAIProvider

        _ = OpenAIProvider
        print("✅ agent_framework.llm.openai_provider")
    except ImportError as e:
        print(f"❌ agent_framework.llm.openai_provider - {e}")
        return False

    try:
        from tools.startup_simulator import StartupSimulatorTool

        _ = StartupSimulatorTool
        print("✅ tools.startup_simulator")
    except ImportError as e:
        print(f"❌ tools.startup_simulator - {e}")
        return False

    try:
        from agent import SimpleAgent

        _ = SimpleAgent
        print("✅ agent")
    except ImportError as e:
        print(f"❌ agent - {e}")
        return False

    try:
        from splunk_ao import SplunkAOLogger

        _ = SplunkAOLogger
        print("✅ splunk_ao")
    except ImportError as e:
        print(f"❌ splunk_ao - {e}")
        return False

    return True


def test_files():
    """Test if all required files exist"""
    print("\n📁 Testing file structure...")

    required_files = [
        "app.py",
        "agent.py",
        "requirements.txt",
        ".env.example",
        "tools.json",
        "templates/index.html",
        "static/css/style.css",
        "static/js/app.js",
    ]

    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - missing")
            missing_files.append(file_path)

    if missing_files:
        print(f"\n⚠️  Missing files: {', '.join(missing_files)}")
        return False

    return True


def main():
    """Run all tests"""
    print("🚀 Startup Simulator 3000 - Setup Test")
    print("=" * 50)

    tests = [
        test_python_version,
        test_dependencies,
        test_environment,
        test_imports,
        test_files,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with error: {e}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        print("\n🚀 To start the application:")
        print("   python app.py")
        print("   Then open: http://localhost:2021")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\n💡 Common solutions:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Configure API keys in .env file")
        print("   3. Make sure you're in the virtual environment")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
