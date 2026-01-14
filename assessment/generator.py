import logging
from datetime import datetime
from db.connection import get_connection
from llm.generator import generate_assessment_description

logger = logging.getLogger(__name__)


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
    logger.info(f"Generating assessment preview for {subject_name}")
    logger.debug(f"Subject: {subject_name} (ID: {subject_id})")
    logger.debug(f"Session: {topic} (ID: {session_id})")
    logger.debug(f"Context chunks: {len(context_snippets)}")
    if custom_notes:
        logger.debug(f"Custom notes: {custom_notes}")

    logger.info("Calling LLM to generate assessment...")
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

    logger.info(f"LLM generation completed ({len(raw_output)} characters)")

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
