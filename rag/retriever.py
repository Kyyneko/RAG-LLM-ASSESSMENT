import numpy as np
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
    logger.info("CrossEncoder imported successfully")
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logger.warning("CrossEncoder not available from sentence_transformers")

class CrossEncoderReranker:
    """CrossEncoder reranker untuk meningkatkan presisi retrieval."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-TinyBERT-L-2-v2"):
        """
        Inisialisasi CrossEncoder reranker.

        Args:
            model_name: Model CrossEncoder (default: ms-marco-TinyBERT-L-2-v2)
        """
        self.model_name = model_name
        self.model = None
        self.is_loaded = False

        if CROSS_ENCODER_AVAILABLE:
            try:
                logger.info(f"Loading CrossEncoder model: {model_name}")
                self.model = CrossEncoder(model_name)
                self.is_loaded = True
                logger.info("CrossEncoder model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load CrossEncoder model: {e}")
                logger.info("Fallback to similarity-based scoring")
        else:
            logger.warning("CrossEncoder not available, install sentence_transformers")

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
            logger.error(f"CrossEncoder reranking failed: {e}")
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
        logger.warning("Empty query")
        return []

    query_vec = embedder.encode([query])
    candidates = vectorstore.search_with_scores(query_vec, initial_k)

    if not candidates:
        logger.debug("No candidates found")
        return []

    cross_encoder_reranker = get_cross_encoder_reranker()

    if cross_encoder_reranker and cross_encoder_reranker.is_available():
        try:
            logger.debug(f"Using CrossEncoder reranking for {len(candidates)} candidates")

            candidate_texts = [cand["text"] for cand in candidates]

            reranked_results = cross_encoder_reranker.rerank(query, candidate_texts, len(candidates))

            for i, cand in enumerate(candidates):
                cand["original_score"] = cand["score"]
                cand["rerank_score"] = reranked_results[i]["score"]
                cand["score"] = cand["rerank_score"]
                cand["reranked"] = True

            candidates.sort(key=lambda x: x["score"], reverse=True)
            logger.debug(f"CrossEncoder reranking completed for {len(candidates)} candidates")

        except Exception as e:
            logger.warning(f"CrossEncoder reranking failed, using similarity score: {e}")
    elif reranker is not None:
        try:
            logger.debug(f"Using manual reranker for {len(candidates)} candidates")

            pairs = [[query, cand["text"]] for cand in candidates]
            rerank_scores = reranker.predict(pairs)

            for i, cand in enumerate(candidates):
                cand["rerank_score"] = float(rerank_scores[i])
                cand["original_score"] = cand["score"]
                cand["score"] = cand["rerank_score"]
                cand["reranked"] = True

            candidates.sort(key=lambda x: x["score"], reverse=True)
            logger.debug(f"Manual reranking completed: {len(candidates)} candidates")
        except Exception as e:
            logger.warning(f"Manual reranking failed, using similarity score: {e}")
    else:
        logger.debug("No reranker available, using similarity scores only")

    filtered = [
        cand for cand in candidates
        if cand["score"] >= score_threshold
    ]

    results = filtered[:top_k]

    logger.info(f"Found {len(results)} contexts (after reranking & filtering)")
    return results