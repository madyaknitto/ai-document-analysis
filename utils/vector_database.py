import chromadb
from chromadb.config import Settings
from config import Config
import json
import uuid
import os
from typing import Any

class VectorDatabaseManager:
    def __init__(self):
        self.client = None
        self.collection = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize ChromaDB"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=Config.VECTOR_DB_PATH,
                settings=Settings(allow_reset=True)
            )
            
            # Create or get collection
            self.collection = self.client.get_or_create_collection(
                name="flow_diagram_embeddings",
                metadata={"hnsw:space": "cosine"}
            )
            
            print("Vector database initialized successfully")
            
        except Exception as e:
            print(f"Error initializing vector database: {e}")
            raise e
    
    def add_diagram_embedding(self, diagram_id, analysis_data, embeddings):
        """Add diagram analysis and embeddings to vector database"""
        try:
            if self.collection is None:
                raise Exception("Vector database not initialized. Check ChromaDB configuration.")
            
            # Convert analysis data to text for embedding
            analysis_text = self._convert_analysis_to_text(analysis_data)
            
            # Add to collection
            self.collection.add(
                documents=[analysis_text],
                embeddings=[embeddings],
                metadatas=[{
                    "diagram_id": diagram_id,
                    "type": "diagram_analysis",
                    "title": analysis_data.get("title", ""),
                    "description": analysis_data.get("description", "")
                }],
                ids=[f"diagram_{diagram_id}_{uuid.uuid4().hex[:8]}"]
            )
            
            print(f"Added embeddings for diagram {diagram_id}")
            return True
            
        except Exception as e:
            print(f"Error adding diagram embedding: {e}")
            return False
    
    def search_similar_content(self, query_embedding, n_results=5):
        """Search for similar content in vector database"""
        try:
            if self.collection is None:
                raise Exception("Vector database not initialized. Check ChromaDB configuration.")
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            return results
            
        except Exception as e:
            print(f"Error searching similar content: {e}")
            return None
    
    def get_diagram_embeddings(self, diagram_id):
        """Get embeddings for specific diagram"""
        try:
            if self.collection is None:
                raise Exception("Vector database not initialized. Check ChromaDB configuration.")
            
            results = self.collection.get(
                where={"diagram_id": {"$eq": diagram_id}},
                include=["documents", "metadatas", "embeddings"]
            )
            
            return results
            
        except Exception as e:
            print(f"Error getting diagram embeddings: {e}")
            return None
    
    def delete_diagram_embeddings(self, diagram_id):
        """Delete embeddings for specific diagram"""
        try:
            if self.collection is None:
                raise Exception("Vector database not initialized. Check ChromaDB configuration.")
            
            # Get all embeddings for this diagram
            results = self.collection.get(
                where={"diagram_id": {"$eq": diagram_id}}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                print(f"Deleted embeddings for diagram {diagram_id}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting diagram embeddings: {e}")
            return False
    
    def add_qa_embedding(self, diagram_id, question, answer, embeddings):
        """Add Q&A pair embedding to database"""
        try:
            if self.collection is None:
                raise Exception("Vector database not initialized. Check ChromaDB configuration.")
            
            qa_text = f"Question: {question}\nAnswer: {answer}"
            
            self.collection.add(
                documents=[qa_text],
                embeddings=[embeddings],
                metadatas=[{
                    "diagram_id": diagram_id,
                    "type": "qa_pair",
                    "question": question
                }],
                ids=[f"qa_{diagram_id}_{uuid.uuid4().hex[:8]}"]
            )
            
            return True
            
        except Exception as e:
            print(f"Error adding Q&A embedding: {e}")
            return False
    
    def search_similar_questions(self, question_embedding, diagram_id=None, n_results=3):
        """Search for similar questions"""
        try:
            if self.collection is None:
                raise Exception("Vector database not initialized. Check ChromaDB configuration.")
            
            # Format where clause properly for ChromaDB
            if diagram_id:
                where_clause = {
                    "$and": [
                        {"type": {"$eq": "qa_pair"}},
                        {"diagram_id": {"$eq": diagram_id}}
                    ]
                }
            else:
                where_clause = {"type": {"$eq": "qa_pair"}}
            
            results = self.collection.query(
                query_embeddings=[question_embedding],
                n_results=n_results,
                where=where_clause,  # type: ignore
                include=["documents", "metadatas", "distances"]
            )
            
            return results
            
        except Exception as e:
            print(f"Error searching similar questions: {e}")
            return None
    
    def get_collection_stats(self):
        """Get statistics about the vector database"""
        try:
            if self.collection is None:
                raise Exception("Vector database not initialized. Check ChromaDB configuration.")
            
            count = self.collection.count()
            return {
                "total_embeddings": count,
                "collection_name": self.collection.name
            }
            
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return None
    
    def _convert_analysis_to_text(self, analysis_data):
        """Convert analysis data to text format for embedding"""
        text_parts = []
        
        if analysis_data.get("title"):
            text_parts.append(f"Title: {analysis_data['title']}")
        
        if analysis_data.get("description"):
            text_parts.append(f"Description: {analysis_data['description']}")
        
        if analysis_data.get("process_flow"):
            text_parts.append(f"Process Flow: {analysis_data['process_flow']}")
        
        if analysis_data.get("decision_points"):
            text_parts.append(f"Decision Points: {', '.join(analysis_data['decision_points'])}")
        
        if analysis_data.get("main_purpose"):
            text_parts.append(f"Main Purpose: {analysis_data['main_purpose']}")
        
        return "\n".join(text_parts) 