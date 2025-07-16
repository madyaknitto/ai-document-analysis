import google.generativeai as genai
from google.generativeai.generative_models import GenerativeModel
from google.generativeai.client import configure
from google.generativeai.embedding import embed_content
from config import Config
import time
import base64
from PIL import Image
import io
import json

class GeminiProcessor:
    def __init__(self):
        self.configure_gemini()
        self.model = None
        self.embedding_model = None
        self.initialize_models()
    
    def configure_gemini(self):
        """Configure Gemini API"""
        try:
            configure(api_key=Config.GEMINI_API_KEY)
            print("Gemini API configured successfully")
        except Exception as e:
            print(f"Error configuring Gemini API: {e}")
            raise e
    
    def initialize_models(self):
        """Initialize Gemini models"""
        try:
            self.model = GenerativeModel(model_name=Config.MODEL_NAME)
            print(f"Model {Config.MODEL_NAME} initialized successfully")
        except Exception as e:
            print(f"Error initializing models: {e}")
            raise e
    
    def analyze_flow_diagram(self, image_path):
        """Analyze flow diagram and extract information"""
        try:
            if self.model is None:
                raise Exception("Model not initialized. Check Gemini API configuration.")
            
            # Load and process image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
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
            
            response = self.model.generate_content([prompt, image])
            
            # Parse JSON response
            try:
                analysis = json.loads(response.text)
            except json.JSONDecodeError:
                # If JSON parsing fails, return structured response
                analysis = {
                    "title": "Flow Diagram Analysis",
                    "description": "Analisis diagram berhasil diproses",
                    "elements": [],
                    "process_flow": response.text,
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
            # Use text embedding model
            embedding = embed_content(
                model=Config.EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_document"
            )
            
            return embedding['embedding']
            
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return None
    
    def answer_question(self, question, diagram_analysis, context_embeddings=None):
        """Answer question about flow diagram"""
        try:
            if self.model is None:
                raise Exception("Model not initialized. Check Gemini API configuration.")
            
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
            response = self.model.generate_content(prompt)
            response_time = time.time() - start_time
            
            return {
                "answer": response.text,
                "response_time": f"{response_time:.2f}s",
                "confidence_score": "High"  # Could implement confidence scoring
            }
            
        except Exception as e:
            print(f"Error answering question: {e}")
            return {
                "answer": "Maaf, terjadi kesalahan dalam memproses pertanyaan Anda.",
                "response_time": "0s",
                "confidence_score": "Low"
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