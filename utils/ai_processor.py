import google.genai as genai
from google.genai import Client
from config import Config
import time
import base64
from PIL import Image
import io
import json

class GeminiProcessor:
    def __init__(self):
        self.client = None
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize Gemini client"""
        try:
            self.client = Client(
                api_key=Config.GEMINI_API_KEY,
                http_options={'api_version': 'v1beta'}
            )
            print("Gemini client initialized successfully")
        except Exception as e:
            print(f"Error initializing Gemini client: {e}")
            raise e
    
    def analyze_flow_diagram(self, image_path):
        """Analyze flow diagram and extract information"""
        try:
            if self.client is None:
                raise Exception("Client not initialized. Check Gemini API configuration.")
            
            # Load and process image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Convert to base64 for API
            # image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prompt for diagram analysis
            prompt = """
            Analisis flow diagram berikut dengan detail:
            
            1. Identifikasi semua elemen diagram (kotak, panah, kondisi, dll)
            2. Jelaskan alur proses dari awal hingga akhir
            3. Sebutkan semua decision points dan alternatif jalur
            4. Identifikasi input dan output dari setiap tahap
            5. Jelaskan tujuan utama dari flow diagram ini
            
            Berikan analisis dalam format JSON dengan struktur:
            {
                "title": "Judul diagram",
                "description": "Deskripsi singkat",
                "elements": ["list elemen-elemen diagram"],
                "process_flow": "Penjelasan alur proses",
                "decision_points": ["list decision points"],
                "inputs_outputs": {"input": [], "output": []},
                "main_purpose": "Tujuan utama diagram"
            }
            """
            
            # Create PIL Image for API
            image = Image.open(io.BytesIO(image_data))
            
            response = self.client.models.generate_content(
                model=Config.MODEL_NAME,
                contents=[prompt, image]
            )
            
            # Parse JSON response
            try:
                response_text = response.text if response.text else ""
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, return structured response
                analysis = {
                    "title": "Flow Diagram Analysis",
                    "description": "Analisis diagram berhasil diproses",
                    "elements": [],
                    "process_flow": response_text,
                    "decision_points": [],
                    "inputs_outputs": {"input": [], "output": []},
                    "main_purpose": "Diagram telah dianalisis"
                }
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing flow diagram: {e}")
            return None
    
    def generate_embeddings(self, text):
        """Generate embeddings for text using Gemini"""
        try:
            if self.client is None:
                raise Exception("Client not initialized. Check Gemini API configuration.")
            
            # Use text embedding model
            embedding = self.client.models.embed_content(
                model=Config.EMBEDDING_MODEL,
                contents=[text]
            )
            
            if embedding and embedding.embeddings:
                return embedding.embeddings[0].values
            else:
                return None
            
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return None
    
    def answer_question(self, question, diagram_analysis, context_embeddings=None):
        """Answer question about flow diagram"""
        try:
            if self.client is None:
                raise Exception("Client not initialized. Check Gemini API configuration.")
            
            # Create context from diagram analysis
            context = f"""
            Berdasarkan analisis flow diagram berikut:
            
            Judul: {diagram_analysis.get('title', 'N/A')}
            Deskripsi: {diagram_analysis.get('description', 'N/A')}
            Alur Proses: {diagram_analysis.get('process_flow', 'N/A')}
            Decision Points: {', '.join(diagram_analysis.get('decision_points', []))}
            Tujuan Utama: {diagram_analysis.get('main_purpose', 'N/A')}
            
            Jawab pertanyaan berikut dengan akurat berdasarkan informasi diagram:
            """
            
            prompt = f"{context}\n\nPertanyaan: {question}\n\nJawaban:"
            
            start_time = time.time()
            response = self.client.models.generate_content(
                model=Config.MODEL_NAME,
                contents=[prompt]
            )
            response_time = time.time() - start_time
            
            return {
                "answer": response.text,
                "response_time": f"{response_time:.2f}s"
            }
            
        except Exception as e:
            print(f"Error answering question: {e}")
            return {
                "answer": "Maaf, terjadi kesalahan dalam memproses pertanyaan Anda.",
                "response_time": "0s"
            }
    
    def find_similar_questions(self, question, qa_history):
        """Find similar questions from history"""
        try:
            # Generate embedding for current question
            question_embedding = self.generate_embeddings(question)
            
            if not question_embedding:
                return []
            
            # Simple similarity check (could be improved with vector similarity)
            similar_questions = []
            for qa in qa_history:
                if self.calculate_similarity(question.lower(), qa.question.lower()):
                    similar_questions.append(qa)
            
            return similar_questions
            
        except Exception as e:
            print(f"Error finding similar questions: {e}")
            return []
    
    def calculate_similarity(self, text1, text2):
        """Simple similarity calculation (could be improved)"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if len(union) == 0:
            return 0
        
        return len(intersection) / len(union) > 0.5  # 50% similarity threshold 