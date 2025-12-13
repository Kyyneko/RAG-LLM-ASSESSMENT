# API Documentation for RAG + LLM Assessment Generation

## Base URL
```
http://localhost:5000/api/rag
```

## Available Endpoints

### 1. Generate Assessment (Main Endpoint)
**POST** `/api/rag/generate`

Menerima input dari FE dan menghasilkan soal praktikum menggunakan RAG + LLM.

#### Request Body (Direct Mode - Recommended for FE):
```json
{
  "subject_id": 1,           // Required
  "module_id": 1,            // Required
  "assistant_id": 1,         // Required
  "tingkat_kesulitan": "Sedang", // Optional: "Mudah", "Sedang", "Sukar"
  "notes": "Catatan tambahan",     // Optional
  "session_id": 1,          // Optional - auto-filled dari module jika tidak ada
  "mode": "preview"         // Optional: "normal" (default) atau "preview"
}
```

#### Response Format (Normal Mode):
```json
{
  "status": "success",
  "mode": "normal",
  "message": "Assessment berhasil dibuat.",
  "action": "create",                    // "create" atau "replace"
  "task_id": 123,                        // ID assessment yang dibuat
  "parameters": {
    "subject_id": 1,
    "subject_name": "Pemrograman Lanjut",
    "module_title": "Array dan Looping",
    "tingkat_kesulitan": "Sedang"
  },
  "processing_time_seconds": 15.23
}
```

#### Response Format (Preview Mode):
```json
{
  "status": "success",
  "mode": "preview",
  "message": "Assessment preview berhasil dibuat.",
  "preview": {
    "sections": {
      "soal": "Buat program untuk menghitung rata-rata nilai array...",
      "requirements": "- Menggunakan loop for\n- Input: array of numbers\n- Output: rata-rata",
      "expected_output": "Program menampilkan rata-rata dari angka-angka dalam array",
      "kunci_jawaban": "def hitung_rata_rata(arr):\n    return sum(arr) / len(arr)",
      "notes": "Pastikan menangani array kosong"
    },
    "raw_output": "#SOAL\nBuat program...\n\n#REQUIREMENTS\n- Menggunakan loop...",
    "metadata": {
      "subject_id": 1,
      "session_id": 1,
      "assistant_id": 1,
      "topic": "Array dan Looping",
      "class_name": "Kelas A",
      "subject_name": "Pemrograman Lanjut",
      "context_count": 5,
      "generated_at": "2024-01-01T10:00:00",
      "model": "google/gemini-2.0-flash-exp:free",
      "custom_notes": "Tingkat kesulitan: Sedang"
    },
    "estimated_time": "60-90 menit"
  },
  "parameters": {
    "subject_id": 1,
    "subject_name": "Pemrograman Lanjut",
    "module_title": "Array dan Looping",
    "tingkat_kesulitan": "Sedang"
  },
  "processing_time_seconds": 12.45
}
```

#### Error Responses:
- **400 Bad Request**: Field required tidak diisi
- **404 Not Found**: Subject/module tidak ditemukan
- **409 Conflict**: Assessment sudah di-apply, tidak bisa regenerate
- **500 Internal Server Error**: Error system

### 2. Save Approved Assessment
**POST** `/api/rag/save-assessment`

Menyimpan assessment yang sudah di-approve dari preview mode ke database.

#### Request Body:
```json
{
  "subject_id": 1,              // Required
  "session_id": 1,              // Optional
  "assistant_id": 1,            // Required
  "title": "Judul Assessment",  // Optional
  "assessment_data": {          // Required - data dari preview response
    "sections": {
      "soal": "konten soal...",
      "requirements": "requirements...",
      "expected_output": "expected output...",
      "kunci_jawaban": "kunci jawaban...",
      "notes": "notes..."
    },
    "metadata": {
      "subject_id": 1,
      "session_id": 1,
      "assistant_id": 1,
      "topic": "Array dan Looping",
      "class_name": "Kelas A",
      "subject_name": "Pemrograman Lanjut",
      "context_count": 5,
      "generated_at": "2024-01-01T10:00:00",
      "model": "google/gemini-2.0-flash-exp:free",
      "custom_notes": "Tingkat kesulitan: Sedang"
    },
    "estimated_time": "60-90 menit"
  }
}
```

#### Response:
```json
{
  "status": "success",
  "message": "Assessment berhasil disimpan.",
  "task_id": 124,                // ID assessment yang tersimpan
  "title": "Judul Assessment",
  "estimated_time": "60-90 menit"
}
```

### 3. Get All Subjects
**GET** `/api/rag/subjects`

Mendapatkan daftar semua mata kuliah untuk dropdown.

#### Response:
```json
{
  "status": "success",
  "total_records": 5,
  "subjects": [
    {
      "id": 1,
      "subject": "Pemrograman Lanjut",
      "description": "Pemrograman dengan Python",
      "created_at": "2024-01-01T10:00:00"
    }
  ]
}
```

### 3. Get Modules by Subject
**GET** `/api/rag/subjects/{subject_id}/modules`

Mendapatkan daftar modul untuk subject tertentu.

#### Response:
```json
{
  "status": "success",
  "subject_id": 1,
  "total_records": 3,
  "modules": [
    {
      "id": 1,
      "title": "Introduction to Python",
      "session_id": 1,
      "session_topic": "Pengenalan Python",
      "created_at": "2024-01-01T10:00:00"
    }
  ]
}
```

### 4. Get Assessment by Task ID
**GET** `/api/rag/task/{task_id}`

Mendapatkan detail assessment yang sudah di-generate.

#### Response:
```json
{
  "status": "success",
  "assessment": {
    "id": 123,
    "title": "Assessment: Array dan Looping",
    "description": "Soal praktikum tentang...",
    "questions": [
      {
        "question": "Buat program untuk...",
        "expected_answer": "Program harus mengandung...",
        "points": 20
      }
    ],
    "generation_status": "draft",
    "created_at": "2024-01-01T10:00:00"
  }
}
```

### 5. Update Task Status
**PATCH** `/api/rag/task/{task_id}/status`

Update status assessment (none/generating/draft/applied).

#### Request Body:
```json
{
  "status": "applied",      // "none", "generating", "draft", "applied"
  "assistant_id": 1
}
```

### 6. Upload Module File
**POST** `/api/rag/upload-module`

Upload file modul baru (PDF, DOCX, TXT).

#### Form Data:
- `file`: File yang diupload
- `session_id`: ID session
- `title`: Judul modul
- `assistant_id`: ID assistant

### 7. Get Generation History
**GET** `/api/rag/generation-history/{subject_id}`

Mendapatkan riwayat generate assessment untuk subject tertentu.

## Integration Flow untuk FE

### 1. Load Data for Dropdown
```javascript
// Load subjects
const subjects = await fetch('/api/rag/subjects').then(r => r.json());

// When subject selected, load modules
const modules = await fetch(`/api/rag/subjects/${subjectId}/modules`).then(r => r.json());
```

### 2. Generate Assessment (Preview Mode - Recommended)
```javascript
// Generate untuk preview
const generatePreview = async (data) => {
  const response = await fetch('/api/rag/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      subject_id: data.subjectId,
      module_id: data.moduleId,
      assistant_id: data.assistantId,
      tingkat_kesulitan: data.level || 'Sedang',
      notes: data.notes || '',
      mode: 'preview'  // Tambahkan mode preview
    })
  });

  const result = await response.json();

  if (result.status === 'success' && result.mode === 'preview') {
    // Tampilkan preview di UI
    displayAssessmentPreview(result.preview);
    return result.preview;
  }

  throw new Error(result.error || 'Failed to generate preview');
};

// Save assessment yang sudah di-approve
const saveAssessment = async (previewData, title) => {
  const response = await fetch('/api/rag/save-assessment', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      subject_id: previewData.metadata.subject_id,
      session_id: previewData.metadata.session_id,
      assistant_id: previewData.metadata.assistant_id,
      title: title,
      assessment_data: previewData
    })
  });

  return response.json();
};
```

### 3. Generate Assessment (Normal Mode - Direct Save)
```javascript
const generateAndSave = async (data) => {
  const response = await fetch('/api/rag/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      subject_id: data.subjectId,
      module_id: data.moduleId,
      assistant_id: data.assistantId,
      tingkat_kesulitan: data.level || 'Sedang',
      notes: data.notes || ''
      // mode: 'normal' (default)
    })
  });

  const result = await response.json();

  if (result.status === 'success') {
    console.log('Assessment saved with task_id:', result.task_id);
    return result;
  }

  throw new Error(result.error || 'Failed to generate assessment');
};
```

### 4. Get Generated Assessment
```javascript
const getAssessment = async (taskId) => {
  const response = await fetch(`/api/rag/task/${taskId}`);
  return response.json();
};
```

### 5. Preview UI Components Example
```javascript
// Display preview dengan sections terpisah
const displayAssessmentPreview = (preview) => {
  const { sections, estimated_time, metadata } = preview;

  document.getElementById('soal-content').innerHTML = formatText(sections.soal);
  document.getElementById('requirements-content').innerHTML = formatText(sections.requirements);
  document.getElementById('expected-output-content').innerHTML = formatText(sections.expected_output);
  document.getElementById('kunci-jawaban-content').innerHTML = formatText(sections.kunci_jawaban);
  document.getElementById('notes-content').innerHTML = formatText(sections.notes);

  document.getElementById('estimated-time').textContent = estimated_time;
  document.getElementById('generation-info').textContent =
    `Generated: ${new Date(metadata.generated_at).toLocaleString()} | Model: ${metadata.model}`;

  // Show approve/reject buttons
  document.getElementById('preview-actions').style.display = 'block';
};

// Handle approve action
const handleApprove = async () => {
  const title = document.getElementById('assessment-title').value;
  const previewData = window.currentPreviewData; // Store current preview

  try {
    const result = await saveAssessment(previewData, title);
    alert(`Assessment berhasil disimpan dengan ID: ${result.task_id}`);

    // Redirect atau refresh list
    window.location.href = '/assessments';
  } catch (error) {
    alert('Gagal menyimpan: ' + error.message);
  }
};
```

## Business Logic

### Assessment Status Flow:
1. **none** → **generating** → **draft** → **applied**
2. Jika status sudah **applied**, tidak bisa regenerate (error 409)
3. Jika status **draft** atau **none**, bisa replace dengan generate baru

### Level Options:
- `"Mudah"` - Soal dasar
- `"Sedang"` - Soal menengah (default)
- `"Sukar"` - Soal challenging

## Error Handling

Selalu cek:
1. `status` field dalam response
2. HTTP status code
3. `error` field jika ada

Example error handling:
```javascript
try {
  const result = await generateAssessment(data);
  if (result.status === 'success') {
    // Handle success
    console.log('Task ID:', result.task_id);
  }
} catch (error) {
  if (error.response.status === 409) {
    alert('Assessment sudah di-apply, tidak bisa regenerate');
  } else {
    alert('Error: ' + error.response.data.error);
  }
}
```