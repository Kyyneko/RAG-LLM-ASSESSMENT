# rag/processor.py

import os
import pymysql
import numpy as np
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from db.connection import get_connection


def index_rag_documents(chunk_size: int = 500):
    """
    Melakukan proses indexing untuk seluruh dokumen pada tabel `rag_source_documents`
    yang belum diindeks. Dokumen akan diekstraksi, dipecah menjadi potongan teks (chunks),
    kemudian diubah menjadi embedding menggunakan model SentenceTransformer,
    dan hasilnya disimpan ke dalam tabel `rag_chunks`.

    Args:
        chunk_size (int, optional): Panjang maksimum karakter tiap potongan teks (default: 500).

    Database yang digunakan:
        - `rag_source_documents`: Menyimpan metadata file sumber.
        - `rag_chunks`: Menyimpan teks hasil chunking dan embedding-nya.

    Catatan:
        Fungsi ini dirancang untuk indexing berbasis database (legacy),
        dan dapat digantikan oleh pipeline FAISS yang lebih modern.
    """
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, file_path FROM rag_source_documents WHERE is_indexed = FALSE")
    docs = cur.fetchall()

    if not docs:
        print("Tidak ada dokumen baru yang perlu diindeks.")
        cur.close()
        conn.close()
        return

    print(f"Memulai proses indexing untuk {len(docs)} dokumen...\n")

    for doc in docs:
        doc_id, path = doc.values() if isinstance(doc, dict) else doc

        if not os.path.exists(path):
            print(f"File tidak ditemukan: {path}")
            continue

        print(f"Memproses dokumen: {path}")

        # 1. Ekstraksi teks dari PDF
        try:
            reader = PdfReader(path)
            text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        except Exception as e:
            print(f"Gagal membaca file PDF ({path}): {str(e)}")
            continue

        if not text or not text.strip():
            print(f"Tidak ada teks yang dapat diekstraksi dari {path}.")
            continue

        # 2. Pemecahan teks menjadi potongan (chunks)
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        if not chunks:
            print(f"Tidak ada chunk yang terbentuk untuk {path}.")
            continue

        # 3. Pembentukan embedding
        embeddings = model.encode(chunks, normalize_embeddings=True)

        # 4. Penyimpanan hasil ke database
        try:
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                cur.execute("""
                    INSERT INTO rag_chunks (document_id, chunk_index, chunk_text, embedding)
                    VALUES (%s, %s, %s, %s)
                """, (doc_id, i, chunk, np.array(emb, dtype=np.float32).tobytes()))

            cur.execute("""
                UPDATE rag_source_documents
                SET is_indexed = TRUE
                WHERE id = %s
            """, (doc_id,))

            conn.commit()
            print(f"Dokumen {os.path.basename(path)} berhasil diindeks ({len(chunks)} chunk).")

        except pymysql.Error as e:
            conn.rollback()
            print(f"Kesalahan database saat memproses {path}: {str(e)}")

    cur.close()
    conn.close()
    print("\nProses indexing selesai.")
