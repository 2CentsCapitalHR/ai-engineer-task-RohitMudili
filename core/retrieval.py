import os
import chromadb
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from bge_reranker import BGEReranker
import logging

from .utils import setup_logging, load_yaml_config

logger = setup_logging(__name__)

class DocumentRetriever:
    def __init__(self, chroma_path: str = "chroma_db", config_path: str = "config/settings.yml"):
        self.chroma_path = chroma_path
        self.config = load_yaml_config(config_path)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_collection("adgm_documents")
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('text-embedding-3-large')
        
        # Initialize reranker
        self.reranker = BGEReranker('BAAI/bge-reranker-large')
        
        # Configuration
        self.top_k = self.config.get('rag', {}).get('top_k', 8)
        self.rerank_k = self.config.get('rag', {}).get('rerank_k', 6)
        self.min_score = self.config.get('rag', {}).get('min_score', 0.35)
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a query using the embedding model"""
        try:
            embedding = self.embedding_model.encode(query)
            return embedding.tolist()
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
        """Rerank documents using BGE reranker"""
        if rerank_k is None:
            rerank_k = self.rerank_k
        
        if not documents:
            return []
        
        try:
            # Prepare documents for reranking
            doc_texts = [doc['text'] for doc in documents]
            
            # Rerank
            rerank_scores = self.reranker.compute_score(query, doc_texts)
            
            # Update documents with rerank scores
            for i, doc in enumerate(documents):
                doc['rerank_score'] = rerank_scores[i]
            
            # Sort by rerank score and take top k
            reranked_docs = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)[:rerank_k]
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Error reranking documents: {e}")
            return documents[:rerank_k]  # Fallback to original order
    
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
            # Use ChromaDB's where clause to filter by tags
            where_clause = {"tags": {"$in": tags}}
            
            results = self.collection.get(
                where=where_clause,
                include=['documents', 'metadatas']
            )
            
            documents = []
            if results['documents']:
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
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
                        all_tags.extend(metadata['tags'])
            
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
