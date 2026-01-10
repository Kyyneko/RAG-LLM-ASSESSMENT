import logging
import traceback
import sys
import time
import os
from functools import wraps
from flask import Blueprint, request, jsonify
from db.connection import get_connection
from rag.pipeline import process_files
from rag.retriever import retrieve_context_with_reranking
from rag.embedder import Embedder
from rag.vectorstore import VectorStore
from assessment.generator import preview_rag_generated_assessment

rag_bp = Blueprint("rag_bp", __name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cache directory for vector stores
VECTORSTORE_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vectorstore")
os.makedirs(VECTORSTORE_CACHE_DIR, exist_ok=True)

# ============================================================
# API SECURITY: Rate Limiting Storage
# ============================================================
request_counts = {}  # {api_key: [timestamp1, timestamp2, ...]}

def require_api_key(f):
    """
    Decorator untuk validasi API Key dan Rate Limiting.
    - Cek header X-API-Key
    - Batasi request per menit sesuai RATE_LIMIT_PER_MINUTE
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        valid_keys = os.getenv("API_KEYS", "").split(",")
        valid_keys = [k.strip() for k in valid_keys if k.strip()]
        
        # Step 1: Validasi API Key
        if not api_key:
            logger.warning("Request tanpa API Key")
            return jsonify({"error": "API Key required. Add 'X-API-Key' header."}), 401
        
        if api_key not in valid_keys:
            logger.warning(f"API Key tidak valid: {api_key[:10]}...")
            return jsonify({"error": "Invalid API Key"}), 401
        
        # Step 2: Rate Limit Check
        limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", 10))
        current_time = time.time()
        window_seconds = 60
        
        if api_key not in request_counts:
            request_counts[api_key] = []
        
        # Hapus request lama (> 60 detik)
        request_counts[api_key] = [
            t for t in request_counts[api_key] 
            if current_time - t < window_seconds
        ]
        
        # Cek limit
        if len(request_counts[api_key]) >= limit:
            logger.warning(f"Rate limit exceeded untuk key: {api_key[:10]}...")
            return jsonify({
                "error": "Rate limit exceeded",
                "limit": limit,
                "retry_after_seconds": 60
            }), 429
        
        # Step 3: Increment counter
        request_counts[api_key].append(current_time)
        logger.debug(f"Request {len(request_counts[api_key])}/{limit} untuk key: {api_key[:10]}...")
        
        # Step 4: Process request
        return f(*args, **kwargs)
    
    return decorated

def get_cache_paths(module_id: int) -> tuple:
    """Get cache file paths for a specific module."""
    index_path = os.path.join(VECTORSTORE_CACHE_DIR, f"module_{module_id}.faiss")
    data_path = os.path.join(VECTORSTORE_CACHE_DIR, f"module_{module_id}.pkl")
    return index_path, data_path

def get_or_build_vectorstore(module_id: int, file_path: str, embedder: Embedder) -> VectorStore:
    """
    Get cached vector store or build new one if not exists.
    
    Args:
        module_id: Module ID for cache identification
        file_path: Path to module file
        embedder: Embedder instance
        
    Returns:
        VectorStore: Cached or newly built vector store
    """
    index_path, data_path = get_cache_paths(module_id)
    
    # Check if cache exists
    if os.path.exists(index_path) and os.path.exists(data_path):
        try:
            logger.info(f"Loading cached vector store for module {module_id}")
            vectorstore = VectorStore.load_from_disk(index_path, data_path)
            # Check if cache is NOT empty - if empty, rebuild
            if vectorstore.index is not None and vectorstore.index.ntotal > 0:
                logger.info(f"Cache loaded with {vectorstore.index.ntotal} vectors")
                return vectorstore
            else:
                logger.warning(f"Cache exists but is empty (0 chunks), rebuilding...")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}, rebuilding...")
    
    # Build new vector store
    logger.info(f"Building new vector store for module {module_id}")
    vectorstore = process_files([file_path], embedder)
    
    # Save to cache
    try:
        vectorstore.save_to_disk(index_path, data_path)
        logger.info(f"Vector store cached for module {module_id}")
    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")
    
    return vectorstore


@rag_bp.route("/generate", methods=["POST"])
@require_api_key
def generate_assessment():
    """
    Generate assessment task dengan RAG dan LLM (Preview Only Mode).
    
    Endpoint ini HANYA mengembalikan response soal yang dihasilkan.
    Tidak menyimpan ke database - penyimpanan ditangani oleh backend SI-Lab.

    Request Body:
    {
        "subject_id": 1,
        "module_id": 1,
        "tingkat_kesulitan": "Sedang",  // Mudah/Sedang/Sulit
        "assistant_id": 1,
        "notes": "catatan opsional"
    }

    Response:
    {
        "status": "success",
        "assessment": {
            "sections": {
                "soal": "...",
                "requirements": "...",
                "expected_output": "...",
                "kunci_jawaban": "..."
            },
            "metadata": {...},
            "estimated_time": "60-90 menit"
        },
        "processing_time_seconds": 5.2
    }
    """
    start_time = time.time()
    conn = None
    cursor = None
    
    try:
        data = request.get_json()

        # Validate required fields
        subject_id = data.get("subject_id")
        module_id = data.get("module_id")
        tingkat_kesulitan = data.get("tingkat_kesulitan", "Sedang")
        assistant_id = data.get("assistant_id")
        notes = data.get("notes", "").strip()
        
        if not all([subject_id, module_id, assistant_id]):
            logger.warning("Field wajib tidak lengkap")
            return jsonify({
                "error": "subject_id, module_id, dan assistant_id wajib diisi."
            }), 400

        logger.info(f"Generate request - subject_id={subject_id}, module_id={module_id}, kesulitan={tingkat_kesulitan}")

        conn = get_connection()
        cursor = conn.cursor()

        # Get subject info
        logger.debug(f"Step 1: Finding subject with ID: {subject_id}")
        cursor.execute("""
            SELECT id, name, description
            FROM subject
            WHERE id = %s
        """, (subject_id,))
        subject_row = cursor.fetchone()

        if not subject_row:
            elapsed = time.time() - start_time
            return jsonify({
                "error": f"Subject dengan ID {subject_id} tidak ditemukan.",
                "processing_time_seconds": round(elapsed, 2)
            }), 404

        subject_name = subject_row["name"]
        logger.debug(f"Subject found: {subject_name} (ID: {subject_id})")
        
        # Get module info
        logger.debug(f"Step 2: Finding module with ID: {module_id}")
        cursor.execute("""
            SELECT id, title, file_path, file_name
            FROM module
            WHERE id = %s
        """, (module_id,))
        module_row = cursor.fetchone()

        if not module_row:
            elapsed = time.time() - start_time
            return jsonify({
                "error": f"Module dengan ID {module_id} tidak ditemukan.",
                "processing_time_seconds": round(elapsed, 2)
            }), 404

        module_title = module_row["title"]
        file_path = module_row["file_path"]
        logger.debug(f"Module found: {module_title} (ID: {module_id})")

        topic = module_title
        
        # Run RAG pipeline with caching
        logger.debug("Step 3: Running indexing pipeline (with cache)...")
        embedder = Embedder()
        vectorstore = get_or_build_vectorstore(module_id, file_path, embedder)
        
        logger.debug("Step 4: Performing context retrieval...")

        # Query berbeda berdasarkan tingkat kesulitan - LEBIH DINAMIS SESUAI TOPIK
        difficulty_lower = tingkat_kesulitan.lower()
        if difficulty_lower == "sulit":
            # Query komprehensif untuk mengambil SELURUH materi modul
            # Query ini akan menarik SEMUA variasi konsep yang ada di topik
            query = f"""Semua materi lengkap tentang {topic} dalam mata kuliah {subject_name}.
            Saya butuh SELURUH konsep, semua variasi sintaks, semua contoh, dan semua teknik yang terkait dengan {topic}.
            Termasuk setiap sub-topik, variasi, dan implementasi yang ada di materi modul ini.
            Contoh: jika tentang looping, butuh for, while, nested, break, continue, do-while, semua."""
            top_k = 15
            initial_k = 50
        elif difficulty_lower == "sedang":
            # Query untuk mengambil beberapa konsep terkait topik
            query = f"""Materi praktikum tentang {topic} dalam {subject_name}
            beserta variasi dan konsep terkait. Saya butuh beberapa contoh penerapan {topic}
            dengan berbagai skenario yang ada di modul."""
            top_k = 8
            initial_k = 25
        else:  # Mudah
            # Query fokus konsep dasar saja
            query = f"""Konsep dasar dan contoh sederhana tentang {topic} dalam mata kuliah {subject_name}.
            Fokus pada pengertian dan contoh penggunaan dasar {topic}."""
            top_k = 5
            initial_k = 15
        
        logger.info(f"Mencari konteks untuk difficulty '{tingkat_kesulitan}': {query[:100]}...")
        
        context_snippets = retrieve_context_with_reranking(
            vectorstore=vectorstore,
            embedder=embedder,
            query=query,
            top_k=top_k,
            initial_k=initial_k
        )
        
        if not context_snippets:
            elapsed = time.time() - start_time
            logger.warning("Tidak ditemukan konteks yang relevan")
            return jsonify({
                "error": "Tidak ada konteks relevan ditemukan.",
                "hint": "Pastikan modul berisi materi tentang topik ini.",
                "processing_time_seconds": round(elapsed, 2)
            }), 404
        
        logger.info(f"Ditemukan {len(context_snippets)} snippets konteks")
        
        # Build custom notes
        custom_notes_parts = []
        if notes:
            custom_notes_parts.append(notes)
        custom_notes_parts.append(f"Tingkat kesulitan: {tingkat_kesulitan}")
        combined_notes = "\n".join(custom_notes_parts)

        # Generate assessment (preview only - no save)
        logger.info(f"Step 5: Generating assessment (preview mode)...")
        logger.debug(f"  Difficulty: {tingkat_kesulitan}")
        if notes:
            logger.debug(f"  Custom notes: {notes}")

        result = preview_rag_generated_assessment(
            subject_id=subject_id,
            session_id=0,
            topic=topic,
            subject_name=subject_name,
            assistant_id=assistant_id,
            context_snippets=context_snippets,
            custom_notes=combined_notes,
            generated_by=assistant_id,
            difficulty=tingkat_kesulitan
        )

        elapsed_time = time.time() - start_time
        logger.info(f"✓ Assessment generated, waktu={elapsed_time:.2f}s")

        # Return response (no save to database)
        return jsonify({
            "status": "success",
            "message": "Assessment berhasil digenerate.",
            "assessment": result.get("preview", {}),
            "parameters": {
                "subject_id": subject_id,
                "subject_name": subject_name,
                "module_id": module_id,
                "module_title": topic,
                "tingkat_kesulitan": tingkat_kesulitan
            },
            "processing_time_seconds": round(elapsed_time, 2)
        }), 200
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        logger.error(f"Exception occurred: {exc_type.__name__ if exc_type else 'Unknown'}")
        logger.error(f"Value: {exc_value if exc_value else 'Unknown'}")
        
        logger.error(f"Error menghasilkan assessment: {exc_value}", exc_info=True)
        
        error_message = str(exc_value) if exc_value else "Terjadi kesalahan yang tidak diketahui"
        error_type = exc_type.__name__ if exc_type else "Exception"
        
        return jsonify({
            "status": "error",
            "error": "Terjadi kesalahan internal.",
            "error_type": error_type,
            "details": error_message,
            "processing_time_seconds": round(elapsed_time, 2)
        }), 500
        
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass


@rag_bp.route("/subjects", methods=["GET"])
@require_api_key
def get_subjects():
    """Mengambil semua subject untuk dropdown/seleksi (untuk Streamlit demo)."""
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, description, created_at
                FROM subject
                WHERE is_active = 1
                ORDER BY name
            """)
            data = cur.fetchall()

        return jsonify({
            "status": "success",
            "total_records": len(data),
            "subjects": data
        }), 200

    except Exception as e:
        print(f"Error mengambil subjects: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500

    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


@rag_bp.route("/subjects/<int:subject_id>/modules", methods=["GET"])
@require_api_key
def get_modules_by_subject(subject_id: int):
    """
    Mengambil semua module untuk subject tertentu (untuk Streamlit demo).
    
    Relasi: module ↔ session_module ↔ session ↔ class ↔ subject
    """
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # Query dengan proper relationship chain:
            # module → session_module → session → class → subject
            cur.execute("""
                SELECT DISTINCT m.id, m.title, m.file_name, m.uploaded_at
                FROM module m
                INNER JOIN session_module sm ON m.id = sm.id_module
                INNER JOIN session s ON sm.id_session = s.id
                INNER JOIN class c ON s.id_class = c.id
                WHERE c.id_subject = %s
                ORDER BY m.title ASC
            """, (subject_id,))
            data = cur.fetchall()

        return jsonify({
            "status": "success",
            "subject_id": subject_id,
            "total_records": len(data),
            "modules": data
        }), 200

    except Exception as e:
        print(f"Error mengambil modules: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500

    finally:
        if conn:
            try:
                conn.close()
            except:
                pass
