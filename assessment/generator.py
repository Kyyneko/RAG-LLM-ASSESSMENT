# assessment/generator.py

import json
from datetime import datetime
from db.connection import get_connection
from llm.generator import generate_assessment_description


def extract_text_from_context(context):
    """Extract text from context (handle both dict and string format)."""
    if isinstance(context, dict):
        return context.get("text", "")
    elif isinstance(context, str):
        return context
    else:
        return str(context)


def check_draft_assessment_for_subject(subject_id: int):
    """Memeriksa apakah ada assessment dengan status 'draft' untuk subject tertentu."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, created_at, session_id
                FROM assessment_task
                WHERE subject_id = %s AND generation_status = 'draft'
                ORDER BY created_at DESC
                LIMIT 1
            """, (subject_id,))
            
            result = cur.fetchone()
            
            if not result:
                return {
                    'has_draft': False,
                    'task_id': None,
                    'title': None,
                    'session_id': None,
                    'created_at': None
                }
            
            return {
                'has_draft': True,
                'task_id': result['id'],
                'title': result['title'],
                'session_id': result['session_id'],
                'created_at': result['created_at']
            }
    finally:
        conn.close()


def create_rag_generated_task(
    subject_id: int,
    session_id: int,
    topic: str,
    class_name: str,
    subject_name: str,
    assistant_id: int,
    context_snippets: list,
    due_date=None,
    existing_task_id=None,
    custom_notes: str = None 
):
    """
    Menghasilkan assessment task menggunakan RAG + LLM.
    
    Args:
        custom_notes: Catatan/instruksi tambahan dari asisten lab (optional)
    """
    is_replace_mode = existing_task_id is not None
    
    print("=" * 60)
    print(f"{'REPLACING DRAFT' if is_replace_mode else 'CREATING NEW'} ASSESSMENT TASK")
    print("=" * 60)
    print(f"Subject: {subject_name} (ID: {subject_id})")
    print(f"Session: {topic} (ID: {session_id})")
    print(f"Class: {class_name}")
    print(f"Context chunks: {len(context_snippets)}")
    if custom_notes:
        print(f"Custom notes: {custom_notes}")
    if is_replace_mode:
        print(f"Replace mode: updating existing task_id={existing_task_id}")
    print("=" * 60)
    
    # 1. Generate dengan LLM (with custom notes)
    print("\nMemanggil LLM untuk menghasilkan teks...")
    raw_output = generate_assessment_description(
        subject_name=subject_name,
        topic=topic,
        class_name=class_name,
        context_snippets=context_snippets,
        custom_notes=custom_notes 
    )
    
    if not raw_output or not raw_output.strip():
        raise Exception("LLM tidak mengembalikan output")
    
    print(f"✓ LLM generation complete ({len(raw_output)} characters)")
    
    # 2. Validation - Check required tags
    required_tags = ["#SOAL", "#REQUIREMENTS", "#EXPECTED OUTPUT", "#KUNCI JAWABAN"]
    missing_tags = [tag for tag in required_tags if tag not in raw_output]
    
    if missing_tags:
        print(f"⚠️ WARNING: Missing tags: {', '.join(missing_tags)}")
    else:
        print(f"✓ Semua tag lengkap")
    
    # 3. Metadata generation
    generation_metadata = {
        "session_id": session_id,
        "topic": topic,
        "class_name": class_name,
        "context_count": len(context_snippets),
        "generated_at": datetime.now().isoformat(),
        "model": "google/gemini-2.0-flash-exp:free",
        "is_replacement": is_replace_mode
    }
    
    # 4. Simpan ke database
    print("\nMenyimpan data ke database...")
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            if is_replace_mode:
                # Mode UPDATE
                print(f"Memperbarui draft task_id={existing_task_id}...")
                cur.execute("""
                    UPDATE assessment_task SET
                        session_id = %s,
                        description = %s,
                        due_date = %s,
                        ai_generated_description = %s,
                        generation_metadata = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    session_id,
                    raw_output,  # ✅ Full LLM output ke description
                    due_date,
                    raw_output,
                    json.dumps(generation_metadata),
                    existing_task_id
                ))
                task_id = existing_task_id
                action = "updated"
                print(f"✓ Task {task_id} updated successfully")
                
            else:
                # Mode INSERT
                print("Membuat assessment baru...")
                cur.execute("""
                    INSERT INTO assessment_task (
                        subject_id, session_id, title, description, due_date, created_by,
                        source_type, generation_status, ai_generated_description, generation_metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    subject_id,
                    session_id,
                    None,  # ✅ title = NULL (akan diisi manual)
                    raw_output,  # ✅ Full LLM output ke description
                    due_date,
                    assistant_id,
                    'rag_generated',
                    'draft',
                    raw_output,
                    json.dumps(generation_metadata)
                ))
                task_id = cur.lastrowid
                action = "created"
                print(f"✓ Task {task_id} created successfully")
            
            # 5. Insert ke ai_generation_log
            print("Mencatat ke tabel ai_generation_log...")
            
            # Extract text from contexts (handle dict format)
            context_texts = [extract_text_from_context(c) for c in context_snippets]
            
            cur.execute("""
                INSERT INTO ai_generation_log (
                    assessment_task_id, generation_type, prompt_parameters,
                    generated_content, source_materials, model_used,
                    generation_status, generated_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                task_id,
                'description',
                json.dumps({
                    "subject": subject_name,
                    "topic": topic,
                    "class": class_name,
                    "action": action
                }),
                raw_output,
                json.dumps({
                    "context_count": len(context_texts),
                    "contexts_preview": [text[:120] for text in context_texts[:3]]
                }),
                "google/gemini-2.0-flash-exp:free",
                'success',
                assistant_id
            ))
            
            conn.commit()
            print(f"✓ Assessment {action} dan log berhasil disimpan")
            
            return task_id
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Database error: {str(e)}")
        raise e
        
    finally:
        conn.close()
