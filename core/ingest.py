import os
import requests
import chromadb
from pathlib import Path
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import PyPDF2
import io
import hashlib
from datetime import datetime
import logging

from .utils import load_yaml_config, setup_logging, chunk_text, clean_text, get_project_root, ensure_directory

logger = setup_logging(__name__)

class DocumentIngester:
    def __init__(self, sources_path: str = "ingest/sources.yml", chroma_path: str = "chroma_db"):
        self.sources_config = load_yaml_config(sources_path)
        self.chroma_path = chroma_path
        self.chunk_size = self.sources_config.get('options', {}).get('chunk_size', 1000)
        self.chunk_overlap = self.sources_config.get('options', {}).get('chunk_overlap', 120)
        
        # Initialize ChromaDB
        ensure_directory(chroma_path)
        self.client = chromadb.PersistentClient(path=chroma_path)
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="adgm_documents",
            metadata={"description": "ADGM regulatory documents and guidance"}
        )
    
    def fetch_html_content(self, url: str) -> Optional[str]:
        """Fetch and parse HTML content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text()
            return clean_text(text)
            
        except Exception as e:
            logger.error(f"Error fetching HTML from {url}: {e}")
            return None
    
    def fetch_pdf_content(self, url: str) -> Optional[str]:
        """Fetch and parse PDF content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return clean_text(text)
            
        except Exception as e:
            logger.error(f"Error fetching PDF from {url}: {e}")
            return None
    
    def extract_metadata(self, source: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Extract metadata from source and content"""
        metadata = {
            "source_url": source["url"],
            "type": source["type"],
            "tags": source.get("tags", []),
            "title": self._extract_title(content),
            "effective_date": self._extract_date(content),
            "published_date": datetime.now().isoformat(),
            "content_length": len(content)
        }
        return metadata
    
    def _extract_title(self, content: str) -> str:
        """Extract title from content"""
        # Simple heuristic: first line that's not too long
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if 10 < len(line) < 200 and not line.isupper():
                return line
        return "Untitled Document"
    
    def _extract_date(self, content: str) -> str:
        """Extract date from content"""
        # Simple date extraction - could be enhanced
        import re
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content[:2000])  # Search first 2000 chars
            if match:
                return match.group()
        
        return datetime.now().strftime("%Y-%m-%d")
    
    def process_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single source and return chunks with metadata"""
        url = source["url"]
        source_type = source["type"]
        
        logger.info(f"Processing {source_type} source: {url}")
        
        # Fetch content based on type
        if source_type == "html":
            content = self.fetch_html_content(url)
        elif source_type == "pdf":
            content = self.fetch_pdf_content(url)
        else:
            logger.warning(f"Unsupported source type: {source_type}")
            return []
        
        if not content:
            logger.warning(f"No content retrieved from {url}")
            return []
        
        # Extract metadata
        metadata = self.extract_metadata(source, content)
        
        # Chunk content
        chunks = chunk_text(content, self.chunk_size, self.chunk_overlap)
        
        # Create documents for each chunk
        documents = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_id": f"{hashlib.md5(url.encode()).hexdigest()}_{i}"
            })
            
            documents.append({
                "text": chunk,
                "metadata": chunk_metadata
            })
        
        return documents
    
    def ingest_all_sources(self) -> None:
        """Ingest all sources from sources.yml"""
        sources = self.sources_config.get("sources", [])
        
        logger.info(f"Starting ingestion of {len(sources)} sources")
        
        all_documents = []
        
        for source in sources:
            try:
                documents = self.process_source(source)
                all_documents.extend(documents)
                logger.info(f"Processed {len(documents)} chunks from {source['url']}")
            except Exception as e:
                logger.error(f"Error processing source {source['url']}: {e}")
                continue
        
        # Add to ChromaDB
        if all_documents:
            texts = [doc["text"] for doc in all_documents]
            metadatas = [doc["metadata"] for doc in all_documents]
            ids = [doc["metadata"]["chunk_id"] for doc in all_documents]
            
            # Clear existing collection
            self.collection.delete(where={})
            
            # Add new documents
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully ingested {len(all_documents)} document chunks")
        else:
            logger.warning("No documents to ingest")
    
    def refresh(self) -> None:
        """Refresh the document collection"""
        logger.info("Starting document refresh...")
        self.ingest_all_sources()
        logger.info("Document refresh completed")

def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ADGM Document Ingester")
    parser.add_argument("command", choices=["refresh"], help="Command to run")
    parser.add_argument("--sources", default="ingest/sources.yml", help="Path to sources.yml")
    parser.add_argument("--chroma-path", default="chroma_db", help="Path to ChromaDB")
    
    args = parser.parse_args()
    
    if args.command == "refresh":
        ingester = DocumentIngester(args.sources, args.chroma_path)
        ingester.refresh()

if __name__ == "__main__":
    main()
