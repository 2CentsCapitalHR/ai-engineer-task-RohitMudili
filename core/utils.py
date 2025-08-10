import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """Load YAML configuration file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        raise Exception(f"Error loading config file {file_path}: {e}")

def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent

def ensure_directory(path: str) -> None:
    """Ensure directory exists, create if it doesn't"""
    Path(path).mkdir(parents=True, exist_ok=True)

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = " ".join(text.split())
    
    # Remove common unwanted characters
    text = text.replace('\x00', '')
    
    return text.strip()

def extract_filename_without_extension(file_path: str) -> str:
    """Extract filename without extension"""
    return Path(file_path).stem

def get_file_extension(file_path: str) -> str:
    """Get file extension"""
    return Path(file_path).suffix.lower()

def is_docx_file(file_path: str) -> bool:
    """Check if file is a .docx file"""
    return get_file_extension(file_path) == '.docx'

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 120) -> List[str]:
    """Split text into overlapping chunks"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            for i in range(end, max(start + chunk_size - 100, start), -1):
                if text[i] in '.!?':
                    end = i + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary with default"""
    return dictionary.get(key, default)

def format_citation(source_url: str, section: Optional[str] = None) -> str:
    """Format citation for display"""
    if section:
        return f"{source_url} (Section: {section})"
    return source_url
