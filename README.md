# RAG-LLM Assessment Generator

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Academic-yellow.svg)](LICENSE)

Sistem **Retrieval-Augmented Generation (RAG)** untuk otomatis generate soal praktikum laboratorium SI-LAB. Sistem ini mengekstrak pengetahuan dari modul praktikum (PDF, DOCX, TXT) dan menghasilkan soal cerita terstruktur menggunakan LLM.

---

## Daftar Isi

- [Gambaran Umum](#gambaran-umum)
- [Fitur Utama](#fitur-utama)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Teknologi yang Digunakan](#teknologi-yang-digunakan)
- [Struktur Direktori](#struktur-direktori)
- [Instalasi](#instalasi)
- [Konfigurasi](#konfigurasi)
- [Penggunaan API](#penggunaan-api)
- [RAG Pipeline](#rag-pipeline)
- [Konfigurasi Mata Kuliah](#konfigurasi-mata-kuliah)
- [Tingkat Kesulitan](#tingkat-kesulitan)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## Gambaran Umum

Proyek ini adalah backend API yang mengotomatisasi pembuatan soal assessment praktikum pemrograman. Sistem membaca dokumen modul, melakukan indexing dengan semantic embedding, lalu menghasilkan soal praktikum yang disesuaikan dengan materi yang telah diajarkan.

### Masalah yang Diselesaikan

- Mengurangi effort manual dalam pembuatan soal praktikum
- Menjamin konsistensi antara materi yang diajarkan dengan soal yang dihasilkan
- Memastikan soal hanya menggunakan konsep yang sudah diajarkan (curriculum-aware)
- Menghasilkan soal dengan format standar dan terstruktur

---

## Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| **Multi-format Document Processing** | Mendukung PDF, DOCX, dan TXT |
| **Semantic Chunking** | Memecah dokumen dengan mempertimbangkan struktur konteks |
| **Vector Store Caching** | Menyimpan index FAISS di disk untuk retrieval cepat |
| **Two-stage Retrieval** | FAISS search + CrossEncoder reranking |
| **Curriculum-Aware Generation** | Memastikan soal hanya menggunakan materi yang sudah diajarkan |
| **Multi-Subject Support** | Python, HTML/CSS/JS/PHP, SQL, Java, Android |
| **Story-Based Questions** | Menghasilkan soal dengan narasi tokoh dan situasi nyata |
| **Difficulty Levels** | Mudah, Sedang, Sulit dengan cakupan materi berbeda |
| **Preview Mode** | Generate tanpa langsung menyimpan ke database |

---

## Arsitektur Sistem

```
+-------------------+     +------------------+     +------------------+
|   Document Upload | --> |  Text Extraction | --> | Semantic Chunking|
+-------------------+     +------------------+     +------------------+
                                                             |
                                                             v
+-------------------+     +------------------+     +------------------+
|  Assessment Output | <--- |    LLM Generator | <--- | Vector Embedding|
+-------------------+     +------------------+     +------------------+
                                   ^                          |
                                   |                          v
                            +------------------+     +------------------+
                            | Prompt Engineering|     |   FAISS + Rerank |
                            +------------------+     +------------------+
```

### Alur Kerja

1. **Document Processing**: Ekstraksi teks dari PDF/DOCX/TXT
2. **Semantic Chunking**: Memecah dokumen menjadi potongan berkonteks
3. **Embedding**: Konversi chunks menjadi vector embeddings (384 dim)
4. **Vector Storage**: Menyimpan embeddings di FAISS dengan metadata
5. **Context Retrieval**: Mencari konteks relevan dengan query
6. **Prompt Engineering**: Membuat prompt dengan curriculum context
7. **LLM Generation**: Menghasilkan soal via OpenRouter API
8. **Output Formatting**: Parsing response menjadi struktur terstandar

---

## Teknologi yang Digunakan

### Backend Framework
- **Flask 3.0+** - Web framework
- **Gunicorn** - WSGI HTTP Server (production)

### Database
- **MySQL 8.0+** - Database utama (subject, module, assessment_task)
- **PyMySQL** - MySQL connector

### Machine Learning & Embedding
- **sentence-transformers** - Text embeddings (`all-MiniLM-L6-v2`, 384 dim)
- **FAISS-cpu** - Vector similarity search
- **transformers** - CrossEncoder reranking (`ms-marco-MiniLM-L-6-v2`)
- **torch (CPU-only)** - PyTorch backend

### Document Processing
- **pypdf** - PDF text extraction
- **python-docx** - DOCX text extraction

### LLM Integration
- **OpenRouter API** - Gateway ke berbagai model LLM
- **Default Model**: Google Gemma 3 27B Instruct (free tier)

---

## Struktur Direktori

```
RAG-LLM-ASSESSMENT/
├── main.py                 # Entry point Flask application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker image configuration
├── docker-compose.yml     # Docker orchestration
├── .env.example           # Environment variables template
├── API_Documentation.md   # API documentation lengkap
│
├── data/                  # Data directory
│   └── vectorstore/       # Cached FAISS indices per module
│
├── assessment/            # Assessment generation logic
│   ├── __init__.py
│   └── generator.py       # Parse & format LLM output
│
├── db/                    # Database connection
│   ├── __init__.py
│   └── connection.py      # MySQL connection manager
│
├── llm/                   # LLM integration
│   ├── __init__.py
│   ├── client.py          # OpenRouter API client
│   └── generator.py       # Prompt engineering & subject configs
│
├── rag/                   # RAG pipeline components
│   ├── __init__.py
│   ├── extractor.py       # PDF/DOCX/TXT text extraction
│   ├── chunker.py         # Semantic text chunking
│   ├── embedder.py        # Sentence embeddings (MiniLM-L6-v2)
│   ├── vectorstore.py     # FAISS wrapper with metadata
│   ├── retriever.py       # Context retrieval + reranking
│   └── pipeline.py        # End-to-end RAG orchestration
│
└── routes/                # API endpoints
    ├── __init__.py
    └── rag_routes.py      # /api/rag/* endpoints
```

---

## Instalasi

### Prasyarat

- Python 3.11+
- MySQL 8.0+
- Docker & Docker Compose (opsional)
- OpenRouter API Key

### Setup Lokal

1. **Clone repository**
```bash
git clone <repository-url>
cd RAG-LLM-ASSESSMENT
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Konfigurasi environment**
```bash
cp .env.example .env
```

Edit file `.env` dan isi:
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=silab_db
OPENROUTER_API_KEY=your-openrouter-api-key
LLM_MODEL=google/gemma-3-27b-it:free
HUGGINGFACE_HUB_TOKEN=your-hf-token  # opsional
```

4. **Setup database**

Pastikan database dan tabel yang dibutuhkan sudah ada:
- `subject` - Data mata kuliah
- `module` - Data modul praktikum
- `session` - Sesi kuliah
- `class` - Data kelas
- `session_module` - Relasi session-modul

5. **Jalankan aplikasi**
```bash
# Development
python main.py

# Production dengan Gunicorn
gunicorn -w 2 -b 0.0.0.0:5002 --timeout 300 main:create_app
```

Server akan berjalan di `http://localhost:5002`

### Setup dengan Docker

```bash
docker-compose up -d
```

---

## Konfigurasi

### Environment Variables

```bash
# Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=silab_db

# LLM API
OPENROUTER_API_KEY=your-key-here
LLM_MODEL=google/gemma-3-27b-it:free

# Hugging Face (optional)
HUGGINGFACE_HUB_TOKEN=your-hf-token

# Application
UPLOAD_FOLDER=upload/
MAX_FILE_SIZE_MB=50
LOG_LEVEL=INFO
```

---

## Penggunaan API

### Base URL
```
http://localhost:5002/api/rag
```

### Generate Assessment

**POST** `/api/rag/generate`

Generate soal assessment berdasarkan modul dan tingkat kesulitan.

**Request Body:**
```json
{
  "subject_id": 1,
  "module_id": 1,
  "assistant_id": 1,
  "tingkat_kesulitan": "Sedang",
  "notes": "Catatan opsional"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Assessment berhasil digenerate.",
  "assessment": {
    "sections": {
      "soal": "Buatlah program...",
      "requirements": "1. ...\n2. ...",
      "expected_output": "...",
      "kunci_jawaban": "..."
    },
    "metadata": {
      "subject_id": 1,
      "topic": "Array dan Looping",
      "generated_at": "2024-01-01T10:00:00",
      "model": "google/gemma-3-27b-it:free"
    },
    "estimated_time": "60-90 menit"
  },
  "parameters": {
    "subject_id": 1,
    "subject_name": "Algoritma dan Pemrograman",
    "module_title": "Looping",
    "tingkat_kesulitan": "Sedang"
  },
  "processing_time_seconds": 12.45
}
```

### Get All Subjects

**GET** `/api/rag/subjects`

Mendapatkan daftar mata kuliah untuk dropdown.

**Response:**
```json
{
  "status": "success",
  "total_records": 5,
  "subjects": [
    {
      "id": 1,
      "name": "Algoritma dan Pemrograman",
      "description": "Pemrograman dengan Python",
      "created_at": "2024-01-01T10:00:00"
    }
  ]
}
```

### Get Modules by Subject

**GET** `/api/rag/subjects/{subject_id}/modules`

Mendapatkan daftar modul untuk mata kuliah tertentu.

**Response:**
```json
{
  "status": "success",
  "subject_id": 1,
  "total_records": 8,
  "modules": [
    {
      "id": 1,
      "title": "Data Types, Collection & Operator",
      "file_name": "modul_1.pdf",
      "uploaded_at": "2024-01-01T10:00:00"
    }
  ]
}
```

Untuk dokumentasi API lengkap, lihat [API_Documentation.md](API_Documentation.md)

---

## RAG Pipeline

### 1. Text Extraction ([rag/extractor.py](rag/extractor.py))

Mengekstrak teks dari berbagai format dokumen:
- **PDF**: Menggunakan `pypdf`
- **DOCX**: Menggunakan `python-docx`
- **TXT**: Direct file read

### 2. Semantic Chunking ([rag/chunker.py](rag/chunker.py))

Memecah dokumen menjadi potongan yang berhubungan:
- Max chunk size: 1000-1500 karakter
- Overlap: 200-300 karakter
- Memisah berdasarkan paragraf dan kalimat

### 3. Embedding ([rag/embedder.py](rag/embedder.py))

Konversi teks menjadi vector embeddings:
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Dimension: 384
- Bahasa: Multi-lingual (dukungan Indonesia)

### 4. Vector Store ([rag/vectorstore.py](rag/vectorstore.py))

Penyimpanan dan pencarian vector:
- Backend: FAISS IndexFlatIP (inner product)
- Metadata: source, file_path, chunk_index, subject_id
- Caching: Disk persistence per module (`data/vectorstore/module_{id}.faiss`)

### 5. Retrieval with Reranking ([rag/retriever.py](rag/retriever.py))

Two-stage retrieval untuk presisi tinggi:
- **Stage 1**: FAISS search (top-k dari initial_k)
- **Stage 2**: CrossEncoder reranking
- Model: `ms-marco-MiniLM-L-6-v2`

---

## Konfigurasi Mata Kuliah

Sistem mendukung beberapa mata kuliah dengan konfigurasi berbeda. Konfigurasi didefinisikan di [llm/generator.py](llm/generator.py):

| Mata Kuliah | Bahasa | Konsep Utama |
|-------------|--------|--------------|
| **Algoritma dan Pemrograman** | Python | Function, loop, error handling, OOP |
| **Pemrograman Website** | HTML/CSS/JS/PHP | Frontend, backend, form, database |
| **Basis Data** | SQL | DDL, DML, query, join, subquery |
| **OOP JAVA** | Java | Class, inheritance, polymorphism |
| **Pemrograman Mobile** | Java (Android) | Activity, Fragment, RecyclerView |

### Subject Configuration

```python
SUBJECT_CONFIGS = {
    "Algoritma dan Pemrograman": {
        "language": "Python",
        "file_ext": "py",
        "concepts": "algoritma, struktur data, function, loop, error handling",
        "focus": "logika pemrograman dan problem solving",
        "typical_tasks": [...],
        "code_style": "procedural dengan fungsi-fungsi modular",
        "output_type": "console/terminal dengan input-output interaktif"
    },
    ...
}
```

---

## Tingkat Kesulitan

Sistem memiliki tiga tingkat kesulitan dengan cakupan materi berbeda:

### Mudah
- Cakupan: 1 konsep dasar dari modul
- 2 kondisi, 1-2 input
- Kode 10-15 baris
- Contoh: Jika topik looping, gunakan HANYA for ATAU while

### Sedang
- Cakupan: 2-3 konsep dari modul
- 3-4 kondisi, 2-3 input
- Kode 20-30 baris
- Contoh: Jika topik looping, kombinasi for DAN while

### Sulit
- Cakupan: SEMUA konsep dari modul
- 5+ kondisi dengan nested logic
- 4+ input berbeda
- Kode minimal 40-60 baris
- WAJIB mengintegrasikan SELURUH variasi sintaks yang diajarkan

---

## Curriculum Context

Fitur **curriculum-aware** memastikan soal yang dihasilkan hanya menggunakan konsep yang sudah diajarkan. Urutan kurikulum didefinisikan di [llm/generator.py](llm/generator.py):

```python
CURRICULUM_ORDER = {
    "Algoritma dan Pemrograman": [
        "Data Types", "Collection", "Operator", "Condition",
        "Looping", "Function", "Error Handling & RegEx", "OOP"
    ],
    "Basis Data": [
        "DDL", "Query Dasar", "DML", "Operator", "Relationship",
        "Join", "Function", "Grouping", "Subquery", ...
    ],
    ...
}
```

### Cara Kerja

1. Sistem mengidentifikasi posisi modul saat ini dalam kurikulum
2. Hanya konsep dari modul sebelumnya dan modul saat ini yang boleh digunakan
3. Konsep dari modul mendatang dilarang digunakan dalam soal

Contoh: Jika modul saat ini adalah "Looping", soal BOLEH menggunakan "Data Types", "Operator", "Condition" tetapi TIDAK BOLEH menggunakan "Function" atau "OOP".

---

## Format Output Assessment

LLM menghasilkan output terstruktur dengan 4 bagian:

```markdown
#SOAL
[Judul Menarik]

[CERITA: Nama tokoh + tempat + situasi + kondisi bisnis/logika]
[Lalu perintah untuk membuat program]

#REQUIREMENTS
1. [Requirement berdasarkan cerita]
2. [Requirement berdasarkan cerita]
...

#EXPECTED OUTPUT
[Contoh interaksi lengkap]

#KUNCI JAWABAN
```python
[Kode lengkap]
```
```

---

## Deployment

### Docker Production

1. **Build image**
```bash
docker build -t rag-llm-assessment .
```

2. **Run dengan docker-compose**
```bash
docker-compose up -d
```

3. **Check logs**
```bash
docker-compose logs -f rag-llm
```

### Health Check

```bash
curl http://localhost:5002/
```

Expected response:
```json
{
  "message": "SI-LAB RAG Assessment Generator API is running.",
  "version": "2.0",
  "endpoints": {...}
}
```

---

## Troubleshooting

### Vector Store Cache

Cache tersimpan di `data/vectorstore/module_{id}.faiss`. Untuk rebuild cache:

```bash
rm data/vectorstore/module_*
```

### LLM Timeout

Default timeout: 300 detik. Sesuaikan di [docker-compose.yml](docker-compose.yml):

```yaml
command: ["gunicorn", "--timeout", "300", ...]
```

### Empty Response

Jika LLM mengembalikan response kosong:
1. Cek API key di `.env`
2. Verifikasi model yang digunakan masih available
3. Cek rate limit OpenRouter

### Debug Mode

Untuk melihat log debug:

```bash
export LOG_LEVEL=DEBUG
python main.py
```

---

## Development

### Menambah Mata Kuliah Baru

Edit [llm/generator.py](llm/generator.py) dan tambahkan konfigurasi:

```python
SUBJECT_CONFIGS = {
    ...
    "Nama Mata Kuliah Baru": {
        "language": "Bahasa Pemrograman",
        "file_ext": "ext",
        "concepts": "konsep1, konsep2, ...",
        "focus": "fokus utama",
        "typical_tasks": [...],
        "code_style": "style",
        "output_type": "output"
    }
}

CURRICULUM_ORDER = {
    ...
    "Nama Mata Kuliah Baru": [
        "Modul 1", "Modul 2", ...
    ]
}
```

---

## License

Proyek ini adalah bagian dari Skripsi Mahasiswa - Universitas Hasanuddin

---

## Author

**Mahendra** - Skripsi Project

- GitHub: [@Kyyneko](https://github.com/Kyyneko)

---

<p align="center">
  Made with ❤️ for SI-LAB
</p>
