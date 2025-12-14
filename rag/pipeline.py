import os
import time
from .extractor import extract_text
from .chunker import create_chunks
from .embedder import Embedder
from .vectorstore import VectorStore

def process_files(file_paths: list[str], embedder: Embedder = None, 
                  subject_id: int = None) -> VectorStore:
    """
    Memproses sejumlah file untuk membangun vector store dengan metadata tracking.
    
    Args:
        file_paths (list[str]): Daftar path file yang akan diproses.
        embedder (Embedder, optional): Instance embedder.
        subject_id (int, optional): ID subject untuk metadata.
    
    Returns:
        VectorStore: Objek VectorStore yang telah berisi seluruh embedding dokumen.
    """
    if embedder is None:
        embedder = Embedder()
    
    vectorstore = VectorStore(embedder.dim)
    total_files = len(file_paths)
    total_chunks = 0
    
    print("=" * 60)
    print("RAG INDEXING PIPELINE")
    print("=" * 60)
    print(f"Total file yang akan diproses: {total_files}\n")
    
    for idx, file_path in enumerate(file_paths, 1):
        if not os.path.exists(file_path):
            print(f"[{idx}/{total_files}] File tidak ditemukan: {file_path}")
            continue
        
        filename = os.path.basename(file_path)
        print(f"[{idx}/{total_files}] Memproses file: {filename}")
        
        print("  - Mengekstrak teks...")
        text = extract_text(file_path)
        
        if not text or not text.strip():
            print("  - Tidak ada teks yang berhasil diekstrak, dilewati.\n")
            continue
        
        print(f"  - Teks berhasil diekstrak ({len(text)} karakter)")
        
        print("  - Membuat potongan teks (chunks) dengan semantic splitting...")
        chunks = list(create_chunks(text, max_chars=1000, overlap=200))
        
        if not chunks:
            print("  - Tidak ada chunk yang dihasilkan, dilewati.\n")
            continue
        
        print(f"  - Total chunk dibuat: {len(chunks)}")
        
        metadata = [{
            "source": filename,
            "file_path": file_path,
            "subject_id": subject_id,
            "chunk_index": i,
            "total_chunks": len(chunks)
        } for i in range(len(chunks))]
        
        print("  - Menghasilkan embedding...")
        embeddings = embedder.encode(chunks)
        
        print("  - Menambahkan ke vector store...")
        vectorstore.add(embeddings, chunks, metadata)
        
        total_chunks += len(chunks)
        print("  - Proses selesai untuk file ini.\n")
    
    print("=" * 60)
    print("INDEXING SELESAI")
    print(f" • Jumlah file diproses: {total_files}")
    print(f" • Total chunk terindeks: {total_chunks}")
    print(f" • Statistik VectorStore: {vectorstore.get_stats()}")
    print("=" * 60)
    
    return vectorstore


def build_vectorstore_for_subject(subject_id: int, use_cache: bool = True):
    """
    Membentuk VectorStore untuk subject dengan caching support.
    
    Jika cache valid (tidak ada dokumen baru), muat dari cache.
    Jika ada dokumen baru atau cache tidak ada, rebuild dan simpan cache.
    
    Args:
        subject_id (int): ID subject.
        use_cache (bool): Apakah menggunakan cache (default: True).
    
    Returns:
        tuple: (VectorStore, metadata)
    """
    from db.connection import get_connection
    
    cache_dir = "cache/vectorstores"
    os.makedirs(cache_dir, exist_ok=True)
    
    index_path = f"{cache_dir}/subject_{subject_id}.index"
    data_path = f"{cache_dir}/subject_{subject_id}.pkl"
    
    if use_cache and os.path.exists(index_path) and os.path.exists(data_path):
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as new_docs 
                FROM rag_source_documents 
                WHERE subject_id = %s AND is_indexed = FALSE
            """, (subject_id,))
            
            result = cur.fetchone()
            new_docs_count = result['new_docs'] if result else 0
            
            if new_docs_count == 0:
                print(f"✓ Menggunakan cached vector store untuk subject {subject_id}")
                conn.close()
                
                try:
                    vectorstore = VectorStore.load_from_disk(index_path, data_path)
                    metadata = {
                        "subject_id": subject_id,
                        "from_cache": True,
                        "docs_processed": 0,
                        "chunks_indexed": vectorstore.get_stats()["total_texts"]
                    }
                    return vectorstore, metadata
                except Exception as e:
                    print(f"⚠️ Cache loading gagal: {e}. Membangun ulang...")
        
        conn.close()
    
    print(f"⚙️ Membangun ulang vector store untuk subject {subject_id}")
    vectorstore, metadata = _build_vectorstore_from_db(subject_id)
    
    try:
        vectorstore.save_to_disk(index_path, data_path)
        metadata["cached"] = True
    except Exception as e:
        print(f"⚠️ Gagal menyimpan cache: {e}")
        metadata["cached"] = False
    
    return vectorstore, metadata


def _build_vectorstore_from_db(subject_id: int):
    """
    Internal function: Build VectorStore dari database.
    
    Args:
        subject_id (int): ID subject.
    
    Returns:
        tuple: (VectorStore, metadata dict)
    """
    from db.connection import get_connection
    
    conn = get_connection()
    embedder = Embedder()
    vectorstore = VectorStore(embedder.dim)
    
    metadata = {
        "subject_id": subject_id,
        "docs_processed": 0,
        "chunks_indexed": 0,
        "failed_files": [],
        "from_cache": False
    }
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, file_path, file_name
                FROM rag_source_documents
                WHERE subject_id = %s AND is_indexed = FALSE
            """, (subject_id,))
            
            docs = cur.fetchall()
            
            if not docs:
                print(f"ℹ️ Tidak ada dokumen baru untuk subject_id={subject_id}")
                return vectorstore, metadata
            
            print(f"📄 Ditemukan {len(docs)} dokumen untuk diindeks")
            
            for doc in docs:
                doc_id = doc["id"]
                file_path = doc["file_path"]
                file_name = doc["file_name"]
                
                if not os.path.exists(file_path):
                    print(f"⚠️ File tidak ditemukan: {file_path}")
                    metadata["failed_files"].append(file_name)
                    continue
                
                print(f"  Memproses: {file_name}")
                
                text = extract_text(file_path)
                if not text:
                    metadata["failed_files"].append(file_name)
                    continue
                
                chunks = list(create_chunks(text, max_chars=1000, overlap=200))
                if not chunks:
                    metadata["failed_files"].append(file_name)
                    continue
                
                chunk_metadata = [{
                    "source": file_name,
                    "file_path": file_path,
                    "subject_id": subject_id,
                    "chunk_index": i,
                    "doc_id": doc_id
                } for i in range(len(chunks))]
                
                embeddings = embedder.encode(chunks)
                vectorstore.add(embeddings, chunks, chunk_metadata)
                
                metadata["docs_processed"] += 1
                metadata["chunks_indexed"] += len(chunks)
                
                cur.execute("""
                    UPDATE rag_source_documents
                    SET is_indexed = TRUE
                    WHERE id = %s
                """, (doc_id,))
                
                conn.commit()
                print(f"  ✓ {len(chunks)} chunks terindeks")
        
    except Exception as e:
        print(f"✗ Kesalahan dalam build_vectorstore_for_subject: {str(e)}")
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    return vectorstore, metadata
