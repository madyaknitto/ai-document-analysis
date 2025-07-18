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
            
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            prompt = """
            Analisis gambar flow diagram ini secara teliti. Tugas Anda adalah mengubahnya menjadi objek JSON tunggal yang valid.
            Output Anda HARUS HANYA berupa string JSON mentah, tanpa teks pembuka, penutup, atau format markdown.

            Struktur JSON yang WAJIB diikuti:
            {
              "flowchart_id": "string (opsional, jika ada di diagram Contohnya seperti 15A.29.8, 40C.12, 15B.29.8.1, dll.)",
              "title": "string (judul utama diagram)",
              "nodes": [
                {
                  "id": "string (ID unik untuk setiap node, e.g., 'start', 'step1', 'decisionA')",
                  "type": "string (pilih dari: Start, End, Process, Decision, Popup, Connector)",
                  "label": "string (teks yang terbaca di dalam node)",
                  "details": "string (opsional, referensi atau detail tambahan, e.g., '[KN UI 1779]')",
                  "next_node_id": "string (HANYA untuk node dengan satu alur keluar, berisi ID node tujuan)",
                  "next_nodes": [
                    { "condition": "string (label dari panah kondisi, e.g., 'Y', 'N', 'Valid')", "target_id": "string (ID node tujuan)" }
                  ]
                }
              ]
            }

            PERHATIKAN:
            - Setiap node HARUS memiliki 'id' yang unik.
            - Node 'Decision' HARUS menggunakan 'next_nodes' untuk merepresentasikan setiap cabang.
            - Node 'Process' atau 'Popup' yang hanya punya satu panah keluar HARUS menggunakan 'next_node_id'.
            - Node 'Connector' harus memiliki 'target_id' yang menunjuk ke 'id' node lain.
            - Pastikan semua hubungan antar node tercermin dengan benar menggunakan 'next_node_id' atau 'next_nodes'.
            """
            
            image = Image.open(io.BytesIO(image_data))
            
            response = self.client.models.generate_content(
                model=Config.MODEL_NAME,
                contents=[prompt, image]
            )
            
            response_text = response.text if response.text else ""
            
            # Clean the response text to remove markdown wrappers
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                print(f"Failed to decode JSON from response: {response_text}")
                # Return a structured error instead of the old format
                return {
                    "error": "Failed to parse JSON from model response.",
                    "raw_response": response_text
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
            analysis_json_string = json.dumps(diagram_analysis, indent=2)
            
            context = f"""
            Berdasarkan analisis flow diagram dalam format JSON berikut:
            
            {analysis_json_string}
            
            1. Jawab pertanyaan berikut dengan akurat berdasarkan informasi dari JSON di atas.
            2. Jika ada Connector, maka sebutkan juga Node dan Label yang menjadi target_id dari Connector tersebut.
            3. Ganti bahasa teknis menjadi bahasa yang bisa dimengerti seperti:
                - node menjadi langkah
                - condition menjadi kondisi
                - label menjadi label
                - next_node_id menjadi langkah selanjutnya
                - next_nodes menjadi langkah selanjutnya
                - target_id menjadi langkah selanjutnya
                - kondisi Y menjadi Ya
                - kondisi N menjadi Tidak
            3. Jika pertanyaan tidak ada hubungannya dengan diagram, jawab dengan "Pertanyaan tidak dimengerti".
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