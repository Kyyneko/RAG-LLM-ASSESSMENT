import faiss
import numpy as np
import pickle
import os

class VectorStore:
    """
    Kelas penyimpanan vektor berbasis FAISS dengan metadata tracking dan persistence.
    
    Fitur baru:
    - Metadata untuk setiap chunk (source file, subject_id, dll)
    - Save/load ke disk untuk caching
    - Search dengan filtering metadata
    - Relevance score tracking
    
    Atribut:
        dim (int): Dimensi embedding yang digunakan.
        index (faiss.IndexFlatIP): Objek indeks FAISS untuk pencarian berbasis vektor.
        texts (list[str]): Daftar potongan teks (chunks).
        metadata (list[dict]): Metadata untuk setiap chunk.
    """
    
    def __init__(self, dim: int):
        """
        Inisialisasi VectorStore baru dengan indeks FAISS.
        
        Args:
            dim (int): Dimensi embedding yang digunakan oleh model.
        """
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.texts = []
        self.metadata = []
        print(f"VectorStore diinisialisasi dengan dimensi embedding: {dim}")
    
    def add(self, embeddings: np.ndarray, texts: list[str], metadata: list[dict] = None) -> None:
        """
        Menambahkan embedding, teks, dan metadata ke dalam indeks FAISS.
        
        Args:
            embeddings (np.ndarray): Array embedding (shape: [n, dim]).
            texts (list[str]): Daftar teks yang terkait dengan embedding.
            metadata (list[dict], optional): Metadata untuk setiap chunk.
                Format: [{"source": "file.pdf", "subject_id": 5, "chunk_index": 0}, ...]
        """
        if embeddings is None or len(embeddings) == 0:
            print("⚠️ Tidak ada embedding yang ditambahkan ke vector store")
            return
        
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        
        self.index.add(embeddings)
        self.texts.extend(texts)
        
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend([{}] * len(texts))
    
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[str]:
        """
        Melakukan pencarian top-k potongan teks yang paling relevan (backward compatible).
        
        Args:
            query_vector (np.ndarray): Embedding dari query yang akan dicari.
            top_k (int, optional): Jumlah hasil teratas yang dikembalikan.
        
        Returns:
            list[str]: Daftar teks paling relevan berdasarkan kemiripan vektor.
        """
        results = self.search_with_scores(query_vector, top_k)
        return [r["text"] for r in results]
    
    def search_with_scores(self, query_vector: np.ndarray, top_k: int = 5, 
                           filter_fn=None) -> list[dict]:
        """
        Pencarian dengan relevance scores dan filtering metadata.
        
        Args:
            query_vector (np.ndarray): Embedding dari query.
            top_k (int): Jumlah hasil teratas.
            filter_fn (callable, optional): Fungsi filter untuk metadata.
                Contoh: lambda meta: meta.get('subject_id') == 5
        
        Returns:
            list[dict]: Hasil dengan format:
                [{"text": "...", "score": 0.85, "metadata": {...}}, ...]
        """
        if len(query_vector.shape) == 1:
            query_vector = query_vector.reshape(1, -1)
        
        k_candidates = min(top_k * 4 if filter_fn else top_k, len(self.texts))
        
        if k_candidates == 0:
            print("⚠️ VectorStore masih kosong")
            return []
        
        distances, indices = self.index.search(query_vector, k_candidates)
        
        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx < len(self.texts):
                if filter_fn is None or filter_fn(self.metadata[idx]):
                    results.append({
                        "text": self.texts[idx],
                        "score": float(score),
                        "metadata": self.metadata[idx]
                    })
                    
                    if len(results) >= top_k:
                        break
        
        return results
    
    def save_to_disk(self, index_path: str, data_path: str) -> None:
        """
        Simpan FAISS index dan data (texts + metadata) ke disk untuk caching.
        
        Args:
            index_path (str): Path untuk menyimpan FAISS index (e.g., "cache/subject_5.index")
            data_path (str): Path untuk menyimpan texts dan metadata (e.g., "cache/subject_5.pkl")
        """
        os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
        
        faiss.write_index(self.index, index_path)
        
        with open(data_path, 'wb') as f:
            pickle.dump({
                'texts': self.texts,
                'metadata': self.metadata,
                'dim': self.dim
            }, f)
        
        print(f"✓ Vector store disimpan ke {index_path}")
    
    @classmethod
    def load_from_disk(cls, index_path: str, data_path: str):
        """
        Muat FAISS index dari disk.
        
        Args:
            index_path (str): Path FAISS index file.
            data_path (str): Path data pickle file.
        
        Returns:
            VectorStore: Instance yang sudah dimuat dari cache.
        """
        with open(data_path, 'rb') as f:
            data = pickle.load(f)
        
        instance = cls(data['dim'])
        
        instance.index = faiss.read_index(index_path)
        instance.texts = data['texts']
        instance.metadata = data.get('metadata', [])
        
        print(f"✓ Vector store dimuat dari cache: {len(instance.texts)} chunks")
        return instance
    
    def get_stats(self) -> dict:
        """
        Mengembalikan informasi statistik dari VectorStore.
        
        Returns:
            dict: Statistik vector store.
        """
        return {
            "dimension": self.dim,
            "total_vectors": self.index.ntotal,
            "total_texts": len(self.texts),
            "has_metadata": len(self.metadata) > 0
        }
