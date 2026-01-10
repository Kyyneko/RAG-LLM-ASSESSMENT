# API Documentation - RAG-LLM Assessment Generator

## Base URL
```
http://localhost:5002/api/rag
```

**Production URL:**
```
https://rag.silabunhas.cloud/api/rag
```

---

## Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate` | Generate soal praktikum dengan RAG + LLM |
| GET | `/subjects` | Daftar semua mata kuliah |
| GET | `/subjects/{subject_id}/modules` | Daftar modul untuk mata kuliah tertentu |

---

## 1. Generate Assessment

**POST** `/api/rag/generate`

Generate soal praktikum menggunakan RAG pipeline dan LLM. Endpoint ini **hanya mengembalikan response soal** (preview mode), tidak menyimpan ke database.

### Request Body

```json
{
  "subject_id": 1,
  "module_id": 1,
  "assistant_id": 1,
  "tingkat_kesulitan": "Sedang",
  "notes": "Catatan opsional"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subject_id` | integer | ✅ | ID mata kuliah |
| `module_id` | integer | ✅ | ID modul praktikum |
| `assistant_id` | integer | ✅ | ID asisten/user yang generate |
| `tingkat_kesulitan` | string | ❌ | `"Mudah"`, `"Sedang"` (default), atau `"Sulit"` |
| `notes` | string | ❌ | Catatan tambahan untuk customize soal |

### Success Response (200)

```json
{
  "status": "success",
  "message": "Assessment berhasil digenerate.",
  "assessment": {
    "sections": {
      "soal": "**Sistem Kasir Toko Elektronik**\n\nPak Budi memiliki toko elektronik...",
      "requirements": "1. Program menerima input nama pelanggan\n2. Program menghitung diskon...",
      "expected_output": "```\nNama: Andi\nTotal: Rp 1.500.000\nDiskon: 15%\nBayar: Rp 1.275.000\n```",
      "kunci_jawaban": "```python\nname = input('Nama: ')\ntotal = int(input('Total: '))\n...\n```"
    },
    "metadata": {
      "subject_id": 1,
      "topic": "Looping",
      "subject_name": "Algoritma dan Pemrograman",
      "context_count": 8,
      "generated_at": "2026-01-10T06:00:00",
      "model": "openai/gpt-oss-120b:free"
    },
    "estimated_time": "60-90 menit"
  },
  "parameters": {
    "subject_id": 1,
    "subject_name": "Algoritma dan Pemrograman",
    "module_id": 1,
    "module_title": "Looping",
    "tingkat_kesulitan": "Sedang"
  },
  "processing_time_seconds": 12.45
}
```

### Error Responses

**400 Bad Request** - Field wajib tidak lengkap
```json
{
  "error": "subject_id, module_id, dan assistant_id wajib diisi."
}
```

**404 Not Found** - Subject atau module tidak ditemukan
```json
{
  "error": "Subject dengan ID 999 tidak ditemukan.",
  "processing_time_seconds": 0.05
}
```

**404 Not Found** - Tidak ada konteks relevan
```json
{
  "error": "Tidak ada konteks relevan ditemukan.",
  "hint": "Pastikan modul berisi materi tentang topik ini.",
  "processing_time_seconds": 2.34
}
```

**500 Internal Server Error** - Error sistem
```json
{
  "status": "error",
  "error": "Terjadi kesalahan internal.",
  "error_type": "Exception",
  "details": "Error message details...",
  "processing_time_seconds": 5.67
}
```

---

## 2. Get All Subjects

**GET** `/api/rag/subjects`

Mengambil daftar semua mata kuliah yang aktif untuk dropdown/selector.

### Success Response (200)

```json
{
  "status": "success",
  "total_records": 5,
  "subjects": [
    {
      "id": 1,
      "name": "Algoritma dan Pemrograman",
      "description": "Pemrograman dasar dengan Python",
      "created_at": "2024-01-01T10:00:00"
    },
    {
      "id": 2,
      "name": "Basis Data",
      "description": "Database dan SQL",
      "created_at": "2024-01-01T10:00:00"
    },
    {
      "id": 3,
      "name": "OOP Java",
      "description": "Object Oriented Programming dengan Java",
      "created_at": "2024-01-01T10:00:00"
    },
    {
      "id": 4,
      "name": "Pemrograman Mobile",
      "description": "Pengembangan aplikasi Android",
      "created_at": "2024-01-01T10:00:00"
    },
    {
      "id": 5,
      "name": "Pemrograman Website",
      "description": "Web development dengan HTML/CSS/JS/PHP/Laravel",
      "created_at": "2024-01-01T10:00:00"
    }
  ]
}
```

---

## 3. Get Modules by Subject

**GET** `/api/rag/subjects/{subject_id}/modules`

Mengambil daftar modul praktikum untuk mata kuliah tertentu.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `subject_id` | integer | ID mata kuliah |

### Success Response (200)

```json
{
  "status": "success",
  "subject_id": 1,
  "total_records": 7,
  "modules": [
    {
      "id": 1,
      "title": "Data Types, Collection & Operator",
      "file_name": "Data Types, Collection & Operator.pdf",
      "uploaded_at": "2024-01-01T10:00:00"
    },
    {
      "id": 2,
      "title": "Condition",
      "file_name": "Bab 3 Condition.pdf",
      "uploaded_at": "2024-01-01T10:00:00"
    },
    {
      "id": 3,
      "title": "Looping",
      "file_name": "Bab 4 Looping.pdf",
      "uploaded_at": "2024-01-01T10:00:00"
    }
  ]
}
```

---

## Integration Example

### JavaScript/Fetch

```javascript
// 1. Load subjects untuk dropdown
async function loadSubjects() {
  const response = await fetch('/api/rag/subjects');
  const data = await response.json();
  return data.subjects;
}

// 2. Load modules berdasarkan subject yang dipilih
async function loadModules(subjectId) {
  const response = await fetch(`/api/rag/subjects/${subjectId}/modules`);
  const data = await response.json();
  return data.modules;
}

// 3. Generate assessment
async function generateAssessment(params) {
  const response = await fetch('/api/rag/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      subject_id: params.subjectId,
      module_id: params.moduleId,
      assistant_id: params.assistantId,
      tingkat_kesulitan: params.difficulty || 'Sedang',
      notes: params.notes || ''
    })
  });

  const result = await response.json();

  if (result.status === 'success') {
    console.log('Generated assessment:', result.assessment);
    return result.assessment;
  } else {
    throw new Error(result.error || 'Failed to generate');
  }
}
```

### Python/Requests

```python
import requests

BASE_URL = "https://rag.silabunhas.cloud/api/rag"

# Get subjects
subjects = requests.get(f"{BASE_URL}/subjects").json()
print(f"Total subjects: {subjects['total_records']}")

# Get modules for subject 1
modules = requests.get(f"{BASE_URL}/subjects/1/modules").json()
print(f"Total modules: {modules['total_records']}")

# Generate assessment
response = requests.post(f"{BASE_URL}/generate", json={
    "subject_id": 1,
    "module_id": 3,
    "assistant_id": 1,
    "tingkat_kesulitan": "Sedang",
    "notes": "Fokus pada nested loop"
})

result = response.json()
if result["status"] == "success":
    print("SOAL:", result["assessment"]["sections"]["soal"])
```

---

## Tingkat Kesulitan

| Level | Cakupan Materi | Kompleksitas |
|-------|----------------|--------------|
| **Mudah** | 1 konsep dasar | 2 kondisi, 1-2 input, 10-15 baris kode |
| **Sedang** | 2-3 konsep | 3-4 kondisi, 2-3 input, 20-30 baris kode |
| **Sulit** | Semua konsep modul | 5+ kondisi, nested logic, 40-60 baris kode |

---

## Notes

1. **Preview Only**: Endpoint `/generate` hanya mengembalikan preview soal, tidak menyimpan ke database. Penyimpanan ditangani oleh sistem SI-Lab terpisah.

2. **Vector Store Caching**: Sistem menggunakan cache FAISS untuk mempercepat retrieval. Cache disimpan di `data/vectorstore/module_{id}.faiss`.

3. **Rate Limiting**: OpenRouter API memiliki rate limit. Jika menerima error 429, tunggu beberapa detik sebelum retry.

4. **Timeout**: Default timeout adalah 300 detik untuk mengakomodasi LLM generation time.

---

## LLM Model

- **Provider**: OpenRouter API
- **Model**: `openai/gpt-oss-120b:free`
- **Max Tokens**: 8000
- **Temperature**: 0.7

---

*Last updated: 2026-01-10*