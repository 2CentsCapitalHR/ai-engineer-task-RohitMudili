#!/usr/bin/env python3
"""
Startup script for ADGM Corporate Agent
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import streamlit
        import chromadb
        import openai
        import pydantic
        print("✅ All required dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_environment():
    """Check environment setup"""
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found")
        print("Please copy env.example to .env and configure your API keys")
        return False
    
    # Check OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key or openai_key == "your_openai_api_key_here":
        print("⚠️  OpenAI API key not configured")
        print("Please set OPENAI_API_KEY in your .env file")
        return False
    
    print("✅ Environment is properly configured")
    return True

def check_database():
    """Check if database exists"""
    chroma_path = Path("chroma_db")
    if not chroma_path.exists():
        print("⚠️  Document database not found")
        print("Initializing database...")
        try:
            subprocess.run([sys.executable, "-m", "core.ingest", "refresh"], check=True)
            print("✅ Database initialized successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to initialize database: {e}")
            return False
    else:
        print("✅ Document database found")
    
    return True

def start_application():
    """Start the Streamlit application"""
    print("🚀 Starting ADGM Corporate Agent...")
    print("📱 Opening browser at http://localhost:8501")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "app/streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")

def main():
    """Main startup function"""
    print("🏢 ADGM Corporate Agent")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check database
    if not check_database():
        sys.exit(1)
    
    print("=" * 50)
    
    # Start application
    start_application()

if __name__ == "__main__":
    main()
