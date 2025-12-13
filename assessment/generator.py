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


def preview_rag_generated_assessment(
    subject_id: int,
    session_id: int,
    topic: str,
    class_name: str,
    subject_name: str,
    assistant_id: int,
    context_snippets: list,
    custom_notes: str = None,
    generated_by: int = None
):
    """
    Generate assessment preview tanpa menyimpan ke database.

    Returns:
        dict: Assessment data yang bisa ditampilkan di FE
    """
    print("=" * 60)
    print(f"GENERATING ASSESSMENT PREVIEW")
    print("=" * 60)
    print(f"Subject: {subject_name} (ID: {subject_id})")
    print(f"Session: {topic} (ID: {session_id})")
    print(f"Class: {class_name}")
    print(f"Context chunks: {len(context_snippets)}")
    if custom_notes:
        print(f"Custom notes: {custom_notes}")
    print("=" * 60)

    # 1. Generate dengan LLM
    print("\nMemanggil LLM untuk menghasilkan assessment...")
    raw_output = generate_assessment_description(
        subject_name=subject_name,
        topic=topic,
        class_name=class_name,
        context_snippets=context_snippets,
        custom_notes=custom_notes,
        assessment_task_id=None,  # Preview mode - no task_id yet
        generation_type="preview",
        generated_by=generated_by  # Track which assistant generated this preview
    )

    if not raw_output or not raw_output.strip():
        raise Exception("LLM tidak mengembalikan output")

    print(f"SUCCESS: LLM generation complete ({len(raw_output)} characters)")

    # 2. Parse response untuk memisahkan sections
    sections = parse_assessment_output(raw_output)

    # 3. Generate metadata
    preview_metadata = {
        "subject_id": subject_id,
        "session_id": session_id,
        "assistant_id": assistant_id,
        "topic": topic,
        "class_name": class_name,
        "subject_name": subject_name,
        "context_count": len(context_snippets),
        "generated_at": datetime.now().isoformat(),
        "model": "google/gemini-2.0-flash-exp:free",
        "custom_notes": custom_notes
    }

    # 4. Return preview data
    return {
        "status": "success",
        "preview": {
            "sections": sections,
            "raw_output": raw_output,
            "metadata": preview_metadata,
            "estimated_time": estimate_assessment_time(sections)
        }
    }


def parse_assessment_output(raw_output: str) -> dict:
    """
    Parse LLM output untuk memisahkan sections.

    Returns:
        dict: Sections parsed dari output
    """
    sections = {
        "soal": "",
        "requirements": "",
        "expected_output": "",
        "kunci_jawaban": "",
        "notes": ""
    }

    # Parse sections berdasarkan tags
    current_section = None
    lines = raw_output.split('\n')

    for line in lines:
        line = line.strip()

        # Detect section headers
        if line.startswith('#SOAL'):
            current_section = 'soal'
            sections[current_section] = line.replace('#SOAL', '').strip()
        elif line.startswith('#REQUIREMENTS'):
            current_section = 'requirements'
            sections[current_section] = line.replace('#REQUIREMENTS', '').strip()
        elif line.startswith('#EXPECTED OUTPUT'):
            current_section = 'expected_output'
            sections[current_section] = line.replace('#EXPECTED OUTPUT', '').strip()
        elif line.startswith('#KUNCI JAWABAN'):
            current_section = 'kunci_jawaban'
            sections[current_section] = line.replace('#KUNCI JAWABAN', '').strip()
        elif line.startswith('#NOTES'):
            current_section = 'notes'
            sections[current_section] = line.replace('#NOTES', '').strip()
        elif current_section and line:
            # Append content to current section
            sections[current_section] += '\n' + line

    # Clean up sections
    for key in sections:
        sections[key] = sections[key].strip()

    return sections


def estimate_assessment_time(sections: dict) -> str:
    """
    Estimasi waktu pengerjaan assessment berdasarkan complexity.
    """
    soal_length = len(sections.get('soal', ''))
    requirements_count = len(sections.get('requirements', '').split('\n'))

    if soal_length > 500 or requirements_count > 10:
        return "90-120 menit"
    elif soal_length > 200 or requirements_count > 5:
        return "60-90 menit"
    else:
        return "30-60 menit"


def save_approved_assessment(
    subject_id: int,
    session_id: int,
    assistant_id: int,
    assessment_data: dict,
    title: str = None
):
    """
    Simpan assessment yang sudah di-approve ke database.

    Args:
        assessment_data: Data dari preview (sections, metadata, etc.)
        title: Judul assessment (optional)

    Returns:
        int: task_id yang tersimpan
    """
    print("=" * 60)
    print(f"SAVING APPROVED ASSESSMENT")
    print("=" * 60)

    sections = assessment_data.get('sections', {})
    metadata = assessment_data.get('metadata', {})

    # Reconstruct full output
    raw_output = reconstruct_full_output(sections)

    # Create database record
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO assessment_task (
                    name, title, description, id_subject, id_score_component,
                    due_date, created_by, is_active, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                title or f"Assessment {datetime.now().strftime('%Y%m%d_%H%M%S')}",  # name
                title,  # title
                raw_output,  # description
                subject_id,  # id_subject
                1,  # id_score_component (default)
                None,  # due_date
                assistant_id,  # created_by
                1,  # is_active
                datetime.now()  # created_at
            ))

            task_id = cur.lastrowid

            # Log to ai_generation_log
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
                    "subject": metadata.get('subject_name'),
                    "topic": metadata.get('topic'),
                    "class": metadata.get('class_name'),
                    "action": "approved_and_saved"
                }),
                raw_output,
                json.dumps({
                    "context_count": metadata.get('context_count', 0),
                    "preview_mode": True
                }),
                metadata.get('model', 'google/gemini-2.0-flash-exp:free'),
                'success',
                assistant_id
            ))

            conn.commit()
            print(f"SUCCESS: Assessment saved with task_id: {task_id}")
            return task_id

    except Exception as e:
        conn.rollback()
        print(f"ERROR: Database error: {str(e)}")
        raise e

    finally:
        conn.close()


def reconstruct_full_output(sections: dict) -> str:
    """
    Reconstruct full LLM output dari sections.
    """
    output_parts = []

    if sections.get('soal'):
        output_parts.append(f"#SOAL\n{sections['soal']}")

    if sections.get('requirements'):
        output_parts.append(f"#REQUIREMENTS\n{sections['requirements']}")

    if sections.get('expected_output'):
        output_parts.append(f"#EXPECTED OUTPUT\n{sections['expected_output']}")

    if sections.get('kunci_jawaban'):
        output_parts.append(f"#KUNCI JAWABAN\n{sections['kunci_jawaban']}")

    if sections.get('notes'):
        output_parts.append(f"#NOTES\n{sections['notes']}")

    return '\n\n'.join(output_parts)


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
    custom_notes: str = None,
    generated_by: int = None 
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
        custom_notes=custom_notes,
        assessment_task_id=existing_task_id,
        generation_type="assessment",
        generated_by=generated_by  # Pass user ID to logging
    )
    
    if not raw_output or not raw_output.strip():
        raise Exception("LLM tidak mengembalikan output")
    
    print(f"SUCCESS: LLM generation complete ({len(raw_output)} characters)")
    
    # 2. Validation - Check required tags
    required_tags = ["#SOAL", "#REQUIREMENTS", "#EXPECTED OUTPUT", "#KUNCI JAWABAN"]
    missing_tags = [tag for tag in required_tags if tag not in raw_output]
    
    if missing_tags:
        print(f"WARNING: WARNING: Missing tags: {', '.join(missing_tags)}")
    else:
        print(f"SUCCESS: Semua tag lengkap")
    
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
                        description = %s,
                        due_date = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    raw_output,  # Full LLM output ke description
                    due_date,
                    existing_task_id
                ))
                task_id = existing_task_id
                action = "updated"
                print(f"SUCCESS: Task {task_id} updated successfully")
                
            else:
                # Mode INSERT
                print("Membuat assessment baru...")
                cur.execute("""
                    INSERT INTO assessment_task (
                        name, title, description, id_subject, id_score_component,
                        due_date, created_by, is_active, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    f"Assessment {datetime.now().strftime('%Y%m%d_%H%M%S')}",  # name
                    None,  # title (akan diisi manual)
                    raw_output,  # description
                    subject_id,  # id_subject
                    1,  # id_score_component (default)
                    due_date,
                    assistant_id,
                    1,  # is_active
                    datetime.now()  # created_at
                ))
                task_id = cur.lastrowid
                action = "created"
                print(f"SUCCESS: Task {task_id} created successfully")
            
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
            print(f"SUCCESS: Assessment {action} dan log berhasil disimpan")
            
            return task_id
            
    except Exception as e:
        conn.rollback()
        print(f"ERROR: Database error: {str(e)}")
        raise e
        
    finally:
        conn.close()
