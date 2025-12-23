import logging
import traceback
import sys
import time
import os
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
            return vectorstore
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
        print(f"\n[Langkah 1] Mencari subject dengan ID: {subject_id}")
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
        print(f"✓ Subject ditemukan: {subject_name} (ID: {subject_id})")
        
        # Get module info
        print(f"[Langkah 2] Mencari module dengan ID: {module_id}")
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
        print(f"✓ Module ditemukan: {module_title} (ID: {module_id})")

        topic = module_title
        class_name = "Generated"
        
        # Run RAG pipeline with caching
        print("[Langkah 3] Menjalankan pipeline indexing (dengan cache)...")
        embedder = Embedder()
        vectorstore = get_or_build_vectorstore(module_id, file_path, embedder)
        
        print("[Langkah 4] Melakukan retrieval konteks...")
        
        # Query berbeda berdasarkan tingkat kesulitan
        difficulty_lower = tingkat_kesulitan.lower()
        if difficulty_lower == "sulit":
            # Query komprehensif untuk mengambil SELURUH materi modul
            query = f"""Seluruh materi lengkap dan komprehensif tentang {topic} dalam {subject_name}. 
            Termasuk semua konsep, sintaks, variasi, contoh kasus, dan penerapan lanjutan.
            Cakup semua sub-topik seperti: for loop, while loop, do-while, nested loop, break, continue, 
            dan semua teknik kontrol alur yang ada di modul."""
            top_k = 10
            initial_k = 30
        elif difficulty_lower == "sedang":
            query = f"Materi praktikum tentang {topic} dengan beberapa variasi konsep dalam {subject_name}"
            top_k = 5
            initial_k = 20
        else:  # Mudah
            query = f"Konsep dasar tentang {topic} dalam mata kuliah {subject_name}"
            top_k = 3
            initial_k = 10
        
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
        print(f"[Langkah 5] Menghasilkan assessment (preview mode)...")
        print(f"  - Tingkat kesulitan: {tingkat_kesulitan}")
        if notes:
            print(f"  - Catatan khusus: {notes}")

        result = preview_rag_generated_assessment(
            subject_id=subject_id,
            session_id=0,
            topic=topic,
            class_name=class_name,
            subject_name=subject_name,
            assistant_id=assistant_id,
            context_snippets=context_snippets,
            custom_notes=combined_notes,
            generated_by=assistant_id
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
        
        print(f"\n{'='*60}")
        print(f"[ERROR] Terjadi exception")
        print(f"Tipe: {exc_type.__name__ if exc_type else 'Unknown'}")
        print(f"Nilai: {exc_value if exc_value else 'Unknown'}")
        print(f"\nTraceback Lengkap:")
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        print(f"{'='*60}\n")
        
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
def get_modules_by_subject(subject_id: int):
    """Mengambil semua module untuk subject tertentu (untuk Streamlit demo)."""
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, file_name, uploaded_at
                FROM module
                ORDER BY uploaded_at DESC
            """)
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
