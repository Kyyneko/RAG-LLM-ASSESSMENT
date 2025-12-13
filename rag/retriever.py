# rag/retriever.py

import numpy as np
import os
from typing import Optional

# Import CrossEncoder untuk reranking
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
    print("SUCCESS: CrossEncoder imported successfully")
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    print("WARNING: sentence_transformers CrossEncoder not available")

class CrossEncoderReranker:
    """CrossEncoder reranker untuk meningkatkan presisi retrieval."""

    def __init__(self, model_name: str = "ms-marco-MiniLM-L-6-v2"):
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
                print(f"Loading CrossEncoder model: {model_name}")
                self.model = CrossEncoder(model_name)
                self.is_loaded = True
                print(f"SUCCESS: CrossEncoder model loaded successfully")
            except Exception as e:
                print(f"WARNING: Failed to load CrossEncoder model: {e}")
                print("Falling back to similarity-based scoring")
        else:
            print("WARNING: CrossEncoder not available, install sentence_transformers")

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
            # Fallback ke urutan asli dengan score 0.5
            return [{"text": doc, "score": 0.5} for doc in documents]

        try:
            # Buat pasangan [query, document] untuk CrossEncoder
            pairs = [[query, doc] for doc in documents]

            # Predict relevance scores
            scores = self.model.predict(pairs)

            # Create ranked results
            results = []
            for doc, score in zip(documents, scores):
                results.append({
                    "text": doc,
                    "score": float(score),
                    "reranked": True
                })

            # Sort by score (descending)
            results.sort(key=lambda x: x["score"], reverse=True)

            return results[:top_k]

        except Exception as e:
            print(f"ERROR: CrossEncoder reranking failed: {e}")
            # Fallback ke urutan asli
            return [{"text": doc, "score": 0.5} for doc in documents]

    def is_available(self) -> bool:
        """Check if CrossEncoder is available and loaded."""
        return self.is_loaded

# Global reranker instance
_cross_encoder_reranker: Optional[CrossEncoderReranker] = None

def get_cross_encoder_reranker() -> Optional[CrossEncoderReranker]:
    """Get or create CrossEncoder reranker instance (singleton pattern)."""
    global _cross_encoder_reranker

    if _cross_encoder_reranker is None:
        # Load model yang valid dan terkenal untuk reranking
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
        print("Peringatan: Query kosong, tidak ada konteks yang diambil.")
        return []

    # Mengubah query menjadi embedding vektor
    query_vec = embedder.encode([query])

    # Melakukan pencarian berbasis similaritas vektor
    results = vectorstore.search(query_vec, top_k)

    print(f"Retrieved {len(results)} konteks paling relevan untuk query: {query[:100]}...")
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
        print("Peringatan: Query kosong.")
        return []

    # Step 1: Initial retrieval (ambil lebih banyak kandidat)
    query_vec = embedder.encode([query])
    candidates = vectorstore.search_with_scores(query_vec, initial_k)

    if not candidates:
        print("Tidak ada kandidat yang ditemukan.")
        return []

    # Step 2: Reranking dengan CrossEncoder (auto-load jika tidak ada)
    cross_encoder_reranker = get_cross_encoder_reranker()

    if cross_encoder_reranker and cross_encoder_reranker.is_available():
        try:
            print(f"SUCCESS: Using CrossEncoder reranking for {len(candidates)} candidates")

            # Extract teks dari candidates
            candidate_texts = [cand["text"] for cand in candidates]

            # Rerank menggunakan CrossEncoder
            reranked_results = cross_encoder_reranker.rerank(query, candidate_texts, len(candidates))

            # Update candidates dengan rerank scores
            for i, cand in enumerate(candidates):
                cand["original_score"] = cand["score"]
                cand["rerank_score"] = reranked_results[i]["score"]
                cand["score"] = cand["rerank_score"]  # Gunakan rerank score sebagai score utama
                cand["reranked"] = True

            # Sort ulang berdasarkan rerank score
            candidates.sort(key=lambda x: x["score"], reverse=True)
            print(f"SUCCESS: CrossEncoder reranking selesai untuk {len(candidates)} kandidat")

        except Exception as e:
            print(f"WARNING: CrossEncoder reranking gagal, menggunakan similarity score: {e}")
            print(f"Fallback ke similarity-based retrieval")
    elif reranker is not None:
        # Manual reranker (legacy support)
        try:
            print(f"SUCCESS: Using manual reranker for {len(candidates)} candidates")

            # Buat pasangan [query, chunk] untuk reranking
            pairs = [[query, cand["text"]] for cand in candidates]
            rerank_scores = reranker.predict(pairs)

            # Update scores dengan hasil reranking
            for i, cand in enumerate(candidates):
                cand["rerank_score"] = float(rerank_scores[i])
                cand["original_score"] = cand["score"]
                cand["score"] = cand["rerank_score"]  # Gunakan rerank score sebagai score utama
                cand["reranked"] = True

            # Sort ulang berdasarkan rerank score
            candidates.sort(key=lambda x: x["score"], reverse=True)
            print(f"SUCCESS: Manual reranking selesai: {len(candidates)} kandidat")
        except Exception as e:
            print(f"WARNING: Manual reranking gagal, menggunakan similarity score: {e}")
    else:
        print("INFO: No reranker available, using similarity scores only")

    # Step 3: Filter berdasarkan threshold
    filtered = [
        cand for cand in candidates
        if cand["score"] >= score_threshold
    ]

    # Step 4: Ambil top-k
    results = filtered[:top_k]

    print(f"Retrieved {len(results)} konteks (setelah reranking & filtering)")
    return results


def retrieve_context_simple(vectorstore, embedder, query: str, top_k: int = 5) -> list[str]:
    """
    Alias untuk retrieve_context (untuk backward compatibility).
    """
    return retrieve_context(vectorstore, embedder, query, top_k)