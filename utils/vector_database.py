import chromadb
from chromadb.config import Settings
from config import Config
import json
import uuid
import os
import shutil

class VectorDatabaseManager:
    def __init__(self):
        self.client = None
        self.collection = None
        self.db_path = os.path.join("storage", "vector_db")
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize ChromaDB with error recovery"""
        try:
            # Create directory if not exists
            os.makedirs(self.db_path, exist_ok=True)
            
            # Try to initialize client
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(allow_reset=True)
            )
            
            # Try to get or create collection
            try:
                self.collection = self.client.get_or_create_collection(
                    name="document_embeddings",
                    metadata={"hnsw:space": "cosine"}
                )
                print("Vector database initialized successfully")
                
                # Test collection access
                _ = self.collection.count()
                print("Collection access test successful")
                
            except Exception as collection_error:
                print(f"Collection error: {collection_error}")
                # Try to reset collection
                self._reset_collection()
                
        except Exception as e:
            print(f"Error initializing vector database: {e}")
            # Try to recover by resetting entire database
            self._reset_database()
    
    def _reset_collection(self):
        """Reset the collection if it's corrupted"""
        try:
            print("Attempting to reset collection...")
            
            # Try to delete and recreate collection
            try:
                self.client.delete_collection("document_embeddings")
                print("Deleted corrupted collection")
            except:
                pass
            
            # Create new collection
            self.collection = self.client.create_collection(
                name="document_embeddings",
                metadata={"hnsw:space": "cosine"}
            )
            print("Collection reset successful")
            
        except Exception as e:
            print(f"Error resetting collection: {e}")
            raise e
    
    def _reset_database(self):
        """Reset entire vector database if initialization fails"""
        try:
            print("Attempting to reset entire vector database...")
            
            # Close client if exists
            if self.client:
                try:
                    self.client = None
                except:
                    pass
            
            # Backup and remove old database
            if os.path.exists(self.db_path):
                backup_path = f"{self.db_path}_backup_{uuid.uuid4().hex[:8]}"
                try:
                    shutil.move(self.db_path, backup_path)
                    print(f"Backed up old database to {backup_path}")
                except Exception as backup_error:
                    print(f"Backup failed: {backup_error}")
                    # Try to remove directly
                    try:
                        shutil.rmtree(self.db_path)
                    except:
                        pass
            
            # Create fresh database
            os.makedirs(self.db_path, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(allow_reset=True)
            )
            
            self.collection = self.client.create_collection(
                name="document_embeddings",
                metadata={"hnsw:space": "cosine"}
            )
            
            print("Vector database reset successful")
            
        except Exception as e:
            print(f"Error resetting database: {e}")
            # Set collection to None to indicate failure
            self.collection = None
    
    def _safe_collection_operation(self, operation, *args, **kwargs):
        """Safely execute collection operations with error recovery"""
        try:
            if self.collection is None:
                raise Exception("Vector DB not initialized.")
            
            return operation(*args, **kwargs)
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for specific ChromaDB errors
            if any(keyword in error_str for keyword in [
                "nothing found on disk", 
                "hnsw segment reader", 
                "corrupted", 
                "invalid"
            ]):
                print(f"ChromaDB corruption detected: {e}")
                print("Attempting to recover...")
                
                try:
                    self._reset_collection()
                    # Retry operation
                    if self.collection is not None:
                        return operation(*args, **kwargs)
                except Exception as recovery_error:
                    print(f"Recovery failed: {recovery_error}")
            
            raise e

    def add_element_embedding(self, element_id, plain_text, embedding_vector, metadata=None):
        """Adds an element's content embedding to the vector database."""
        try:
            # Default metadata
            default_metadata = {
                "element_id": str(element_id),
                "content_type": "page_element"
            }
            
            # Merge with provided metadata
            if metadata:
                default_metadata.update(metadata)
            
            def add_operation():
                self.collection.add(
                    documents=[plain_text],
                    embeddings=[embedding_vector],
                    metadatas=[default_metadata],
                    ids=[str(uuid.uuid4())]
                )
            
            self._safe_collection_operation(add_operation)
            return True
            
        except Exception as e:
            print(f"Error adding element embedding for element {element_id}: {e}")
            return False

    def search_similar_elements(self, query_embedding, document_id=None, top_k=5):
        """Searches for top_k most similar elements."""
        try:
            # Build where clause
            where_clause = {}
            if document_id:
                where_clause["document_id"] = {"$eq": str(document_id)}
            
            def search_operation():
                return self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=where_clause if where_clause else None,
                    include=["documents", "metadatas", "distances"]
                )
            
            return self._safe_collection_operation(search_operation)
            
        except Exception as e:
            print(f"Error searching similar elements: {e}")
            return None

    def delete_element_embedding(self, element_id):
        """Deletes embedding associated with a specific element_id."""
        try:
            def delete_operation():
                self.collection.delete(where={"element_id": {"$eq": str(element_id)}})
            
            self._safe_collection_operation(delete_operation)
            print(f"Deleted embedding for element {element_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting embedding for element {element_id}: {e}")
            return False

    def delete_document_embeddings(self, document_id):
        """Deletes all embeddings associated with a specific document_id."""
        try:
            def delete_operation():
                self.collection.delete(where={"document_id": {"$eq": str(document_id)}})
            
            self._safe_collection_operation(delete_operation)
            print(f"Deleted all embeddings for document {document_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting embeddings for document {document_id}: {e}")
            return False

    def get_collection_stats(self):
        """Get statistics about the vector database."""
        try:
            def stats_operation():
                return {
                    "total_embeddings": self.collection.count(),
                    "collection_name": self.collection.name
                }
            
            return self._safe_collection_operation(stats_operation)
            
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return {"error": f"Vector DB error: {str(e)}"}

    def get_collection_data(self, include=["documents", "metadatas", "embeddings"]):
        """Get all data from collection with error handling"""
        try:
            def get_operation():
                return self.collection.get(include=include)
            
            return self._safe_collection_operation(get_operation)
            
        except Exception as e:
            print(f"Error getting collection data: {e}")
            return None

    def is_healthy(self):
        """Check if vector database is healthy"""
        try:
            if self.collection is None:
                return False
            
            # Test basic operations
            _ = self.collection.count()
            return True
            
        except Exception as e:
            print(f"Vector database health check failed: {e}")
            return False

    def force_reset(self):
        """Force reset the entire vector database"""
        try:
            print("Force resetting vector database...")
            self._reset_database()
            return self.is_healthy()
        except Exception as e:
            print(f"Force reset failed: {e}")
            return False