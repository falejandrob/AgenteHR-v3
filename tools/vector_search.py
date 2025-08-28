"""
Enhanced document search system with LangChain and FAISS
Semantic vector search for better accuracy
"""
import os
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
import pickle

from langchain.text_splitter import RecursiveCharacterTextSplitter
"""Vector search helper with graceful fallback.

Recent changes:
 - Use import from langchain_community to avoid deprecation warning.
 - Robust vectorstore loading detecting 'allow_dangerous_deserialization' support.
 - Clearer log messages to distinguish benign warnings from critical errors.
"""

from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from config.langchain_config import get_azure_embeddings

logger = logging.getLogger(__name__)

class VectorDocumentSearch:
    def __init__(self, documents_path: str = "data/documents", vector_store_path: str = "data/vectorstore"):
        self.documents_path = Path(documents_path)
        self.vector_store_path = Path(vector_store_path)
        
        # Use basic embeddings for now until Azure is properly configured
        try:
            self.embeddings = get_azure_embeddings()
        except Exception as e:
            logger.warning(f"Error with Azure embeddings: {e}")
            # Fallback to keyword search system
            self.embeddings = None
            self.use_keyword_search = True
            logger.info("Using keyword search as fallback")
        else:
            self.use_keyword_search = False
            
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
    def load_documents(self) -> List[Document]:
        """
        Load documents from JSON files
        """
        documents = []
        
        if not self.documents_path.exists():
            logger.warning(f"Documents directory not found: {self.documents_path}")
            return documents
            
        for file_path in self.documents_path.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if isinstance(data, list):
                    for item in data:
                        doc = Document(
                            page_content=item.get('content', ''),
                            metadata={
                                'source': str(file_path),
                                'title': item.get('title', ''),
                                'type': item.get('type', ''),
                                'category': item.get('category', '')
                            }
                        )
                        documents.append(doc)
                else:
                    doc = Document(
                        page_content=data.get('content', ''),
                        metadata={
                            'source': str(file_path),
                            'title': data.get('title', ''),
                            'type': data.get('type', ''),
                            'category': data.get('category', '')
                        }
                    )
                    documents.append(doc)
                    
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                
        logger.info(f"Loaded {len(documents)} documents")
        return documents
    
    def create_vectorstore(self) -> bool:
        """
        Create the vector store from the documents
        """
        if self.use_keyword_search:
            logger.info("Using keyword search - vectorstore not required")
            return True
            
        try:
            documents = self.load_documents()
            if not documents:
                logger.error("No documents to process")
                return False
                
            # Split documents into chunks
            texts = self.text_splitter.split_documents(documents)
            logger.info(f"Documents split into {len(texts)} chunks")
            
            # Create vectorstore
            self.vectorstore = FAISS.from_documents(texts, self.embeddings)
            
            # Save vectorstore
            self.vector_store_path.mkdir(parents=True, exist_ok=True)
            self.vectorstore.save_local(str(self.vector_store_path))
            
            logger.info("Vectorstore created and saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating vectorstore: {e}")
            # Switch to keyword search
            self.use_keyword_search = True
            self.embeddings = None
            logger.info("Switching to keyword search")
            return True
    
    def load_vectorstore(self) -> bool:
        """
        Load the existing vector store
        """
        if self.use_keyword_search:
            logger.info("Using keyword search - no vectorstore to load")
            return True
            
        try:
            if not self.vector_store_path.exists():
                logger.warning("Vectorstore not found, creating new one...")
                return self.create_vectorstore()
                
            # Try loading detecting if the signature supports the parameter
            load_kwargs = {}
            try:
                import inspect
                params = inspect.signature(FAISS.load_local).parameters
                if 'allow_dangerous_deserialization' in params:
                    load_kwargs['allow_dangerous_deserialization'] = True
            except Exception:
                pass  # If inspection fails, continue without the parameter

            try:
                self.vectorstore = FAISS.load_local(
                    str(self.vector_store_path),
                    self.embeddings,
                    **load_kwargs
                )
            except TypeError as te:
                # Retry without kwargs in case of old version
                logger.warning(f"Retrying vectorstore load without extra parameters: {te}")
                self.vectorstore = FAISS.load_local(
                    str(self.vector_store_path),
                    self.embeddings
                )

            logger.info("Vectorstore loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading vectorstore: {e}")
            logger.info("Attempting to recreate vectorstore...")
            return self.create_vectorstore()
    
    def search(self, query: str, k: int = None) -> List[Dict]:
        """
        Search similar documents using vector search or keyword search
        """
        # Use environment variable or default
        if k is None:
            k = int(os.getenv("SEARCH_RESULTS_COUNT", "15"))
            
        try:
            if self.use_keyword_search:
                return self._keyword_search(query, k)
            
            if not self.vectorstore:
                if not self.load_vectorstore():
                    return self._keyword_search(query, k)
            
            # Similarity search
            docs = self.vectorstore.similarity_search_with_score(query, k=k)
            
            results = []
            for doc, score in docs:
                result = {
                    'content': doc.page_content,
                    'score': float(score),
                    'metadata': doc.metadata,
                    'title': doc.metadata.get('title', ''),
                    'source': doc.metadata.get('source', ''),
                    'type': doc.metadata.get('type', ''),
                    'category': doc.metadata.get('category', '')
                }
                results.append(result)
                
            logger.info(f"Found {len(results)} relevant documents")
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return self._keyword_search(query, k)
    
    def _keyword_search(self, query: str, k: int = 15) -> List[Dict]:
        """
        Keyword search as fallback
        """
        try:
            documents = self.load_documents()
            if not documents:
                return []
            
            query_words = set(query.lower().split())
            scored_docs = []
            
            for doc in documents:
                content_words = set(doc.page_content.lower().split())
                title_words = set(doc.metadata.get('title', '').lower().split())
                
                # Calculate score based on matching words
                content_matches = len(query_words.intersection(content_words))
                title_matches = len(query_words.intersection(title_words)) * 2  # Higher weight for title
                
                score = content_matches + title_matches
                
                if score > 0:
                    result = {
                        'content': doc.page_content,
                        'score': score,
                        'metadata': doc.metadata,
                        'title': doc.metadata.get('title', ''),
                        'source': doc.metadata.get('source', ''),
                        'type': doc.metadata.get('type', ''),
                        'category': doc.metadata.get('category', '')
                    }
                    scored_docs.append(result)
            
            # Sort by score descending
            scored_docs.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"Keyword search: {len(scored_docs[:k])} results")
            return scored_docs[:k]
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
    
    def get_context(self, results: List[Dict], max_length: int = 3000) -> str:
        """
        Extract optimized context from the results
        """
        if not results:
            return ""
            
        context_parts = []
        current_length = 0
        
        for result in results:
            content = result['content'].strip()
            title = result.get('title', '')
            
            # Format the chunk with title if available
            if title:
                chunk = f"**{title}**\n{content}\n"
            else:
                chunk = f"{content}\n"
                
            # Check if we can add this chunk
            if current_length + len(chunk) <= max_length:
                context_parts.append(chunk)
                current_length += len(chunk)
            else:
                # Add as much as we can from the current chunk
                remaining = max_length - current_length
                if remaining > 100:  # Only if significant space is left
                    truncated = chunk[:remaining-3] + "..."
                    context_parts.append(truncated)
                break
        
        return "\n".join(context_parts)
    
    def rebuild_index(self) -> bool:
        """
        Completely rebuild the vector index
        """
        logger.info("Rebuilding vector index...")
        
        # Remove existing vectorstore
        if self.vector_store_path.exists():
            import shutil
            shutil.rmtree(self.vector_store_path)
            
        return self.create_vectorstore()

# Global instance for reuse
document_search = VectorDocumentSearch()
