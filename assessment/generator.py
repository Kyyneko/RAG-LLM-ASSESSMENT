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
    subject_name: str,
    assistant_id: int,
    context_snippets: list,
    custom_notes: str = None,
    generated_by: int = None,
    difficulty: str = "Sedang"
):
    """
    Generate assessment preview tanpa menyimpan ke database.

    Returns:
        dict: Assessment data yang bisa ditampilkan di FE
    """
    print("=" * 60)
    print(f"MENGHASILKAN PREVIEW ASSESSMENT")
    print("=" * 60)
    print(f"Subject: {subject_name} (ID: {subject_id})")
    print(f"Session: {topic} (ID: {session_id})")
    print(f"Context chunks: {len(context_snippets)}")
    if custom_notes:
        print(f"Catatan khusus: {custom_notes}")
    print("=" * 60)

    print("\nMemanggil LLM untuk menghasilkan assessment...")
    raw_output = generate_assessment_description(
        subject_name=subject_name,
        topic=topic,
        context_snippets=context_snippets,
        custom_notes=custom_notes,
        assessment_task_id=None,
        generation_type="preview",
        generated_by=generated_by,
        difficulty=difficulty
    )

    if not raw_output or not raw_output.strip():
        raise Exception("LLM tidak mengembalikan output")

    print(f"✓ LLM generation selesai ({len(raw_output)} karakter)")

    sections = parse_assessment_output(raw_output)

    preview_metadata = {
        "subject_id": subject_id,
        "session_id": session_id,
        "assistant_id": assistant_id,
        "topic": topic,
        "subject_name": subject_name,
        "context_count": len(context_snippets),
        "generated_at": datetime.now().isoformat(),
        "model": "openai/gpt-oss-120b:free",
        "custom_notes": custom_notes
    }

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

    current_section = None
    lines = raw_output.split('\n')

    for line in lines:
        line = line.strip()

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
            sections[current_section] += '\n' + line

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
    print(f"MENYIMPAN ASSESSMENT YANG DISETUJUI")
    print("=" * 60)

    sections = assessment_data.get('sections', {})
    metadata = assessment_data.get('metadata', {})

    raw_output = reconstruct_full_output(sections)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO assessment_task (
                    name, title, description, id_subject, id_score_component,
                    due_date, created_by, is_active, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                title or f"Assessment {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                title,
                raw_output,
                subject_id,
                1,
                None,
                assistant_id,
                1,
                datetime.now()
            ))

            task_id = cur.lastrowid

            conn.commit()
            print(f"✓ Assessment tersimpan dengan task_id: {task_id}")
            return task_id

    except Exception as e:
        conn.rollback()
        print(f"✗ Kesalahan database: {str(e)}")
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
    print(f"{'MENGGANTI DRAFT' if is_replace_mode else 'MEMBUAT'} ASSESSMENT TASK BARU")
    print("=" * 60)
    print(f"Subject: {subject_name} (ID: {subject_id})")
    print(f"Session: {topic} (ID: {session_id})")
    print(f"Context chunks: {len(context_snippets)}")
    if custom_notes:
        print(f"Catatan khusus: {custom_notes}")
    if is_replace_mode:
        print(f"Mode replace: memperbarui task_id={existing_task_id}")
    print("=" * 60)
    
    print("\nMemanggil LLM untuk menghasilkan teks...")
    raw_output = generate_assessment_description(
        subject_name=subject_name,
        topic=topic,
        context_snippets=context_snippets,
        custom_notes=custom_notes,
        assessment_task_id=existing_task_id,
        generation_type="assessment",
        generated_by=generated_by
    )
    
    if not raw_output or not raw_output.strip():
        raise Exception("LLM tidak mengembalikan output")
    
    print(f"✓ LLM generation selesai ({len(raw_output)} karakter)")
    
    required_tags = ["#SOAL", "#REQUIREMENTS", "#EXPECTED OUTPUT", "#KUNCI JAWABAN"]
    missing_tags = [tag for tag in required_tags if tag not in raw_output]
    
    if missing_tags:
        print(f"⚠️ Tag tidak lengkap: {', '.join(missing_tags)}")
    else:
        print(f"✓ Semua tag lengkap")
    
    generation_metadata = {
        "session_id": session_id,
        "topic": topic,
        "context_count": len(context_snippets),
        "generated_at": datetime.now().isoformat(),
        "model": "openai/gpt-oss-120b:free",
        "is_replacement": is_replace_mode
    }
    
    print("\nMenyimpan data ke database...")
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            if is_replace_mode:
                print(f"Memperbarui draft task_id={existing_task_id}...")
                cur.execute("""
                    UPDATE assessment_task SET
                        description = %s,
                        due_date = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    raw_output,
                    due_date,
                    existing_task_id
                ))
                task_id = existing_task_id
                action = "diperbarui"
                print(f"✓ Task {task_id} berhasil diperbarui")
                
            else:
                print("Membuat assessment baru...")
                cur.execute("""
                    INSERT INTO assessment_task (
                        name, title, description, id_subject, id_score_component,
                        due_date, created_by, is_active, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    f"Assessment {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    None,
                    raw_output,
                    subject_id,
                    1,
                    due_date,
                    assistant_id,
                    1,
                    datetime.now()
                ))
                task_id = cur.lastrowid
                action = "dibuat"
                print(f"✓ Task {task_id} berhasil dibuat")
            
            conn.commit()
            print(f"✓ Assessment berhasil {action} dan disimpan")
            
            return task_id
            
    except Exception as e:
        conn.rollback()
        print(f"✗ Kesalahan database: {str(e)}")
        raise e
        
    finally:
        conn.close()
