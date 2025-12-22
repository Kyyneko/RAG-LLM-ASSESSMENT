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
    class_name: str,
    context_snippets: list,
    module_names: list[str] = None,
    custom_notes: str = None,
    assessment_task_id: int = None,
    generation_type: str = "assessment",
    generated_by: int = None,
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
        class_name (str): Nama kelas
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
    print(f"[DEBUG] Kelas   : {class_name}")
    print(f"[DEBUG] Konteks : {len(context_snippets) if context_snippets else 0}")
    if custom_notes:
        print(f"[DEBUG] Catatan khusus: {custom_notes[:100]}...")

    if not subject_name.strip():
        raise ValueError("subject_name tidak boleh kosong!")
    if not topic.strip():
        raise ValueError("topic tidak boleh kosong!")
    if not class_name.strip():
        raise ValueError("class_name tidak boleh kosong!")

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

    user_instruction = f"""
=== PARAMETER WAJIB DIPERTIMBANGKAN ===

📚 MATA KULIAH: {subject_name}
📝 TOPIK UTAMA: {topic}
🎯 TINGKAT KESULITAN: Sesuaikan kompleksitas soal dengan topik yang diminta
👥 KELAS: {class_name}
💻 BAHASA: {language}

=== INSTRUKSI GENERATE SOAL CERITA ===

**LANGKAH 1: ANALISIS MODUL**
Baca konteks modul dan identifikasi konsep yang bisa dikombinasikan.

**LANGKAH 2: BUAT SKENARIO SESUAI TINGKAT KESULITAN**

🎯 TOPIK: {topic}

⚡ TINGKAT KESULITAN - SANGAT PENTING! IKUTI DENGAN KETAT!

📗 MUDAH:
- 2 kondisi saja (if-else sederhana)
- 1 input
- Kode 10-15 baris
- Contoh: Cek positif/negatif, genap/ganjil

📙 SEDANG:
- 3-4 kondisi (if-elif-else)
- 2-3 input
- Kode 20-30 baris
- Contoh: Kategori nilai (A/B/C/D/E), kategori BMI

📕 SULIT - HARUS KOMPLEKS!:
- 5+ kondisi dengan NESTED IF (if didalam if)
- 4+ input berbeda
- Kode MINIMAL 40-60 baris
- WAJIB ada: nested conditions, multiple calculations, validasi input
- Contoh skenario SULIT:
  "Rental mobil dengan tarif berbeda: weekday/weekend, durasi sewa, jenis mobil, member/non-member, asuransi"
  "Gaji karyawan dengan tunjangan: jabatan, masa kerja, lembur, potongan pajak bertingkat"

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

PENTING: 
- JANGAN tambahkan penjelasan atau klarifikasi apapun di awal
- JANGAN tambahkan checklist atau FINAL CHECK
- Langsung mulai dengan **SOAL:**
- Output HANYA berisi 4 section: SOAL, REQUIREMENTS, EXPECTED OUTPUT, KUNCI JAWABAN
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