#!/usr/bin/env python3
"""
Simple script to run the ADGM document ingestion
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ingest import DocumentIngester

def main():
    print("Starting ADGM document ingestion...")
    
    try:
        # Initialize ingester
        ingester = DocumentIngester()
        
        # Run refresh
        ingester.refresh()
        
        print("✅ Document ingestion completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
