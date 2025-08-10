import os
import chromadb
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import openai
import logging

from .utils import setup_logging, load_yaml_config

logger = setup_logging()

class DocumentRetriever:
    def __init__(self, chroma_path: str = "chroma_db", config_path: str = "config/settings.yml"):
        self.chroma_path = chroma_path
        self.config = load_yaml_config(config_path)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_collection("adgm_documents")
        
        # Initialize OpenAI client
        self.openai_client = openai.OpenAI()
        
        # Configuration
        self.top_k = self.config.get('rag', {}).get('top_k', 8)
        self.rerank_k = self.config.get('rag', {}).get('rerank_k', 6)
        self.min_score = self.config.get('rag', {}).get('min_score', 0.35)
        
        # Configuration
        self.top_k = self.config.get('rag', {}).get('top_k', 8)
        self.rerank_k = self.config.get('rag', {}).get('rerank_k', 6)
        self.min_score = self.config.get('rag', {}).get('min_score', 0.35)
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a query using OpenAI's embedding model"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=query
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            return []
    
    def retrieve_documents(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve documents from ChromaDB"""
        if top_k is None:
            top_k = self.top_k
        
        try:
            # Embed query
            query_embedding = self.embed_query(query)
            if not query_embedding:
                return []
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            documents = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 0
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    
                    # Convert distance to similarity score
                    similarity_score = 1 - distance
                    
                    documents.append({
                        'text': doc,
                        'metadata': metadata,
                        'similarity_score': similarity_score,
                        'distance': distance
                    })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
    
    def rerank_documents(self, query: str, documents: List[Dict[str, Any]], 
                        rerank_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Rerank documents using OpenAI's embedding similarity"""
        if rerank_k is None:
            rerank_k = self.rerank_k
        
        if not documents:
            return []
        
        try:
            # Get embeddings for query and documents
            query_embedding = self.embed_query(query)
            if not query_embedding:
                return documents[:rerank_k]
            
            # Get embeddings for all documents
            doc_texts = [doc['text'] for doc in documents]
            doc_embeddings_response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=doc_texts
            )
            doc_embeddings = [item.embedding for item in doc_embeddings_response.data]
            
            # Calculate cosine similarities
            similarities = []
            for doc_embedding in doc_embeddings:
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                similarities.append(similarity)
            
            # Update documents with similarity scores
            for i, doc in enumerate(documents):
                doc['rerank_score'] = similarities[i]
            
            # Sort by similarity score and take top k
            reranked_docs = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)[:rerank_k]
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Error reranking documents: {e}")
            return documents[:rerank_k]  # Fallback to original order
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0
    
    def filter_by_score(self, documents: List[Dict[str, Any]], 
                       min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """Filter documents by minimum similarity score"""
        if min_score is None:
            min_score = self.min_score
        
        return [doc for doc in documents if doc.get('similarity_score', 0) >= min_score]
    
    def retrieve_and_rerank(self, query: str) -> List[Dict[str, Any]]:
        """Complete retrieval pipeline: embed → retrieve → rerank → filter"""
        logger.info(f"Processing query: {query}")
        
        # Step 1: Retrieve documents
        documents = self.retrieve_documents(query)
        logger.info(f"Retrieved {len(documents)} documents")
        
        if not documents:
            return []
        
        # Step 2: Rerank documents
        reranked_docs = self.rerank_documents(query, documents)
        logger.info(f"Reranked to {len(reranked_docs)} documents")
        
        # Step 3: Filter by score
        filtered_docs = self.filter_by_score(reranked_docs)
        logger.info(f"Filtered to {len(filtered_docs)} documents above threshold")
        
        return filtered_docs
    
    def get_citations(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Extract citations from retrieved documents"""
        citations = []
        seen_urls = set()
        
        for doc in documents:
            metadata = doc.get('metadata', {})
            source_url = metadata.get('source_url', '')
            
            if source_url and source_url not in seen_urls:
                citations.append(source_url)
                seen_urls.add(source_url)
        
        return citations
    
    def format_context_for_llm(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents as context for LLM"""
        if not documents:
            return "No relevant documents found."
        
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            metadata = doc.get('metadata', {})
            source_url = metadata.get('source_url', 'Unknown source')
            title = metadata.get('title', 'Untitled')
            
            context_parts.append(f"Document {i}: {title}")
            context_parts.append(f"Source: {source_url}")
            context_parts.append(f"Content: {doc['text']}")
            context_parts.append("---")
        
        return "\n".join(context_parts)
    
    def search_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """Search documents by tags"""
        try:
            # Since tags are stored as comma-separated strings, we need to search differently
            # Get all documents and filter by tags
            results = self.collection.get(
                include=['documents', 'metadatas']
            )
            
            documents = []
            if results['documents']:
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    doc_tags = metadata.get('tags', '').split(',') if metadata.get('tags') else []
                    
                    # Check if any of the requested tags are in the document's tags
                    if any(tag.strip() in doc_tags for tag in tags):
                        documents.append({
                            'text': doc,
                            'metadata': metadata
                        })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching by tags: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the document collection"""
        try:
            count = self.collection.count()
            
            # Get sample documents to analyze tags
            sample_results = self.collection.get(limit=1000)
            all_tags = []
            
            if sample_results['metadatas']:
                for metadata in sample_results['metadatas']:
                    if metadata and 'tags' in metadata:
                        tags_str = metadata['tags']
                        if tags_str:
                            all_tags.extend([tag.strip() for tag in tags_str.split(',')])
            
            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            return {
                'total_documents': count,
                'tag_distribution': tag_counts,
                'sample_size': len(sample_results['documents']) if sample_results['documents'] else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {'error': str(e)}
