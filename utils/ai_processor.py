import time
import random
from google.genai import Client, types
from config import Config
import base64
import json

from utils.function_call import STRUCTURED_EXTRACTION_TOOL

class AIProcessor:
    def __init__(self):
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Gemini client"""
        try:
            self.client = Client(
                api_key=Config.GEMINI_API_KEY,
                http_options={'api_version': 'v1beta'}
            )
            print("Gemini client initialized successfully")
            if not Config.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY tidak ditemukan")
            print(f"Using model: {Config.MODEL_NAME}")
            print(f"Using embedding model: {Config.EMBEDDING_MODEL}")
        except Exception as e:
            print(f"Error initializing Gemini client: {e}")
            raise e

    def _retry_with_backoff(self, func, max_retries=3, base_delay=1):
        """Retry function with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                # Retry untuk error 503 (overloaded) dan 500 (internal server error)
                if "503" in str(e) or "UNAVAILABLE" in str(e) or "500" in str(e) or "INTERNAL" in str(e):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        error_type = "503/overloaded" if "503" in str(e) else "500/internal"
                        print(f"API {error_type} error, retrying in {delay:.2f} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"Max retries reached for API error: {e}")
                        return None
                else:
                    print(f"Non-retryable error: {e}")
                    return None
        return None

    def process_png_page(self, png_filepath):
        """
        Process a single PNG page to extract text, flowchart, and summary.
        
        Returns:
            list: A list of extracted elements.
        """
        try:
            with open(png_filepath, 'rb') as f:
                png_data = f.read()
            png_b64 = base64.b64encode(png_data).decode('utf-8')
            
            extracted_elements = []

            content = {
                'role': 'user',
                'parts': [
                    {'inline_data': {'mime_type': 'image/png', 'data': png_b64}},
                    {'text': 'Analisis halaman dokumen ini. Ekstrak seluruh teks dan identifikasi flowchart. Berikan juga penjelasan (explanation) yang mengidentifikasi jenis halaman (misalnya, cover, daftar isi, atau isi utama) dan konteksnya dalam dokumen. Gunakan function call `analyze_document_page` untuk mengembalikan hasilnya.'}
                ]
            }

            def api_call():
                return self.client.models.generate_content(
                    model=Config.MODEL_NAME,
                    contents=[content],
                    config=types.GenerateContentConfig(
                        tools=STRUCTURED_EXTRACTION_TOOL,
                        tool_config=types.ToolConfig(
                            function_calling_config=types.FunctionCallingConfig(mode='ANY')
                        )
                    )
                )
            
            response = self._retry_with_backoff(api_call)

            if response is None:
                print("Failed to get response after all retries")
                return []

            self._debug_response_structure(response)

            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call and part.function_call.name == 'analyze_document_page':
                        args = dict(part.function_call.args)
                        
                        # 1. Ekstrak dan Gabungkan Teks dan Penjelasan
                        if 'extracted_text' in args:
                            text_content = args['extracted_text'].get('all_text', '')
                            explanation_content = args['extracted_text'].get('explanation', '')
                            
                            # Gabungkan untuk embedding
                            combined_plain_text = f"{text_content} \n\nPenjelasan: {explanation_content}".strip()
                            
                            # Simpan keduanya dalam JSON untuk referensi
                            combined_content_json = {
                                'all_text': text_content,
                                'explanation': explanation_content
                            }
                            
                            if combined_plain_text:
                                extracted_elements.append({
                                    'element_type': 'ALL_TEXT',
                                    'content_json': json.dumps(combined_content_json, ensure_ascii=False),
                                    'plain_text': combined_plain_text
                                })
                        
                        # 2. Ekstrak Flowchart
                        if 'flowchart' in args and args['flowchart']:
                            flowchart_content = args['flowchart']
                            plain_text = self._flowchart_to_text(flowchart_content)
                            extracted_elements.append({
                                'element_type': 'FLOWCHART',
                                'content_json': json.dumps(flowchart_content, ensure_ascii=False),
                                'plain_text': plain_text
                            })
            
            print(f"Final extracted elements count: {len(extracted_elements)}")
            return extracted_elements
            
        except Exception as e:
            print(f"Error processing PNG page: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _flowchart_to_text(self, flowchart_content):
        """Converts flowchart JSON to a readable text format."""
        parts = []
        if flowchart_content.get('title'):
            parts.append(flowchart_content['title'])
        
        for node in flowchart_content.get('nodes', []):
            parts.append(f"Node ({node.get('shape', '')}): {node.get('label', '')}")
            
        if flowchart_content.get('edges'):
            parts.append("\nAlur:")
            for edge in flowchart_content.get('edges', []):
                edge_text = f"  Dari {edge.get('from_node', '')} ke {edge.get('to_node', '')}"
                if edge.get('label'):
                    edge_text += f" dengan label '{edge.get('label')}'"
                parts.append(edge_text)
        
        if flowchart_content.get('explanation'):
            parts.append(f"\nPenjelasan: {flowchart_content['explanation']}")
            
        return "\n".join(parts)

    def call_gemini_api(self, text_content):
        """Call Gemini API for text-based queries"""
        try:
            content = {'role': 'user', 'parts': [{'text': text_content}]}
            response = self.client.models.generate_content(model=Config.MODEL_NAME, contents=[content])
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            return "Tidak ada respons yang valid dari AI."
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return f"Error: {str(e)}"

    def generate_embeddings(self, text):
        """Generate embeddings for text using Gemini with retry logic"""
        try:
            # Validasi input text
            if not text or not text.strip():
                print("Warning: Empty text provided for embedding generation")
                return None
            
            # Truncate text jika terlalu panjang (Gemini embedding model memiliki batas)
            max_text_length = 2048  # Batas aman untuk embedding model
            if len(text) > max_text_length:
                print(f"Warning: Text too long ({len(text)} chars), truncating to {max_text_length} chars")
                text = text[:max_text_length]
            
            def embedding_api_call():
                # Tambahkan delay kecil untuk menghindari rate limiting
                time.sleep(0.1)
                return self.client.models.embed_content(
                    model=Config.EMBEDDING_MODEL,
                    contents=[text]
                )
            
            # Gunakan retry logic yang sudah ada
            response = self._retry_with_backoff(embedding_api_call)
            
            if response is None:
                print("Failed to generate embeddings after all retries")
                return None
            
            # Based on the latest error log, the structure is response.embeddings[0].values
            if hasattr(response, 'embeddings') and response.embeddings and hasattr(response.embeddings[0], 'values'):
                return response.embeddings[0].values
            else:
                print(f"Unexpected embedding response structure: {type(response)}")
                print(f"Response content: {response}")
                return None
                
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            import traceback
            traceback.print_exc()
            return None

    def answer_question(self, question, elements_context):
        """Answer question based on elements context with a more natural response format."""
        try:
            if not elements_context:
                return "Maaf, tidak ada informasi yang relevan untuk menjawab pertanyaan Anda."
            
            # Kelompokkan konteks berdasarkan nomor halaman
            context_by_page = {}
            for element in elements_context:
                page_number = element.get('page_number', 'N/A')
                if page_number not in context_by_page:
                    context_by_page[page_number] = []
                
                # Tambahkan prefix tipe elemen untuk kejelasan
                element_text = f"[{element.get('element_type', 'UNKNOWN')}] {element.get('plain_text', '')}"
                context_by_page[page_number].append(element_text)

            # Buat teks konteks yang terstruktur per halaman
            context_parts = []
            for page_number, contents in context_by_page.items():
                content_str = "\n".join(contents)
                context_parts.append(f"--- Informasi dari Halaman {page_number} ---\n{content_str}")

            context_text = "\n\n".join(context_parts)

            prompt = f"""Berdasarkan informasi dari dokumen berikut, jawablah pertanyaan yang diajukan.

{context_text}

---
PERTANYAAN: {question}

PETUNJUK JAWABAN:
1. Jawab pertanyaan secara langsung, jelas, dan ringkas dalam Bahasa Indonesia.
2. Sintesis informasi dari halaman-halaman yang disediakan untuk membentuk satu jawaban yang utuh dan koheren.
3. Jika perlu merujuk pada informasi spesifik, sebutkan nomor halamannya secara natural (contoh: "Menurut alur proses di halaman 9,..., Gambar 1. (15.X.1.1)").

JAWABAN:"""

            return self.call_gemini_api(prompt)
            
        except Exception as e:
            print(f"Error answering question: {e}")
            return f"Maaf, terjadi kesalahan: {str(e)}"

    def _debug_response_structure(self, response):
        """Debug helper to print response structure"""
        print("🔍 Debug Response Structure:")
        try:
            if response and response.candidates:
                print(f"   Candidates count: {len(response.candidates)}")
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    print(f"   Parts count: {len(candidate.content.parts)}")
                    for i, part in enumerate(candidate.content.parts):
                        if hasattr(part, 'function_call') and part.function_call:
                            print(f"   Part {i} function_call: {part.function_call.name}")
            else:
                print("   No candidates found.")
        except Exception as e:
            print(f"   Error debugging response: {e}")
        print("🔍 End Debug Response Structure")
