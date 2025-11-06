import os
import numpy as np
from sentence_transformers import SentenceTransformer
from huggingface_hub import login


class Embedder:
    """
    Wrapper untuk model SentenceTransformer dengan pola Singleton.
    Termasuk auto-login Hugging Face melalui environment variable (.env)
    agar dapat mengunduh model private seperti all-MiniLM-L6-v2.

    Contoh:
        >>> embedder = Embedder()
        >>> vecs = embedder.encode(["contoh teks"])
        >>> print(vecs.shape)
        (1, 384)
    """

    _instance = None
    _model = None
    _dim = None

    def __new__(cls, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        if cls._instance is None:
            # === Auto-login Hugging Face ===
            token = os.getenv("HUGGINGFACE_HUB_TOKEN")
            if token:
                try:
                    login(token=token)
                    print("✓ Login Hugging Face berhasil (token dari .env).")
                except Exception as e:
                    print(f"⚠️  Gagal login Hugging Face: {e}")
            else:
                print("ℹ️  Tidak ada token Hugging Face di environment, mencoba tanpa login.")

            # === Muat model utama dengan fallback ===
            try:
                print(f"Memuat model embedding: {model_name}")
                cls._instance = super().__new__(cls)
                cls._model = SentenceTransformer(model_name)
                cls._dim = cls._model.get_sentence_embedding_dimension()
                print(f"✓ Model berhasil dimuat. Dimensi: {cls._dim}")
            except Exception as e:
                print(f"⚠️  Gagal memuat model '{model_name}': {e}")
                print("→ Menggunakan model fallback: paraphrase-MiniLM-L6-v2 (publik).")
                cls._instance = super().__new__(cls)
                cls._model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
                cls._dim = cls._model.get_sentence_embedding_dimension()
                print(f"✓ Fallback model dimuat. Dimensi: {cls._dim}")
        return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        return self._model

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts) -> np.ndarray:
        """Mengubah teks menjadi embedding normalisasi L2."""
        if isinstance(texts, str):
            texts = [texts]
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.array(vectors, dtype="float32")
