from .client import call_openrouter

# ======================================================
# ENHANCED SUBJECT-SPECIFIC CONFIGURATIONS
# ======================================================

SUBJECT_CONFIGS = {
    "Algoritma dan Pemrograman": {
        "language": "Python",
        "file_ext": "py",
        "concepts": "algoritma, struktur data, function, loop, error handling",
        "focus": "logika pemrograman dan problem solving",
        "typical_tasks": [
            "Pengolahan array/list dan operasi data",
            "Implementasi algoritma pencarian dan pengurutan",
            "Manipulasi string dan file I/O",
            "Penerapan fungsi rekursif",
            "Validasi input dan exception handling"
        ],
        "code_style": "procedural dengan fungsi-fungsi modular",
        "output_type": "console/terminal dengan input-output interaktif"
    },
    "Pemrograman Website": {
        "language": "HTML/CSS/JavaScript/PHP",
        "file_ext": "html/css/js/php",
        "concepts": "frontend, backend, form, database integration, API",
        "focus": "user interface dan interaksi web",
        "typical_tasks": [
            "Desain layout responsif dengan CSS",
            "Form validation menggunakan JavaScript",
            "CRUD operations dengan PHP dan MySQL",
            "AJAX untuk komunikasi asynchronous",
            "Session management dan autentikasi user"
        ],
        "code_style": "multi-file dengan separation of concerns (HTML/CSS/JS/PHP terpisah)",
        "output_type": "halaman web interaktif yang dapat diakses via browser"
    },
    "Basis Data": {
        "language": "SQL",
        "file_ext": "sql",
        "concepts": "DDL, DML, query, join, subquery, normalisasi, indexing",
        "focus": "desain database dan query optimization",
        "typical_tasks": [
            "Pembuatan skema database dengan DDL",
            "Query kompleks menggunakan JOIN dan subquery",
            "Implementasi stored procedure dan trigger",
            "Analisis data dengan aggregate functions",
            "Optimasi query dan indexing strategy"
        ],
        "code_style": "query SQL terstruktur dengan komentar untuk setiap bagian",
        "output_type": "hasil query dalam bentuk tabel dan penjelasan hasil eksekusi"
    },
    "OOP JAVA": {
        "language": "Java",
        "file_ext": "java",
        "concepts": "class, object, inheritance, polymorphism, encapsulation, interface",
        "focus": "object-oriented design dan design patterns",
        "typical_tasks": [
            "Desain class hierarchy dengan inheritance",
            "Implementasi interface dan abstract class",
            "Penerapan encapsulation dengan getter/setter",
            "Polymorphism melalui method overriding",
            "Exception handling dengan try-catch-finally"
        ],
        "code_style": "multi-class dengan package structure yang jelas",
        "output_type": "console application dengan interaksi object-oriented"
    },
    "Pemrograman Mobile": {
        "language": "Java (Android)",
        "file_ext": "java",
        "concepts": "Activity, Fragment, Intent, RecyclerView, ViewModel, LiveData",
        "focus": "android UI/UX dan lifecycle management",
        "typical_tasks": [
            "Implementasi multi-screen dengan Activity/Fragment",
            "Data passing menggunakan Intent dan Bundle",
            "List display dengan RecyclerView dan Adapter",
            "State management dengan ViewModel dan LiveData",
            "Local storage dengan SharedPreferences atau Room"
        ],
        "code_style": "Android project structure dengan Activity, Adapter, dan XML layout",
        "output_type": "screenshot UI dan penjelasan navigation flow aplikasi"
    },
}


def get_subject_config(subject_name: str) -> dict:
    """
    Mengambil konfigurasi bahasa dan konsep berdasarkan nama mata kuliah.

    Args:
        subject_name (str): Nama mata kuliah.

    Returns:
        dict: {language, file_ext, concepts, focus, typical_tasks, code_style, output_type}
    """
    subject_lower = subject_name.lower()

    for key, config in SUBJECT_CONFIGS.items():
        if key.lower() in subject_lower or subject_lower in key.lower():
            return config

    # Default fallback
    return {
        "language": "Programming",
        "file_ext": "code",
        "concepts": "programming fundamentals",
        "focus": "general programming",
        "typical_tasks": ["basic programming tasks"],
        "code_style": "clean and readable code",
        "output_type": "expected program output"
    }


def build_subject_specific_examples(config: dict) -> str:
    """
    Membuat contoh format soal yang spesifik untuk setiap mata kuliah.
    """
    language = config["language"]
    focus = config["focus"]
    tasks = "\n".join([f"   - {task}" for task in config["typical_tasks"][:3]])
    
    return f"""
**KARAKTERISTIK SOAL {language.upper()}:**

Fokus utama: {focus}

Tipe tugas yang umum:
{tasks}

Style kode: {config["code_style"]}
Tipe output: {config["output_type"]}
"""


def generate_assessment_description(
    subject_name: str,
    topic: str,
    class_name: str,
    context_snippets: list,
    module_names: list[str] = None,
    custom_notes: str = None,
) -> str:
    """
    Membuat deskripsi tugas praktikum lintas mata kuliah (multi-language).

    Mendukung:
      - Algoritma & Pemrograman (Python)
      - Pemrograman Website (HTML/CSS/JS/PHP)
      - Basis Data (SQL)
      - OOP JAVA (Java)
      - Pemrograman Mobile (Kotlin/Java)

    Returns:
        str: Deskripsi soal ber-tag (#SOAL, #REQUIREMENTS, #EXPECTED OUTPUT, #KUNCI JAWABAN)
    """

    # ======================================================
    # VALIDATION & DEBUG LOGGING
    # ======================================================
    print("\n[DEBUG] Generating assessment...")
    print(f"[DEBUG] Subject : {subject_name}")
    print(f"[DEBUG] Topic   : {topic}")
    print(f"[DEBUG] Class   : {class_name}")
    print(f"[DEBUG] Context : {len(context_snippets) if context_snippets else 0}")
    if custom_notes:
        print(f"[DEBUG] Custom notes: {custom_notes[:100]}...")

    if not subject_name.strip():
        raise ValueError("subject_name tidak boleh kosong!")
    if not topic.strip():
        raise ValueError("topic tidak boleh kosong!")
    if not class_name.strip():
        raise ValueError("class_name tidak boleh kosong!")

    # ======================================================
    # SUBJECT CONFIG
    # ======================================================
    config = get_subject_config(subject_name)
    language = config["language"]
    concepts = config["concepts"]
    focus = config["focus"]
    typical_tasks = config["typical_tasks"]
    code_style = config["code_style"]
    output_type = config["output_type"]
    
    print(f"[DEBUG] Detected language: {language}")
    print(f"[DEBUG] Focus area: {focus}")

    # ======================================================
    # NORMALIZE CONTEXT SNIPPETS
    # ======================================================
    normalized_snippets = []
    if context_snippets:
        for item in context_snippets:
            if isinstance(item, dict):
                text = item.get("text", "")
                if text.strip():
                    normalized_snippets.append(text.strip())
            elif isinstance(item, str) and item.strip():
                normalized_snippets.append(item.strip())

        print(f"[DEBUG] Normalized {len(normalized_snippets)} snippets")

    # ======================================================
    # BUILD CONTEXT TEXT
    # ======================================================
    if normalized_snippets:
        if module_names:
            if len(module_names) > 1:
                module_info = "Soal dibuat dari gabungan modul:\n"
                module_info += "\n".join(
                    [f"{i+1}. {m}" for i, m in enumerate(module_names)]
                )
            else:
                module_info = f"Soal dibuat dari modul: {module_names[0]}"
        else:
            module_info = "Referensi modul praktikum:"

        context_parts = []
        for i, snippet in enumerate(normalized_snippets[:5], 1):
            if len(snippet) > 2000:
                snippet = snippet[:2000] + "... [truncated]"
            context_parts.append(f"[Konteks {i}]\n{snippet}")

        context_text = f"{module_info}\n\n" + "\n\n".join(context_parts)
        print(f"[DEBUG] Context length: {len(context_text)} chars")
    else:
        print("⚠️ WARNING: No context!")
        context_text = f"(Tidak ada konteks, buat soal umum tentang {concepts})"

    # ======================================================
    # SUBJECT-SPECIFIC EXAMPLES
    # ======================================================
    subject_examples = build_subject_specific_examples(config)

    # ======================================================
    # ENHANCED SYSTEM MESSAGE (Subject-Aware)
    # ======================================================
    system_message = {
        "role": "system",
        "content": f"""Anda adalah asisten dosen ahli yang membuat soal praktikum untuk mata kuliah {subject_name}.

**KEAHLIAN KHUSUS ANDA:**
- Bahasa/Teknologi: {language}
- Fokus pembelajaran: {focus}
- Konsep utama: {concepts}

**PRINSIP PEMBUATAN SOAL:**
1. Soal harus mencerminkan karakteristik khas {subject_name}
2. Tingkat kesulitan sesuai dengan topik "{topic}"
3. Implementasi menggunakan best practices {language}
4. Kode harus lengkap, dapat dijalankan, dan production-ready
5. Sertakan komentar yang jelas untuk bagian-bagian penting
6. Gunakan bahasa Indonesia formal dan profesional

**STRUKTUR OUTPUT WAJIB:**
#SOAL - Deskripsi tugas yang jelas dan terstruktur
#REQUIREMENTS - 5-7 persyaratan teknis spesifik {language}
#EXPECTED OUTPUT - {output_type}
#KUNCI JAWABAN - {code_style}

**LARANGAN:**
- Jangan gunakan kata "HOTS" atau "C1-C6"
- Jangan buat soal generic yang bisa untuk semua bahasa
- Jangan gunakan placeholder atau kode tidak lengkap
- Jangan abaikan karakteristik khusus {subject_name}"""
    }

    # ======================================================
    # ENHANCED USER INSTRUCTION
    # ======================================================
    user_instruction = f"""
Buatkan tugas praktikum untuk mata kuliah **{subject_name}** dengan spesifikasi berikut:

=== INFORMASI DASAR ===
Mata Kuliah: {subject_name}
Kelas      : {class_name}
Topik      : {topic}
Teknologi  : {language}

=== KARAKTERISTIK SOAL ===
{subject_examples}

=== PANDUAN FITUR/KOMPONEN ===
Buat soal dengan 4-6 fitur yang relevan dengan {subject_name}, misalnya:
{chr(10).join([f"{i+1}. {task}" for i, task in enumerate(typical_tasks)])}

=== REQUIREMENTS TEKNIS ===
Pastikan requirements mencakup:
- Konsep inti: {concepts}
- Best practices {language}
- Error handling dan validasi
- Code organization dan readability
- Testing atau demonstration case
"""

    if custom_notes and custom_notes.strip():
        user_instruction += f"""
=== CATATAN KHUSUS DARI ASISTEN LAB ===
{custom_notes.strip()}

⚠️ PENTING: Ikuti semua poin di catatan khusus ini.
Pastikan soal mengakomodasi permintaan spesifik di atas.
"""

    user_instruction += f"""
=== KONTEKS DARI MODUL ===
{context_text}

=== FORMAT OUTPUT YANG DIHARAPKAN ===

#SOAL
[Judul Tugas yang Menarik]

Buatlah [jenis aplikasi/sistem] menggunakan {language} dengan fitur-fitur berikut:

1. [Fitur 1 - spesifik untuk {language}]
2. [Fitur 2 - terapkan konsep {concepts}]
3. [Fitur 3 - dengan error handling]
4. [Fitur 4 - dengan validasi]
5. [Fitur 5 - (opsional) fitur tambahan]

Deskripsi detail tentang skenario atau use case...

#REQUIREMENTS
1. [Requirement teknis 1 - spesifik {language}]
2. [Requirement teknis 2 - best practice]
3. [Requirement teknis 3 - konsep utama]
4. [Requirement teknis 4 - error handling]
5. [Requirement teknis 5 - code quality]
6. [Requirement teknis 6 - documentation]
7. [Requirement teknis 7 - testing/demo]

#EXPECTED OUTPUT
[Deskripsi output sesuai {output_type}]
[Contoh konkret hasil eksekusi atau tampilan]
[Screenshot/gambaran hasil akhir jika perlu]

#KUNCI JAWABAN
[Kode {language} lengkap dengan struktur {code_style}]
[Sertakan komentar untuk menjelaskan logika penting]
[Pastikan kode dapat langsung dijalankan]

---

**INSTRUKSI AKHIR:**
- Buat soal yang KHAS untuk {subject_name}, bukan soal generic
- Gunakan terminologi dan pattern yang spesifik untuk {language}
- Kode harus production-ready dengan error handling lengkap
- Output harus sesuai dengan {output_type}
- Gunakan bahasa Indonesia formal dan profesional
"""

    # ======================================================
    # BUILD MESSAGES
    # ======================================================
    user_message = {"role": "user", "content": user_instruction}
    messages = [system_message, user_message]

    # ======================================================
    # DEBUG STATISTICS
    # ======================================================
    total_len = len(system_message["content"]) + len(user_message["content"])
    print(f"\n[DEBUG] Prompt length: {total_len} chars (~{total_len // 4} tokens)")
    if total_len < 100:
        raise ValueError(f"Prompt too short ({total_len} chars)!")

    # ======================================================
    # CALL LLM
    # ======================================================
    print(f"\n[DEBUG] Calling LLM for {language}...")
    result = call_openrouter(messages)

    if not result or not result.strip():
        raise Exception("LLM returned empty response.")

    print(f"\n[DEBUG] Response: {len(result)} chars")
    print(f"Preview: {result[:150]}...")

    # ======================================================
    # VALIDATE TAGS
    # ======================================================
    required_tags = ["#SOAL", "#REQUIREMENTS", "#EXPECTED OUTPUT", "#KUNCI JAWABAN"]
    missing = [t for t in required_tags if t not in result]

    if missing:
        print(f"⚠️ Missing tags: {', '.join(missing)}")
    else:
        print("✓ All required tags present")

    return result