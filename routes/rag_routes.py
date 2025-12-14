import logging
import traceback
import sys
import time
import os
import hashlib
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from db.connection import get_connection
from rag.pipeline import process_files
from rag.retriever import retrieve_context_with_reranking
from rag.embedder import Embedder
from assessment.generator import create_rag_generated_task, preview_rag_generated_assessment, save_approved_assessment

rag_bp = Blueprint("rag_bp", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def allowed_file(filename: str) -> bool:
    """Mengecek apakah ekstensi file diperbolehkan."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@rag_bp.route("/generate", methods=["POST"])
def generate_assessment():
    """
    Generate assessment task dengan RAG dan LLM.

    Mendukung tiga mode:
    1. Mode berbasis session (backward compatible):
       - Dibutuhkan: session_id, assistant_id
       - Opsional: notes

    2. Mode parameter langsung (dukungan UI baru):
       - Dibutuhkan: subject_id, module_id, tingkat_kesulitan, assistant_id
       - Opsional: session_id (jika diberikan, menghubungkan ke session yang ada)

    3. Mode preview:
       - Parameter: mode: "preview"
       - Tidak menyimpan ke database, hanya return hasil generate

    Business Logic (mode normal):
    - Jika sudah ada assessment untuk session ini dengan status 'applied': REJECT (409 Conflict)
    - Jika sudah ada assessment dengan status 'draft'/'none'/'generating': REPLACE (200 OK)
    - Jika belum ada assessment: CREATE NEW (201 Created)

    Mode Preview:
    - Generate dan return hasil langsung tanpa save ke DB
    - FE bisa preview dan approve dengan endpoint terpisah
    """
    start_time = time.time()
    conn = None
    cursor = None
    
    try:
        data = request.get_json()

        mode = data.get("mode", "normal")
        is_preview_mode = mode == "preview"

        is_direct_mode = "subject_id" in data or "module_id" in data
        
        if is_direct_mode:
            subject_id = data.get("subject_id")
            module_id = data.get("module_id")
            tingkat_kesulitan = data.get("tingkat_kesulitan", "Sedang")
            assistant_id = data.get("assistant_id")
            session_id = data.get("session_id")
            notes = data.get("notes", "").strip()
            
            if not all([subject_id, module_id, assistant_id]):
                logger.warning("Field wajib tidak lengkap untuk mode langsung")
                return jsonify({
                    "error": "subject_id, module_id, dan assistant_id wajib diisi."
                }), 400

            logger.info(f"Mode langsung - subject_id={subject_id}, module_id={module_id}, kesulitan={tingkat_kesulitan}")

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, username, id_role
                FROM user
                WHERE id = %s
            """, (assistant_id,))
            assistant_user = cursor.fetchone()

            if not assistant_user:
                return jsonify({
                    "error": f"Assistant dengan ID {assistant_id} tidak ditemukan.",
                    "hint": "Gunakan assistant ID yang valid (202-217)"
                }), 404

            if assistant_user['id_role'] != 3:
                logger.warning(f"User ID {assistant_id} bukan assistant (role: {assistant_user['id_role']})")
                return jsonify({
                    "error": f"User dengan ID {assistant_id} bukan assistant.",
                    "hint": "Gunakan user dengan role assistant"
                }), 400
            
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
            print(f"✓ Module ditemukan: {module_title} (ID: {module_id})")
            
            if session_id:
                print(f"[Langkah 3] Mengambil data session: {session_id}")
                cursor.execute("""
                    SELECT s.id, s.session_name, c.class_name
                    FROM session s
                    LEFT JOIN class c ON s.id_class = c.id
                    WHERE s.id = %s
                """, (session_id,))
                session_row = cursor.fetchone()

                if session_row:
                    topic = session_row["session_name"] or module_title
                    class_name = session_row["class_name"] or "Unknown"
                    print(f"✓ Session ditemukan: {topic} ({class_name})")
                else:
                    topic = module_title
                    class_name = "Generated"
                    print(f"Session tidak ditemukan, menggunakan judul modul sebagai topik: {topic}")
            else:
                topic = module_title
                class_name = "Generated"
                print(f"Tidak ada session_id, menggunakan judul modul sebagai topik: {topic}")
            
        else:
            session_id = data.get("session_id")
            assistant_id = data.get("assistant_id")
            notes = data.get("notes", "").strip()
            tingkat_kesulitan = "Sedang"
            
            if not session_id or not assistant_id:
                logger.warning("session_id atau assistant_id tidak ada")
                return jsonify({"error": "session_id dan assistant_id wajib diisi."}), 400
            
            logger.info(f"Mode legacy - session_id={session_id}, assistant_id={assistant_id}")
            
            if notes:
                logger.info(f"Catatan khusus diberikan: {notes[:100]}...")
            
            conn = get_connection()
            cursor = conn.cursor()
            
            print("\n[Langkah 1] Mengambil data session...")
            cursor.execute("""
                SELECT
                    s.id, s.session_name, s.id_class,
                    c.class_name,
                    sub.name as subject_name, sub.id as subject_id
                FROM session s
                JOIN class c ON s.id_class = c.id
                CROSS JOIN subject sub
                WHERE s.id = %s
                LIMIT 1
            """, (session_id,))
            session = cursor.fetchone()

            if not session:
                elapsed = time.time() - start_time
                return jsonify({
                    "error": f"Session {session_id} tidak ditemukan",
                    "processing_time_seconds": round(elapsed, 2)
                }), 404

            topic = session["session_name"]
            class_name = session["class_name"]
            subject_name = session["subject_name"]
            subject_id = session["subject_id"]
            
            print(f"✓ Session: {subject_name} ({class_name}) - Topik: {topic}")
        
        print("[Langkah 4] Memeriksa assessment yang sudah ada...")
        if session_id:
            cursor.execute("""
                SELECT id, title, generation_status, created_at
                FROM assessment_task
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (session_id,))
            existing_task = cursor.fetchone()
        else:
            existing_task = None
        
        replace_task_id = None
        action_type = "create"
        
        if existing_task:
            existing_status = existing_task["generation_status"]
            existing_title = existing_task["title"] or "(tanpa judul)"
            existing_id = existing_task["id"]
            
            print(f"⚠️ Ditemukan assessment yang sudah ada:")
            print(f"   - ID: {existing_id}")
            print(f"   - Judul: {existing_title}")
            print(f"   - Status: {existing_status}")
            
            if existing_status == "applied":
                elapsed = time.time() - start_time
                return jsonify({
                    "error": "Assessment untuk session ini sudah di-apply.",
                    "message": "Tidak dapat membuat assessment baru karena sudah ada yang di-apply.",
                    "existing_task_id": existing_id,
                    "existing_title": existing_title,
                    "status": existing_status,
                    "hint": "Hapus atau ubah status assessment existing terlebih dahulu.",
                    "processing_time_seconds": round(elapsed, 2)
                }), 409

            print(f"✓ Akan MEMBUAT assessment BARU (mengabaikan yang sudah ada)")
            action_type = "create"
        else:
            print("✓ Tidak ada assessment yang sudah ada, akan membuat baru")
        
        print("[Langkah 5] Mengambil file modul...")
        if is_direct_mode and module_id:
            cursor.execute("""
                SELECT file_path, title, file_name
                FROM module
                WHERE id = %s
            """, (module_id,))
            modules = cursor.fetchall()
        elif session_id:
            cursor.execute("""
                SELECT file_path, title, file_name
                FROM module
                ORDER BY uploaded_at DESC
                LIMIT 5
            """)
            modules = cursor.fetchall()
        else:
            cursor.execute("""
                SELECT file_path, title, file_name
                FROM module
                ORDER BY uploaded_at DESC
                LIMIT 5
            """)
            modules = cursor.fetchall()
        
        if not modules:
            elapsed = time.time() - start_time
            return jsonify({
                "error": "Tidak ada modul untuk session/subject ini.",
                "hint": "Upload modul terlebih dahulu menggunakan /api/rag/upload-module",
                "processing_time_seconds": round(elapsed, 2)
            }), 404
        
        file_paths = [m["file_path"] for m in modules]
        print(f"✓ {len(modules)} modul ditemukan")
        
        print("[Langkah 6] Menjalankan pipeline indexing...")
        embedder = Embedder()
        vectorstore = process_files(file_paths, embedder)
        
        print("[Langkah 7] Melakukan retrieval konteks...")
        query = f"Materi praktikum tentang {topic} dalam mata kuliah {subject_name}"
        logger.info(f"Mencari konteks untuk: {query}")
        
        context_snippets = retrieve_context_with_reranking(
            vectorstore=vectorstore,
            embedder=embedder,
            query=query,
            top_k=5,
            initial_k=15
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
        
        custom_notes_parts = []
        if notes:
            custom_notes_parts.append(notes)
        
        custom_notes_parts.append(f"Tingkat kesulitan: {tingkat_kesulitan}")
        
        combined_notes = "\n".join(custom_notes_parts)

        print(f"[Langkah 8] Menghasilkan assessment ({'preview' if is_preview_mode else action_type})...")
        print(f"  - Tingkat kesulitan: {tingkat_kesulitan}")
        if notes:
            print(f"  - Catatan khusus: {notes}")

        task_id = create_rag_generated_task(
            subject_id=subject_id,
            session_id=session_id if session_id else 0,
            assistant_id=assistant_id,
            subject_name=subject_name,
            topic=topic,
            class_name=class_name,
            context_snippets=context_snippets,
            existing_task_id=replace_task_id,
            custom_notes=combined_notes,
            generated_by=assistant_id
        )

        elapsed_time = time.time() - start_time
        logger.info(f"✓ Assessment {action_type}: task_id={task_id}, waktu={elapsed_time:.2f}s")

        response_data = {
            "status": "success",
            "mode": "normal",
            "message": f"Assessment berhasil {'diperbarui' if action_type == 'replace' else 'dibuat'}.",
            "action": action_type,
            "task_id": task_id,
            "parameters": {
                "subject_id": subject_id,
                "subject_name": subject_name,
                "module_title": topic,
                "tingkat_kesulitan": tingkat_kesulitan
            },
            "processing_time_seconds": round(elapsed_time, 2)
        }

        if action_type == "replace":
            response_data["replaced_task_id"] = replace_task_id

        status_code = 200 if action_type == "replace" else 201
        return jsonify(response_data), status_code
        
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


@rag_bp.route("/upload-module", methods=["POST"])
def upload_module():
    """Upload file modul baru dan simpan metadata ke database."""
    if "file" not in request.files:
        return jsonify({"error": "Tidak ada file yang diunggah"}), 400
    
    file = request.files["file"]
    session_id = request.form.get("session_id")
    title = request.form.get("title")
    assistant_id = request.form.get("assistant_id")
    
    if not all([session_id, title, assistant_id]):
        return jsonify({
            "error": "Parameter session_id, title, dan assistant_id wajib diisi."
        }), 400
    
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({
            "error": "Format file tidak didukung.",
            "allowed_formats": list(ALLOWED_EXTENSIONS)
        }), 400
    
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT subject_id FROM session WHERE id = %s", (session_id,))
        session = cur.fetchone()
        
        if not session:
            return jsonify({"error": f"Session {session_id} tidak ditemukan"}), 404
        
        subject_id = session["subject_id"]
        
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        safe_filename = f"{session_id}_{timestamp}_{filename}"
        
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "upload/")
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path_string = os.path.join(upload_folder, safe_filename)
        file.save(file_path_string)
        print(f"✓ File tersimpan: {file_path_string}")
        
        with open(file_path_string, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        file_type = filename.rsplit(".", 1)[1].lower() if "." in filename else "unknown"
        
        cur.execute("""
            INSERT INTO module (session_id, subject_id, title, file_path, uploaded_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (session_id, subject_id, title, file_path_string, assistant_id))
        
        module_id = cur.lastrowid
        
        cur.execute("""
            INSERT INTO rag_source_documents 
            (subject_id, session_id, file_name, file_type, file_path, checksum, uploaded_by, is_indexed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
        """, (subject_id, session_id, filename, file_type, file_path_string, checksum, assistant_id))
        
        conn.commit()
        
        print(f"✓ Modul terunggah: {filename} (ID: {module_id})")
        
        return jsonify({
            "status": "success",
            "message": "Modul berhasil diunggah.",
            "module_id": module_id,
            "file_path": file_path_string,
            "file_name": filename,
            "checksum": checksum
        }), 201
        
    except Exception as e:
        print(f"✗ Error mengunggah modul: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500
        
    finally:
        if cur:
            try:
                cur.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass


@rag_bp.route("/register-module", methods=["POST"])
def register_module():
    """Mendaftarkan file modul yang sudah ada tanpa upload (metadata saja)."""
    try:
        data = request.get_json()
        
        required_fields = ["session_id", "title", "file_path", "assistant_id"]
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            return jsonify({
                "error": f"Field wajib tidak ada: {', '.join(missing)}"
            }), 400
        
        session_id = data["session_id"]
        title = data["title"]
        file_path = data["file_path"]
        assistant_id = data["assistant_id"]
        
        if not os.path.exists(file_path):
            return jsonify({
                "error": f"File tidak ditemukan: {file_path}"
            }), 404
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT subject_id FROM session WHERE id = %s", (session_id,))
        session = cur.fetchone()
        
        if not session:
            cur.close()
            conn.close()
            return jsonify({"error": f"Session {session_id} tidak ditemukan"}), 404
        
        subject_id = session["subject_id"]
        
        filename = os.path.basename(file_path)
        file_type = filename.rsplit(".", 1)[1].lower() if "." in filename else "unknown"
        
        with open(file_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        cur.execute("""
            INSERT INTO module (session_id, subject_id, title, file_path, uploaded_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (session_id, subject_id, title, file_path, assistant_id))
        
        module_id = cur.lastrowid
        
        cur.execute("""
            INSERT INTO rag_source_documents 
            (subject_id, session_id, file_name, file_type, file_path, checksum, uploaded_by, is_indexed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
        """, (subject_id, session_id, filename, file_type, file_path, checksum, assistant_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✓ Modul terdaftar: {filename} (ID: {module_id})")
        
        return jsonify({
            "status": "success",
            "message": "Modul berhasil didaftarkan.",
            "module_id": module_id,
            "file_path": file_path,
            "file_name": filename,
            "checksum": checksum
        }), 201
        
    except Exception as e:
        print(f"✗ Error mendaftarkan modul: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500


@rag_bp.route("/task/<int:task_id>/status", methods=["PATCH"])
def update_task_status(task_id: int):
    """Update status assessment task (none/generating/draft/applied)."""
    data = request.get_json() or {}
    new_status = data.get("status")
    assistant_id = data.get("assistant_id")
    
    valid_statuses = ["none", "generating", "draft", "applied"]
    
    if not new_status or new_status not in valid_statuses:
        return jsonify({
            "error": "Status tidak valid.",
            "valid_statuses": valid_statuses
        }), 400
    
    if not assistant_id:
        return jsonify({"error": "assistant_id wajib diisi."}), 400
    
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, generation_status, title FROM assessment_task WHERE id = %s", (task_id,))
        task = cur.fetchone()
        
        if not task:
            return jsonify({"error": f"Task {task_id} tidak ditemukan"}), 404
        
        old_status = task["generation_status"]
        
        cur.execute("""
            UPDATE assessment_task 
            SET generation_status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (new_status, task_id))
        
        conn.commit()
        
        print(f"✓ Task {task_id} diperbarui: {old_status} → {new_status}")
        
        return jsonify({
            "status": "success",
            "message": f"Status berhasil diupdate dari '{old_status}' ke '{new_status}'.",
            "task_id": task_id,
            "old_status": old_status,
            "new_status": new_status
        }), 200
        
    except Exception as e:
        print(f"✗ Error memperbarui status: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500
        
    finally:
        if cur:
            try:
                cur.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass


@rag_bp.route("/subjects", methods=["GET"])
def get_subjects():
    """Mengambil semua subject untuk dropdown/seleksi."""
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
    """Mengambil semua module untuk subject tertentu."""
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


@rag_bp.route("/save-assessment", methods=["POST"])
def save_assessment():
    """
    Menyimpan assessment yang sudah di-approve dari mode preview.

    Request Body:
    {
        "subject_id": 1,
        "session_id": 1,
        "assistant_id": 1,
        "title": "Judul Assessment",
        "assessment_data": {
            "sections": {
                "soal": "konten soal...",
                "requirements": "requirements...",
                "expected_output": "expected output...",
                "kunci_jawaban": "kunci jawaban...",
                "notes": "notes..."
            },
            "metadata": { ... },
            "estimated_time": "60-90 menit"
        }
    }
    """
    try:
        data = request.get_json()

        required_fields = ["subject_id", "assistant_id", "assessment_data"]
        missing = [f for f in required_fields if f not in data]

        if missing:
            return jsonify({
                "error": f"Field wajib tidak ada: {', '.join(missing)}"
            }), 400

        subject_id = data["subject_id"]
        session_id = data.get("session_id", 0)
        assistant_id = data["assistant_id"]
        title = data.get("title")
        assessment_data = data["assessment_data"]

        task_id = save_approved_assessment(
            subject_id=subject_id,
            session_id=session_id,
            assistant_id=assistant_id,
            assessment_data=assessment_data,
            title=title
        )

        return jsonify({
            "status": "success",
            "message": "Assessment berhasil disimpan.",
            "task_id": task_id,
            "title": title,
            "estimated_time": assessment_data.get("estimated_time")
        }), 201

    except Exception as e:
        print(f"✗ Error menyimpan assessment: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500


@rag_bp.route("/generation-history/<int:subject_id>", methods=["GET"])
def generation_history(subject_id: int):
    """Mengambil riwayat generasi assessment untuk subject tertentu."""
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name as title, description, id_subject, created_at, updated_at
                FROM assessment_task
                WHERE id_subject = %s
                ORDER BY created_at DESC
            """, (subject_id,))
            data = cur.fetchall()

        return jsonify({
            "status": "success",
            "subject_id": subject_id,
            "total_records": len(data),
            "history": data
        }), 200

    except Exception as e:
        print(f"Error mengambil riwayat: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500

    finally:
        if conn:
            try:
                conn.close()
            except:
                pass
