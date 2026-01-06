import numpy as np
import os
from typing import Optional

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
    print("[OK] CrossEncoder berhasil diimpor")
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    print("[WARNING] CrossEncoder tidak tersedia dari sentence_transformers")

class CrossEncoderReranker:
    """CrossEncoder reranker untuk meningkatkan presisi retrieval."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-TinyBERT-L-2-v2"):
        """
        Inisialisasi CrossEncoder reranker.

        Args:
            model_name: Model CrossEncoder (default: ms-marco-MiniLM-L-6-v2)
        """
        self.model_name = model_name
        self.model = None
        self.is_loaded = False

        if CROSS_ENCODER_AVAILABLE:
            try:
                print(f"Memuat model CrossEncoder: {model_name}")
                self.model = CrossEncoder(model_name)
                self.is_loaded = True
                print(f"✓ Model CrossEncoder berhasil dimuat")
            except Exception as e:
                print(f"⚠️ Gagal memuat model CrossEncoder: {e}")
                print("Fallback ke similarity-based scoring")
        else:
            print("⚠️ CrossEncoder tidak tersedia, install sentence_transformers")

    def rerank(self, query: str, documents: list[str], top_k: int = 10) -> list[dict]:
        """
        Rerank documents menggunakan CrossEncoder.

        Args:
            query: Query pencarian
            documents: List dokumen untuk di-rerank
            top_k: Jumlah hasil terbaik yang dikembalikan

        Returns:
            List dict dengan format: [{"text": "...", "score": 0.85}, ...]
        """
        if not self.is_loaded or not documents:
            return [{"text": doc, "score": 0.5} for doc in documents]

        try:
            pairs = [[query, doc] for doc in documents]

            scores = self.model.predict(pairs)

            results = []
            for doc, score in zip(documents, scores):
                results.append({
                    "text": doc,
                    "score": float(score),
                    "reranked": True
                })

            results.sort(key=lambda x: x["score"], reverse=True)

            return results[:top_k]

        except Exception as e:
            print(f"✗ CrossEncoder reranking gagal: {e}")
            return [{"text": doc, "score": 0.5} for doc in documents]

    def is_available(self) -> bool:
        """Check if CrossEncoder is available and loaded."""
        return self.is_loaded

_cross_encoder_reranker: Optional[CrossEncoderReranker] = None

def get_cross_encoder_reranker() -> Optional[CrossEncoderReranker]:
    """Get or create CrossEncoder reranker instance (singleton pattern)."""
    global _cross_encoder_reranker

    if _cross_encoder_reranker is None:
        _cross_encoder_reranker = CrossEncoderReranker("cross-encoder/ms-marco-TinyBERT-L-2-v2")

    return _cross_encoder_reranker

def retrieve_context(vectorstore, embedder, query: str, top_k: int = 5) -> list[str]:
    """
    Mengambil (retrieve) sejumlah potongan teks yang paling relevan (backward compatible).

    Args:
        vectorstore: Instance dari kelas VectorStore.
        embedder: Instance dari kelas Embedder.
        query (str): Kalimat atau teks pencarian (query).
        top_k (int, optional): Jumlah hasil teratas (default: 5).

    Returns:
        list[str]: Daftar potongan teks paling relevan.
    """
    if not query or not query.strip():
        print("⚠️ Query kosong, tidak ada konteks yang diambil")
        return []

    query_vec = embedder.encode([query])

    results = vectorstore.search(query_vec, top_k)

    print(f"Ditemukan {len(results)} konteks paling relevan untuk query: {query[:100]}...")
    return results


def retrieve_context_with_reranking(vectorstore, embedder, query: str,
                                     top_k: int = 5, initial_k: int = 20,
                                     score_threshold: float = 0.3,
                                     reranker=None) -> list[dict]:
    """
    Retrieval dengan reranking untuk meningkatkan presisi hasil.

    Proses:
    1. Ambil top-N kandidat dari vectorstore (initial retrieval)
    2. Rerank menggunakan cross-encoder (jika tersedia)
    3. Filter berdasarkan score threshold
    4. Kembalikan top-k terbaik

    Args:
        vectorstore: Instance VectorStore.
        embedder: Instance Embedder.
        query (str): Query pencarian.
        top_k (int): Jumlah hasil akhir yang dikembalikan.
        initial_k (int): Jumlah kandidat awal untuk reranking.
        score_threshold (float): Threshold minimum untuk relevance score.
        reranker: Instance CrossEncoder (optional, jika None skip reranking).

    Returns:
        list[dict]: Hasil dengan format:
            [{"text": "...", "score": 0.85, "metadata": {...}}, ...]
    """
    if not query or not query.strip():
        print("⚠️ Query kosong")
        return []

    query_vec = embedder.encode([query])
    candidates = vectorstore.search_with_scores(query_vec, initial_k)

    if not candidates:
        print("Tidak ada kandidat yang ditemukan")
        return []

    cross_encoder_reranker = get_cross_encoder_reranker()

    if cross_encoder_reranker and cross_encoder_reranker.is_available():
        try:
            print(f"✓ Menggunakan CrossEncoder reranking untuk {len(candidates)} kandidat")

            candidate_texts = [cand["text"] for cand in candidates]

            reranked_results = cross_encoder_reranker.rerank(query, candidate_texts, len(candidates))

            for i, cand in enumerate(candidates):
                cand["original_score"] = cand["score"]
                cand["rerank_score"] = reranked_results[i]["score"]
                cand["score"] = cand["rerank_score"]
                cand["reranked"] = True

            candidates.sort(key=lambda x: x["score"], reverse=True)
            print(f"✓ CrossEncoder reranking selesai untuk {len(candidates)} kandidat")

        except Exception as e:
            print(f"⚠️ CrossEncoder reranking gagal, menggunakan similarity score: {e}")
            print(f"Fallback ke similarity-based retrieval")
    elif reranker is not None:
        try:
            print(f"✓ Menggunakan manual reranker untuk {len(candidates)} kandidat")

            pairs = [[query, cand["text"]] for cand in candidates]
            rerank_scores = reranker.predict(pairs)

            for i, cand in enumerate(candidates):
                cand["rerank_score"] = float(rerank_scores[i])
                cand["original_score"] = cand["score"]
                cand["score"] = cand["rerank_score"]
                cand["reranked"] = True

            candidates.sort(key=lambda x: x["score"], reverse=True)
            print(f"✓ Manual reranking selesai: {len(candidates)} kandidat")
        except Exception as e:
            print(f"⚠️ Manual reranking gagal, menggunakan similarity score: {e}")
    else:
        print("ℹ️ Tidak ada reranker tersedia, menggunakan similarity scores saja")

    filtered = [
        cand for cand in candidates
        if cand["score"] >= score_threshold
    ]

    results = filtered[:top_k]

    print(f"Ditemukan {len(results)} konteks (setelah reranking & filtering)")
    return results


def retrieve_context_simple(vectorstore, embedder, query: str, top_k: int = 5) -> list[str]:
    """
    Alias untuk retrieve_context (untuk backward compatibility).
    """
    return retrieve_context(vectorstore, embedder, query, top_k)