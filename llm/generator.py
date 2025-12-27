import time
import logging
from .client import call_openrouter

logger = logging.getLogger(__name__)

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

# ============== URUTAN KURIKULUM LAB SI ==============
# Digunakan untuk memastikan soal hanya menggunakan konsep yang SUDAH diajarkan
CURRICULUM_ORDER = {
    "Algoritma dan Pemrograman": [
        "Data Types",
        "Collection", 
        "Operator",
        "Condition",
        "Looping",
        "Function",
        "Error Handling & RegEx",
        "OOP"
    ],
    "Pemrograman Website": [
        "HTML",
        "CSS",
        "JavaScript",
        "Database Connection",
        "Laravel"
    ],
    "OOP JAVA": [
        "Pengenalan Java",
        "Class dan Object",
        "Attribute",
        "Behavior",
        "Constructor",
        "Encapsulation",
        "Abstract Class",
        "Interface",
        "Inheritance",
        "Thread",
        "Polymorphism"
    ],
    "Pemrograman Mobile": [
        "Activity",
        "Intent",
        "RecyclerView",
        "Fragment",
        "Background Thread",
        "Networking",
        "SharedPreferences",
        "SQLite"
    ],
    "Basis Data": [
        "DDL",
        "Query Dasar",
        "DML",
        "Operator",
        "Relationship",
        "Join",
        "Function",
        "Grouping",
        "Subquery",
        "Union",
        "Intersect",
        "Except",
        "Transaction",
        "Index & Control Flow"
    ]
}


def get_curriculum_context(subject_name: str, topic: str) -> str:
    """
    Generate curriculum context untuk prompt, menentukan materi yang sudah diajarkan.
    
    Args:
        subject_name: Nama mata kuliah
        topic: Topik/modul saat ini
        
    Returns:
        String curriculum context untuk dimasukkan ke prompt
    """
    # Normalize subject name
    subject_key = None
    subject_lower = subject_name.lower()
    for key in CURRICULUM_ORDER.keys():
        if key.lower() in subject_lower or subject_lower in key.lower():
            subject_key = key
            break
    
    if not subject_key:
        return ""  # Unknown subject, skip curriculum context
    
    curriculum = CURRICULUM_ORDER[subject_key]
    topic_lower = topic.lower()
    
    # Find current module position (fuzzy match)
    # IMPORTANT: For combined topics like "Data Types, Collection & Operator",
    # we need to find the HIGHEST matching module to include all allowed concepts
    current_idx = -1
    matched_modules = []
    
    for idx, module in enumerate(curriculum):
        module_lower = module.lower()
        # Check if topic contains module name or vice versa (exact match preferred)
        if module_lower == topic_lower:
            # Exact match - highest priority
            matched_modules.append((idx, module, 2))  # priority 2 = exact
        elif module_lower in topic_lower or topic_lower in module_lower:
            matched_modules.append((idx, module, 1))  # priority 1 = substring
        
        # Check for partial match (e.g., "Data Types, Collection" matches "Data Types")
        for part in topic.split(","):
            part = part.strip().lower()
            # Also handle "&" separator
            for subpart in part.split("&"):
                subpart = subpart.strip()
                # Only match if subpart is substantial (at least 4 chars) and matches well
                if len(subpart) >= 4 and (subpart == module_lower or module_lower == subpart):
                    matched_modules.append((idx, module, 2))  # exact part match
                elif len(subpart) >= 4 and (subpart in module_lower or module_lower in subpart):
                    # Only add if not already matched and significant overlap
                    if len(subpart) >= 4 and len(module_lower) >= 4:
                        matched_modules.append((idx, module, 1))
    # Take the best match: prioritize by (priority DESC, index for topic position)
    if matched_modules:
        # Sort by priority (descending), then by index 
        # For same priority, prefer the match that best fits the topic
        best_match = max(matched_modules, key=lambda x: (x[2], -abs(curriculum.index(x[1]) - len(curriculum)//2)))
        current_idx = best_match[0]
        print(f"[DEBUG] Matched modules: {list(set([m for _, m, _ in matched_modules]))}, using: {curriculum[current_idx]} (priority={best_match[2]})")
    
    if current_idx == -1:
        # Topic not found in curriculum, assume it's a new/combined module
        # Place it at the end of known curriculum
        return f"""
=== KONTEKS KURIKULUM ===
Mata Kuliah: {subject_key}
Modul: {topic} (modul baru/gabungan - diasumsikan setelah modul terakhir)

Urutan materi dalam kurikulum:
{chr(10).join([f"  {i+1}. {m}" for i, m in enumerate(curriculum)])}

⚠️ SANGAT PENTING - PEMBATASAN MATERI:
- Karena posisi modul tidak diketahui, asumsikan SEMUA materi sebelumnya sudah diajarkan
- BOLEH menggunakan semua konsep dari daftar di atas
- JANGAN gunakan konsep yang jelas-jelas di luar kurikulum mata kuliah ini
"""
    
    # Generate list of allowed concepts (current + all previous)
    allowed_modules = curriculum[:current_idx + 1]
    forbidden_modules = curriculum[current_idx + 1:] if current_idx < len(curriculum) - 1 else []
    
    context = f"""
=== KONTEKS KURIKULUM - SANGAT PENTING! ===
Mata Kuliah: {subject_key}
Modul Saat Ini: {topic} (urutan ke-{current_idx + 1} dari {len(curriculum)})

✅ MATERI YANG SUDAH DIAJARKAN (BOLEH digunakan):
{chr(10).join([f"  {i+1}. {m}" for i, m in enumerate(allowed_modules)])}
"""
    
    if forbidden_modules:
        context += f"""
❌ MATERI YANG BELUM DIAJARKAN (DILARANG digunakan):
{chr(10).join([f"  - {m}" for m in forbidden_modules])}

⚠️ PEMBATASAN KERAS:
- JANGAN gunakan konsep dari materi yang BELUM diajarkan
- Contoh: Jika modul saat ini "Looping", JANGAN gunakan "Function" atau "OOP"
- Soal dan kunci jawaban HARUS bisa dikerjakan dengan materi yang SUDAH diajarkan saja
"""
    else:
        context += """
✅ Ini adalah modul terakhir, semua materi sebelumnya boleh digunakan.
"""
    
    return context


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

    return {
        "language": "Programming",
        "file_ext": "code",
        "concepts": "programming fundamentals",
        "focus": "general programming",
        "typical_tasks": ["basic programming tasks"],
        "code_style": "clean and readable code",
        "output_type": "expected program output"
    }


def generate_assessment_description(
    subject_name: str,
    topic: str,
    context_snippets: list,
    module_names: list[str] = None,
    custom_notes: str = None,
    assessment_task_id: int = None,
    generation_type: str = "assessment",
    generated_by: int = None,
    difficulty: str = "Sedang",
) -> str:
    """
    Membuat deskripsi tugas praktikum lintas mata kuliah (multi-language).

    Mendukung:
      - Algoritma & Pemrograman (Python)
      - Pemrograman Website (HTML/CSS/JS/PHP)
      - Basis Data (SQL)
      - OOP JAVA (Java)
      - Pemrograman Mobile (Kotlin/Java)

    Args:
        subject_name (str): Nama mata kuliah
        topic (str): Topik materi
        context_snippets (list): Konteks materi
        module_names (list): Nama modul
        custom_notes (str): Catatan khusus
        assessment_task_id (int): ID assessment task untuk logging
        generation_type (str): Tipe generasi ('assessment', 'preview', 'test')
        generated_by (int): ID user yang melakukan request

    Returns:
        str: Deskripsi soal ber-tag (#SOAL, #REQUIREMENTS, #EXPECTED OUTPUT, #KUNCI JAWABAN)
    """

    print("\n[DEBUG] Menghasilkan assessment...")
    print(f"[DEBUG] Subject : {subject_name}")
    print(f"[DEBUG] Topik   : {topic}")
    print(f"[DEBUG] Konteks : {len(context_snippets) if context_snippets else 0}")
    if custom_notes:
        print(f"[DEBUG] Catatan khusus: {custom_notes[:100]}...")

    if not subject_name.strip():
        raise ValueError("subject_name tidak boleh kosong!")
    if not topic.strip():
        raise ValueError("topic tidak boleh kosong!")

    config = get_subject_config(subject_name)
    language = config["language"]
    concepts = config["concepts"]
    focus = config["focus"]
    code_style = config["code_style"]
    output_type = config["output_type"]

    print(f"[DEBUG] Bahasa terdeteksi: {language}")
    print(f"[DEBUG] Area fokus: {focus}")

    normalized_snippets = []
    if context_snippets:
        for item in context_snippets:
            if isinstance(item, dict):
                text = item.get("text", "")
                if text.strip():
                    normalized_snippets.append(text.strip())
            elif isinstance(item, str) and item.strip():
                normalized_snippets.append(item.strip())

        print(f"[DEBUG] {len(normalized_snippets)} snippets dinormalisasi")

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
                snippet = snippet[:2000] + "... [dipotong]"
            context_parts.append(f"[Konteks {i}]\n{snippet}")

        context_text = f"{module_info}\n\n" + "\n\n".join(context_parts)
        print(f"[DEBUG] Panjang konteks: {len(context_text)} karakter")
    else:
        print("⚠️ Tidak ada konteks!")
        context_text = f"(Tidak ada konteks, buat soal umum tentang {concepts})"

    system_message = {
        "role": "system",
        "content": f"""Anda adalah asisten dosen EXPERT yang membuat SOAL CERITA praktikum untuk mata kuliah {subject_name}.

DEFINISI SOAL CERITA:
Soal cerita adalah soal yang memiliki KONTEKS NARATIF dengan tokoh, tempat, dan situasi nyata.
Soal HARUS dimulai dengan cerita/skenario, BUKAN langsung perintah teknis.

CONTOH SOAL CERITA YANG BENAR:
✅ "Toko Elektronik 'Maju Jaya' milik Pak Budi memberikan diskon khusus untuk pelanggan setia. 
Jika total belanja lebih dari Rp 1.000.000, pelanggan mendapat diskon 15%. 
Jika pelanggan adalah member, ada tambahan diskon 5%. 
Buatlah program kasir untuk menghitung total yang harus dibayar pelanggan..."

✅ "Perpustakaan kampus UNHAS menerapkan sistem denda keterlambatan pengembalian buku.
Denda dihitung Rp 1.000 per hari untuk 7 hari pertama, dan Rp 2.000 per hari setelahnya.
Mahasiswa dengan status 'VIP' mendapat keringanan 50%. 
Buatlah program untuk menghitung denda..."

CONTOH YANG SALAH (BUKAN SOAL CERITA):
❌ "Buatlah program untuk menentukan bilangan genap atau ganjil"
❌ "Buatlah program untuk menentukan status umur seseorang"
❌ "Buatlah program yang menerima input dan menampilkan output"

ATURAN OUTPUT:
- LANGSUNG mulai dengan **SOAL:** tanpa pengantar
- Output HANYA 4 section: **SOAL:**, **REQUIREMENTS:**, **EXPECTED OUTPUT:**, **KUNCI JAWABAN:**
- Soal HARUS berbentuk cerita dengan tokoh dan situasi nyata

ATURAN KONTEN:
- WAJIB ada nama tokoh/tempat dalam soal (Pak Budi, Toko ABC, Rumah Sakit X, dll)
- WAJIB ada konteks situasi yang jelas
- Kode jawaban minimal 25-40 baris dengan logika kompleks

**BAHASA:** {language}
**OUTPUT:** {output_type}

**FORMAT:**
**SOAL:**
[Judul Menarik]

[CERITA: Nama tokoh + tempat + situasi + kondisi bisnis/logika]
[Lalu perintah untuk membuat program]

**REQUIREMENTS:**
1. [Requirement berdasarkan cerita]
...

**EXPECTED OUTPUT:**
[Contoh interaksi lengkap]

**KUNCI JAWABAN:**
```{language.lower()}
[Kode lengkap]
```"""
    }

    # Normalisasi difficulty
    difficulty_level = difficulty.lower() if difficulty else "sedang"
    print(f"[DEBUG] Difficulty: {difficulty_level}")
    
    # Generate curriculum context
    curriculum_context = get_curriculum_context(subject_name, topic)
    if curriculum_context:
        print(f"[DEBUG] Curriculum context generated for: {topic}")
    
    user_instruction = f\"\"\"
=== PARAMETER WAJIB DIPERTIMBANGKAN ===

📚 MATA KULIAH: {subject_name}
📝 TOPIK UTAMA: {topic}
🎯 TINGKAT KESULITAN: {difficulty.upper()}
💻 BAHASA: {language}

{curriculum_context}

=== INSTRUKSI GENERATE SOAL CERITA ===

**LANGKAH 1: ANALISIS MODUL**
Baca SELURUH konteks modul dan identifikasi SEMUA konsep yang tersedia.

**LANGKAH 2: BUAT SKENARIO SESUAI TINGKAT KESULITAN**

🎯 TOPIK: {topic}
🎯 DIFFICULTY: {difficulty.upper()}

⚡ PANDUAN TINGKAT KESULITAN - WAJIB DIIKUTI DENGAN KETAT!

📗 MUDAH:
- Cakupan: HANYA 1 konsep dasar dari modul
- Jika topik looping: gunakan HANYA for ATAU HANYA while (pilih satu)
- Jika topik conditional: gunakan HANYA if-else sederhana
- 2 kondisi, 1-2 input, kode 10-15 baris

📙 SEDANG:
- Cakupan: 2-3 konsep dari modul
- Jika topik looping: kombinasi for DAN while (2 jenis loop)
- Jika topik conditional: if-elif-else dengan beberapa cabang
- 3-4 kondisi, 2-3 input, kode 20-30 baris

📕 SULIT - WAJIB MENCAKUP SELURUH KONSEP DARI MODUL:
- Cakupan: SEMUA konsep yang ada di konteks modul WAJIB digunakan
- Jika topik looping: WAJIB ada for, while, nested loop, break, continue (SEMUA!)
- Jika topik conditional: WAJIB ada if, elif, else, nested if, operator logika (SEMUA!)
- 5+ kondisi dengan nested logic
- 4+ input berbeda
- Kode MINIMAL 40-60 baris
- WAJIB mengintegrasikan SELURUH variasi sintaks yang diajarkan di modul

**LANGKAH 3: TULIS SOAL CERITA**
- Ada tokoh dan tempat (Pak Budi, Toko X, dll)
- Deskripsi skenario yang DETAIL
- Requirements yang SPESIFIK
- Expected output dengan BANYAK KASUS TEST

**CONTOH BATASAN:**

ERROR: SALAH - Jika modul hanya tentang "Data Types & Operators":
```python
def hitung_luas(p, l):  # ← SALAH! Function tidak diajarkan
    try:                # ← SALAH! Try-except tidak diajarkan
        return p * l
    except:
        print("Error")
```

✅ BENAR - Jika modul hanya tentang "Data Types & Operators":
```python
panjang = float(input("Panjang: "))
lebar = float(input("Lebar: "))
luas = panjang * lebar  # Hanya operator yang diajarkan
print("Luas:", luas)
```
"""

    if custom_notes and custom_notes.strip():
        user_instruction += f"""
=== 🚨 CATATAN KHUSUS DARI USER - WAJIB DIIKUTI! 🚨 ===

"{custom_notes.strip()}"

⚠️ INSTRUKSI DI ATAS ADALAH PERINTAH LANGSUNG!
- Soal yang dibuat HARUS mengikuti catatan ini
- Jika catatan menyebutkan topik spesifik, fokus pada topik tersebut
- Jika catatan menyebutkan format tertentu, ikuti format tersebut
- PRIORITAS: Catatan user > Isi modul umum
"""

    user_instruction += f"""
=== ISI MODUL (SUMBER TUNGGAL - PALING PENTING!) ===
{context_text}

CRITICAL: INSTRUKSI ANALISIS:
1. ABAIKAN topik yang diminta jika TIDAK ADA di modul
2. Baca SELURUH konteks modul di atas
3. List konsep/sintaks yang EKSPLISIT disebutkan DI MODUL
4. Buat soal yang HANYA menggunakan list tersebut
5. JANGAN menambahkan konsep lain yang tidak ada di modul
6. Soal HARUS berdasarkan ISI MODUL, bukan topik yang diminta user

WARNING: Jika modul tentang Conditional Statement tapi user minta MVC, buat soal tentang Conditional Statement!

=== FORMAT OUTPUT ===

**SOAL:**
[Judul Sederhana]

Buatlah program {language} sederhana yang [deskripsi task menggunakan HANYA konsep dari modul].

Contoh: "Buatlah program untuk menghitung luas persegi panjang menggunakan input, konversi tipe data, dan operator perkalian."

JANGAN: "Buatlah program dengan function untuk menghitung luas..."

**REQUIREMENTS:**
1. [Requirement sesuai materi modul]
2. [Requirement sesuai materi modul]
3. [Requirement sesuai materi modul]
4. [Requirement sesuai materi modul]
5. [Requirement sesuai materi modul]

WARNING: Requirements HARUS tentang konsep yang ADA di modul

**EXPECTED OUTPUT:**
```
[Contoh output program sesuai {output_type}]
```

**KUNCI JAWABAN:**
```{language.lower()}
# Kode sederhana tanpa function/class/try-except
# (kecuali konsep tersebut ADA di modul)
# Gunakan kode linear/sequential
# Sesuai dengan style contoh di modul

[kode di sini]
```

⚠️ KEBEBASAN METODE - SANGAT PENTING!
- JANGAN mendikte metode/tools SPESIFIK yang harus digunakan
- SALAH: "Gunakan dictionary untuk menyimpan data" atau "Harus menggunakan nested loop"
- BENAR: "Simpan data produk" atau "Proses data dengan pengulangan yang sesuai"
- Biarkan praktikan MEMILIH SENDIRI pendekatan solusi mereka
- Ini melatih kreativitas dan pemahaman, bukan sekadar mengikuti instruksi
- Di sesi asistensi, aslab bisa menanyakan ALASAN pemilihan tools tersebut

PENTING: 
- JANGAN tambahkan penjelasan atau klarifikasi apapun di awal
- JANGAN tambahkan checklist atau FINAL CHECK
- Langsung mulai dengan **SOAL:**
- Output HANYA berisi 4 section: SOAL, REQUIREMENTS, EXPECTED OUTPUT, KUNCI JAWABAN
"""

    # Tambahkan instruksi khusus untuk difficulty SULIT
    if difficulty_level == "sulit":
        user_instruction += f"""

=== 🔴 INSTRUKSI WAJIB UNTUK DIFFICULTY SULIT 🔴 ===

ANDA HARUS menggunakan SEMUA konsep yang ada di konteks modul!

LANGKAH WAJIB:
1. Baca SELURUH konteks modul yang diberikan di atas
2. Identifikasi SETIAP sintaks dan konsep yang disebutkan
3. Soal HARUS mengintegrasikan SEMUA konsep tersebut dalam SATU program

CONTOH UNTUK MODUL LOOPING dengan difficulty SULIT:
- WAJIB ada for loop untuk iterasi data/menu
- WAJIB ada while loop untuk validasi input atau kondisi tertentu  
- WAJIB ada nested loop (loop di dalam loop) untuk proses kompleks
- WAJIB ada break untuk keluar dari loop pada kondisi tertentu
- WAJIB ada continue untuk melewati iterasi pada kondisi tertentu

CONTOH SKENARIO YANG BENAR UNTUK LOOPING SULIT:
"Sistem kasir minimarket yang menggunakan:
 - while True untuk menu utama yang terus berulang
 - for loop untuk menampilkan daftar produk
 - nested for untuk menghitung sub-total per kategori
 - break untuk keluar saat user pilih 'Selesai'
 - continue untuk melewati produk yang stoknya habis"

⚠️ JANGAN buat soal yang hanya menggunakan sebagian konsep!
⚠️ Jika konteks modul memiliki 5 konsep, soal WAJIB menggunakan 5 konsep tersebut!
"""

    # Tambahkan reminder catatan di akhir jika ada
    if custom_notes and custom_notes.strip():
        user_instruction += f"""

🔔 REMINDER FINAL: Jangan lupa catatan user: "{custom_notes.strip()}"
Pastikan soal sudah SESUAI dengan catatan tersebut!
"""

    user_message = {"role": "user", "content": user_instruction}
    messages = [system_message, user_message]

    total_len = len(system_message["content"]) + len(user_message["content"])
    print(f"\n[DEBUG] Panjang prompt: {total_len} karakter (~{total_len // 4} tokens)")
    if total_len < 100:
        raise ValueError(f"Prompt terlalu pendek ({total_len} karakter)!")

    print(f"\n[DEBUG] Memanggil LLM untuk {language}...")
    llm_start_time = time.time()

    try:
        result = call_openrouter(messages)
        execution_time_ms = int((time.time() - llm_start_time) * 1000)

        if not result or not result.strip():
            raise Exception("LLM mengembalikan response kosong.")

        print(f"\n[DEBUG] Response: {len(result)} karakter")
        print(f"Preview: {result[:150]}...")

        required_tags = ["**SOAL:", "**REQUIREMENTS:", "**EXPECTED OUTPUT:", "**KUNCI JAWABAN:"]
        missing = [t for t in required_tags if t not in result]

        if missing:
            print(f"⚠️ Tag tidak lengkap: {', '.join(missing)}")
        else:
            print("✓ Semua tag yang diperlukan ada")

        return result

    except Exception as e:
        raise e