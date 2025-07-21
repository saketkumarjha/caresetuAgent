"""
ChromaDB Cloud Vector Store Integration
Handles connection to ChromaDB Cloud for vector search with company isolation
"""

import chromadb
import logging
import hashlib
import time
import re
import json
import os
from typing import List, Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudVectorStore:
    """
    ChromaDB Cloud Vector Store for semantic search with multi-tenant support
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 tenant: Optional[str] = None,
                 database: Optional[str] = None):
        """
        Initialize ChromaDB Cloud client
        
        Args:
            api_key: ChromaDB Cloud API key
            tenant: ChromaDB Cloud tenant ID
            database: ChromaDB Cloud database name
        """
        self.api_key = api_key or os.environ.get("CHROMADB_API_KEY")
        self.tenant = tenant or os.environ.get("CHROMADB_TENANT")
        self.database = database or os.environ.get("CHROMADB_DATABASE")
        
        if not self.api_key:
            raise ValueError("ChromaDB Cloud API key is required")
        if not self.tenant:
            raise ValueError("ChromaDB Cloud tenant is required")
        if not self.database:
            raise ValueError("ChromaDB Cloud database is required")
        
        # Initialize ChromaDB Cloud client using the correct format
        try:
            self.client = chromadb.CloudClient(
                api_key=self.api_key,
                tenant=self.tenant,
                database=self.database
            )
            logger.info(f"✅ Connected to ChromaDB Cloud - Tenant: {self.tenant}, Database: {self.database}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to ChromaDB Cloud: {e}")
            raise
        
        # Track collections for each company
        self.company_collections = {}
        self.search_cache = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
    
    def get_collection(self, company_id: str, collection_type: str) -> "CloudSecureCollection":
        """
        Get or create a collection for a company
        
        Args:
            company_id: Company identifier
            collection_type: Collection type (e.g., privacy_policy, appointment_guide)
            
        Returns:
            CloudSecureCollection instance
        """
        collection_key = f"{company_id}_{collection_type}"
        
        if collection_key not in self.company_collections:
            self.company_collections[collection_key] = CloudSecureCollection(
                self.client,
                company_id,
                collection_type,
                self
            )
        
        return self.company_collections[collection_key]
    
    def list_company_collections(self, company_id: str) -> List[str]:
        """
        List all collections for a company
        
        Args:
            company_id: Company identifier
            
        Returns:
            List of collection names
        """
        try:
            collections = self.client.list_collections()
            company_collections = [
                collection.name for collection in collections
                if collection.name.startswith(f"{company_id}_")
            ]
            return company_collections
        except Exception as e:
            logger.error(f"❌ Error listing collections for {company_id}: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic statistics about the cloud vector store."""
        try:
            collections = self.client.list_collections()
            return {
                "total_collections": len(collections),
                "company_collections": len(self.company_collections),
                "cache_size": len(self.search_cache)
            }
        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
            return {"error": str(e)}

class CloudSecureCollection:
    """Secure collection with company isolation for ChromaDB Cloud."""
    
    def __init__(self, client, company_id: str, collection_type: str, vector_store):
        """
        Initialize secure collection for ChromaDB Cloud
        
        Args:
            client: ChromaDB Cloud client
            company_id: Company identifier
            collection_type: Type of collection
            vector_store: Parent vector store instance
        """
        self.client = client
        self.company_id = company_id
        self.collection_type = collection_type
        self.vector_store = vector_store
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """Get or create collection with proper metadata."""
        collection_name = f"{self.company_id}_{self.collection_type}"
        
        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "company_id": self.company_id,
                    "type": self.collection_type,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            )
            logger.info(f"✅ Using collection: {collection_name}")
            return collection
        except Exception as e:
            logger.error(f"❌ Error getting collection {collection_name}: {e}")
            raise
    
    def add_documents(self, ids: List[str], documents: List[str], 
                     metadatas: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Add documents to collection with security validation
        
        Args:
            ids: Document IDs
            documents: Document contents
            metadatas: Document metadata
            
        Returns:
            Success status
        """
        # Validate company access
        self._validate_company_access()
        
        # Ensure all metadatas have company_id
        if metadatas:
            for i, metadata in enumerate(metadatas):
                if metadata is None:
                    metadatas[i] = {"company_id": self.company_id}
                else:
                    metadata["company_id"] = self.company_id
        else:
            metadatas = [{"company_id": self.company_id} for _ in range(len(documents))]
        
        try:
            # Using upsert to avoid duplicate documents
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"✅ Added {len(documents)} documents to {self.collection.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding documents to {self.collection.name}: {e}")
            return False
    
    def search(self, query_text: str, n_results: int = 5, 
              filters: Optional[Dict[str, Any]] = None, 
              use_hybrid: bool = True) -> Dict[str, Any]:
        """
        Search collection with security validation and hybrid search capabilities
        
        Args:
            query_text: Query text
            n_results: Number of results to return
            filters: Additional filters
            use_hybrid: Whether to use hybrid search (vector + keyword)
            
        Returns:
            Search results with relevance scores
        """
        # Validate company access
        self._validate_company_access()
        
        # Check cache first
        cache_key = self._get_cache_key(query_text, filters, n_results)
        cached_results = self._get_from_cache(cache_key)
        if cached_results:
            logger.debug(f"Cache hit for query: '{query_text}'")
            return cached_results
        
        # Build where clause with company isolation
        where_clause = {"company_id": self.company_id}
        if filters:
            where_clause.update(filters)
        
        try:
            # Perform vector search
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results * 2 if use_hybrid else n_results,  # Get more results for hybrid reranking
                where=where_clause
            )
            
            # Apply hybrid search if enabled
            if use_hybrid and results["documents"] and results["documents"][0]:
                results = self._apply_hybrid_search(query_text, results, n_results)
            
            # Log the search operation
            self._log_search_operation(query_text, results)
            
            # Cache results
            self._add_to_cache(cache_key, results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching {self.collection.name}: {e}")
            return {"documents": [[]], "ids": [[]], "distances": [[]], "metadatas": [[]], "relevance_scores": [[]]}
    
    def _validate_company_access(self):
        """Validate company access permissions."""
        # In a real implementation, this would check user permissions
        logger.debug(f"Access validated for company: {self.company_id}")
    
    def _log_search_operation(self, query: str, results: Dict[str, Any]):
        """Log search operation for audit purposes."""
        doc_count = len(results["documents"][0]) if results["documents"] and results["documents"][0] else 0
        logger.info(f"🔍 Search in {self.collection.name}: query='{query}', results={doc_count}")
    
    def _apply_hybrid_search(self, query_text: str, vector_results: Dict[str, Any], n_results: int) -> Dict[str, Any]:
        """
        Apply hybrid search by combining vector similarity with keyword matching
        
        Args:
            query_text: Query text
            vector_results: Vector search results
            n_results: Number of results to return
            
        Returns:
            Reranked search results
        """
        # Extract keywords from query
        keywords = self._extract_keywords(query_text)
        
        # Calculate hybrid scores
        hybrid_scores = []
        
        for i, (doc, distance) in enumerate(zip(vector_results["documents"][0], vector_results["distances"][0])):
            # Calculate keyword match score
            keyword_score = self._calculate_keyword_score(doc, keywords)
            
            # Calculate vector score (lower distance is better, so invert it)
            vector_score = 1.0 - min(distance, 1.0)  # Normalize to 0-1 range
            
            # Combine scores (70% vector, 30% keyword by default)
            combined_score = (vector_score * 0.7) + (keyword_score * 0.3)
            
            hybrid_scores.append((i, combined_score))
        
        # Sort by combined score
        hybrid_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Take top n_results
        top_indices = [idx for idx, _ in hybrid_scores[:n_results]]
        
        # Create reranked results
        reranked_results = {
            "documents": [[vector_results["documents"][0][i] for i in top_indices]],
            "ids": [[vector_results["ids"][0][i] for i in top_indices]],
            "distances": [[vector_results["distances"][0][i] for i in top_indices]],
            "metadatas": [[vector_results["metadatas"][0][i] for i in top_indices]] if vector_results["metadatas"] else None,
            "relevance_scores": [[score for _, score in hybrid_scores[:n_results]]]
        }
        
        return reranked_results
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query for keyword matching."""
        # Simple keyword extraction (remove common words)
        common_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'like', 'through', 'over', 'before', 'between', 'after', 'since', 'without', 'under', 'within', 'along', 'following', 'across', 'behind', 'beyond', 'plus', 'except', 'but', 'up', 'out', 'around', 'down', 'off', 'above', 'near', 'and', 'or', 'but', 'so', 'yet', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'shall', 'should', 'may', 'might', 'must', 'of'}
        
        # Tokenize and filter
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [word for word in words if word not in common_words and len(word) > 2]
        
        return keywords
    
    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """Calculate keyword match score."""
        if not keywords:
            return 0.0
        
        text_lower = text.lower()
        
        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        
        # Calculate score based on percentage of keywords matched
        score = matches / len(keywords) if keywords else 0.0
        
        # Boost score for exact phrase match
        if ' '.join(keywords) in text_lower:
            score = min(score + 0.3, 1.0)
        
        return score
    
    def _get_cache_key(self, query_text: str, filters: Optional[Dict[str, Any]], n_results: int) -> str:
        """Generate cache key for search query."""
        key_parts = [query_text, str(n_results)]
        
        if filters:
            # Convert filters to stable string representation
            filter_str = json.dumps(filters, sort_keys=True)
            key_parts.append(filter_str)
        
        # Create a hash of the key parts
        key = "_".join(key_parts)
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get results from cache if available and not expired."""
        if cache_key in self.vector_store.search_cache:
            timestamp, results = self.vector_store.search_cache[cache_key]
            if time.time() - timestamp < self.vector_store.cache_ttl:
                return results
        return None
    
    def _add_to_cache(self, cache_key: str, results: Dict[str, Any]):
        """Add results to cache with timestamp."""
        self.vector_store.search_cache[cache_key] = (time.time(), results)
        
        # Clean cache if it gets too large
        if len(self.vector_store.search_cache) > 100:  # Limit cache size
            self._clean_cache()
    
    def _clean_cache(self):
        """Clean expired entries from cache."""
        current_time = time.time()
        expired_keys = []
        
        for key, (timestamp, _) in self.vector_store.search_cache.items():
            if current_time - timestamp > self.vector_store.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.vector_store.search_cache[key]

# Example usage and testing
if __name__ == "__main__":
    # Test ChromaDB Cloud connection
    try:
        # Initialize with your credentials
        cloud_store = CloudVectorStore(
            api_key='ck-8qMvVqpxS2ZPiA4rDDrPtT4Gjer1vawnCHNqANwqyxaF',
            tenant='952f5e15-854e-461e-83d1-3cef021c755c',
            database='Assembly_AI'
        )
        
        # Get a test collection
        test_collection = cloud_store.get_collection("test_company", "policies")
        
        # Test adding documents
        success = test_collection.add_documents(
            ids=["test_doc_1", "test_doc_2"],
            documents=[
                "This is a test privacy policy document for testing ChromaDB Cloud integration.",
                "This is a test appointment scheduling policy for testing vector search capabilities."
            ],
            metadatas=[
                {"category": "privacy", "type": "policy"},
                {"category": "scheduling", "type": "policy"}
            ]
        )
        
        if success:
            print("✅ Successfully added test documents to ChromaDB Cloud")
            
            # Test search
            results = test_collection.search("privacy policy")
            print(f"✅ Search results: {len(results['documents'][0])} documents found")
            
            # Get stats
            stats = cloud_store.get_stats()
            print(f"✅ Cloud store stats: {stats}")
        else:
            print("❌ Failed to add documents to ChromaDB Cloud")
            
    except Exception as e:
        print(f"❌ ChromaDB Cloud test failed: {e}")