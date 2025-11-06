# rag/reranker.py
# File OPTIONAL - gunakan jika ingin implement reranking dengan cross-encoder

"""
CARA INSTALL RERANKER (jika ingin gunakan):
pip install sentence-transformers

Lalu uncomment kode di bawah.
"""

from sentence_transformers import CrossEncoder

class Reranker:
    """
    Wrapper untuk cross-encoder reranking model.
    
    Cross-encoder memberikan scoring yang lebih akurat dibanding
    bi-encoder (embedding similarity) karena memproses query dan dokumen secara bersamaan.
    """
    
    _instance = None
    _model = None
    
    def __new__(cls, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Singleton pattern untuk model reranker."""
        if cls._instance is None:
            print(f"Memuat reranker model: {model_name}")
            cls._instance = super().__new__(cls)
            cls._model = CrossEncoder(model_name)
        return cls._instance
    
    def predict(self, pairs: list) -> list:
        """
        Memberikan relevance score untuk pasangan [query, document].
        
        Args:
            pairs (list): List of [query, document] pairs
                Example: [["what is RAG?", "RAG stands for..."], ...]
        
        Returns:
            list: Relevance scores (higher = more relevant)
        """
        return self._model.predict(pairs)
