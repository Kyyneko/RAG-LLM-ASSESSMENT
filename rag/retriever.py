# rag/retriever.py

import numpy as np

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
    
    # Step 2: Reranking (jika reranker tersedia)
    if reranker is not None:
        try:
            # Buat pasangan [query, chunk] untuk reranking
            pairs = [[query, cand["text"]] for cand in candidates]
            rerank_scores = reranker.predict(pairs)
            
            # Update scores dengan hasil reranking
            for i, cand in enumerate(candidates):
                cand["rerank_score"] = float(rerank_scores[i])
                cand["original_score"] = cand["score"]
                cand["score"] = cand["rerank_score"]  # Gunakan rerank score sebagai score utama
            
            # Sort ulang berdasarkan rerank score
            candidates.sort(key=lambda x: x["score"], reverse=True)
            print(f"✓ Reranking selesai: {len(candidates)} kandidat")
        except Exception as e:
            print(f"⚠️  Reranking gagal, menggunakan similarity score: {e}")
    
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
