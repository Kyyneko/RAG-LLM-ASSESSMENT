# Panduan Evaluasi Skripsi RAG-LLM Assessment

## Desain Penelitian

### 1. Tujuan Evaluasi
Mengevaluasi kualitas assessment yang dihasilkan oleh sistem RAG-LLM dibandingkan dengan assessment manual yang dibuat oleh asisten lab.

### 2. Metodologi

```
┌─────────────────────────────────────────────────────────────┐
│                    DESAIN PENELITIAN                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐          ┌─────────────────┐          │
│  │  GRUP A (RAG)   │          │  GRUP B (Manual)│          │
│  │ 30 Assessment   │          │ 30 Assessment   │          │
│  │ dari sistem     │          │ dari aslab      │          │
│  └────────┬────────┘          └────────┬────────┘          │
│           │                            │                    │
│           └──────────┬─────────────────┘                    │
│                      ▼                                      │
│           ┌─────────────────┐                              │
│           │ 3 Expert Menilai│                              │
│           │ dengan Rubrik   │                              │
│           └────────┬────────┘                              │
│                    ▼                                        │
│           ┌─────────────────┐                              │
│           │ Analisis        │                              │
│           │ Statistik       │                              │
│           └─────────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

### 3. Sampel Penelitian

| Komponen | Jumlah | Keterangan |
|----------|--------|------------|
| Assessment RAG-LLM | 30 | Dihasilkan dari 6 modul × 5 variasi |
| Assessment Manual | 30 | Dari arsip tugas praktikum existing |
| Expert Evaluator | 3 | Dosen/Koordinator Lab |
| Mata Kuliah | 2-3 | Algoritma, Web, OOP |

### 4. Instrumen Evaluasi

1. **Rubrik Penilaian** (6 kriteria, skor 1-5)
   - Lihat: [EVALUATION_RUBRIC.md](./EVALUATION_RUBRIC.md)

2. **Form Rekapitulasi** (Excel/Google Form)

---

## Analisis Statistik

### 1. Inter-Rater Reliability

Gunakan **Fleiss' Kappa** atau **Cohen's Kappa** untuk mengukur konsistensi antar penilai:

```
Interpretasi Kappa:
- κ < 0.20     : Buruk
- 0.21 - 0.40  : Cukup
- 0.41 - 0.60  : Moderat
- 0.61 - 0.80  : Baik
- 0.81 - 1.00  : Sangat Baik
```

### 2. Perbandingan Grup (RAG vs Manual)

| Uji Statistik | Kegunaan |
|---------------|----------|
| **Independent t-test** | Membandingkan mean skor 2 grup |
| **Mann-Whitney U** | Jika data tidak normal |
| **Effect Size (Cohen's d)** | Besarnya perbedaan praktis |

### 3. Hipotesis

```
H0: Tidak ada perbedaan signifikan antara kualitas assessment 
    RAG-LLM dengan assessment manual

H1: Terdapat perbedaan signifikan antara kualitas assessment 
    RAG-LLM dengan assessment manual

Atau:

H1: Kualitas assessment RAG-LLM setara atau lebih baik dari 
    assessment manual
```

---

## Langkah Pelaksanaan

### Tahap 1: Persiapan (1 minggu)
- [ ] Siapkan 30 assessment dari RAG-LLM
- [ ] Kumpulkan 30 assessment manual dari arsip
- [ ] Siapkan rubrik dan form penilaian
- [ ] Rekrut 3 expert evaluator

### Tahap 2: Evaluasi (1-2 minggu)
- [ ] Distribusikan assessment ke evaluator
- [ ] Evaluator menilai tanpa tahu sumber (blind)
- [ ] Kumpulkan hasil penilaian

### Tahap 3: Analisis (1 minggu)
- [ ] Input data ke SPSS/Excel
- [ ] Hitung Cohen's Kappa (inter-rater)
- [ ] Lakukan uji t-test atau Mann-Whitney
- [ ] Hitung effect size

### Tahap 4: Interpretasi
- [ ] Buat tabel hasil
- [ ] Interpretasi statistik
- [ ] Tulis kesimpulan

---

## Contoh Tabel Hasil

### Tabel 1. Perbandingan Skor Kualitas Assessment

| Kriteria | RAG-LLM (M±SD) | Manual (M±SD) | t | p | Cohen's d |
|----------|----------------|---------------|---|---|-----------|
| Kesesuaian Materi | 4.2 ± 0.7 | 4.0 ± 0.8 | 1.2 | 0.23 | 0.26 |
| Kelengkapan | 4.5 ± 0.5 | 3.8 ± 0.9 | 3.1 | 0.01* | 0.85 |
| Kejelasan | 4.1 ± 0.6 | 4.2 ± 0.6 | -0.5 | 0.62 | -0.17 |
| Tingkat Kesulitan | 3.9 ± 0.8 | 3.7 ± 0.9 | 0.9 | 0.37 | 0.24 |
| Kualitas Kode | 4.3 ± 0.6 | 3.5 ± 1.0 | 3.5 | 0.001** | 0.97 |
| Nilai Edukatif | 4.0 ± 0.7 | 3.9 ± 0.7 | 0.6 | 0.55 | 0.14 |
| **Total** | **25.0 ± 2.1** | **23.1 ± 3.2** | **2.8** | **0.007**| **0.70** |

*p < 0.05, **p < 0.01

### Tabel 2. Inter-Rater Reliability

| Kriteria | Kappa | Interpretasi |
|----------|-------|--------------|
| Kesesuaian Materi | 0.72 | Baik |
| Kelengkapan | 0.81 | Sangat Baik |
| Kejelasan | 0.65 | Baik |
| ... | ... | ... |

---

## Tools yang Direkomendasikan

| Tool | Kegunaan |
|------|----------|
| **SPSS** | Analisis statistik lengkap |
| **Excel** | Input data, grafik sederhana |
| **Python (scipy)** | t-test, effect size |
| **Google Forms** | Form penilaian online |

---

## Template Python untuk Analisis

```python
from scipy import stats
import numpy as np

# Data sampel (ganti dengan data asli)
rag_scores = [25, 24, 26, 23, 27, ...]  # Total skor RAG-LLM
manual_scores = [22, 24, 21, 23, 20, ...]  # Total skor Manual

# Independent t-test
t_stat, p_value = stats.ttest_ind(rag_scores, manual_scores)

# Effect size (Cohen's d)
def cohens_d(group1, group2):
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    return (np.mean(group1) - np.mean(group2)) / pooled_std

d = cohens_d(rag_scores, manual_scores)

print(f"t = {t_stat:.3f}, p = {p_value:.4f}, Cohen's d = {d:.2f}")
```

---

## Referensi

1. Cohen, J. (1960). A coefficient of agreement for nominal scales.
2. Fleiss, J. L. (1971). Measuring nominal scale agreement among many raters.
3. Lakens, D. (2013). Calculating and reporting effect sizes.
