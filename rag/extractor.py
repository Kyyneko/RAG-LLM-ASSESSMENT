# rag/extractor.py
import os
from pypdf import PdfReader
from docx import Document


def extract_text_from_pdf(path: str) -> str:
    """
    Mengekstrak teks dari file PDF.

    Args:
        path (str): Lokasi file PDF.

    Returns:
        str: Konten teks hasil ekstraksi.
    """
    try:
        reader = PdfReader(path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        print(f"Kesalahan saat mengekstrak PDF ({path}): {str(e)}")
        return ""


def extract_text_from_docx(path: str) -> str:
    """
    Mengekstrak teks dari file DOCX.

    Args:
        path (str): Lokasi file DOCX.

    Returns:
        str: Konten teks hasil ekstraksi.
    """
    try:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        print(f"Kesalahan saat mengekstrak DOCX ({path}): {str(e)}")
        return ""


def extract_text_from_txt(path: str) -> str:
    """
    Membaca teks dari file TXT.

    Args:
        path (str): Lokasi file TXT.

    Returns:
        str: Konten teks hasil pembacaan.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print(f"Kesalahan saat membaca TXT ({path}): {str(e)}")
        return ""


def extract_text(path: str) -> str:
    """
    Menentukan metode ekstraksi berdasarkan ekstensi file.

    Args:
        path (str): Lokasi file yang akan diekstrak.

    Returns:
        str: Konten teks hasil ekstraksi. Jika format tidak didukung atau file tidak ditemukan,
             fungsi akan mengembalikan string kosong.
    """
    if not os.path.exists(path):
        print(f"File tidak ditemukan: {path}")
        return ""

    ext = path.lower()

    if ext.endswith(".pdf"):
        return extract_text_from_pdf(path)
    elif ext.endswith(".docx"):
        return extract_text_from_docx(path)
    elif ext.endswith(".txt"):
        return extract_text_from_txt(path)
    else:
        print(f"Format file tidak didukung: {path}")
        return ""
