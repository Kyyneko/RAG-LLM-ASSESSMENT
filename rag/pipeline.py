import os
import time
import logging
from .extractor import extract_text
from .chunker import create_chunks
from .embedder import Embedder
from .vectorstore import VectorStore

logger = logging.getLogger(__name__)

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
    
    logger.info(f"Starting RAG indexing pipeline for {total_files} files")
    
    for idx, file_path in enumerate(file_paths, 1):
        if not os.path.exists(file_path):
            logger.warning(f"[{idx}/{total_files}] File not found: {file_path}")
            continue
        
        filename = os.path.basename(file_path)
        logger.info(f"[{idx}/{total_files}] Processing file: {filename}")
        
        logger.debug("  Extracting text...")
        text = extract_text(file_path)
        
        if not text or not text.strip():
            logger.warning("  No text extracted, skipping")
            continue
        
        logger.debug(f"  Text extracted ({len(text)} characters)")
        
        logger.debug("  Creating chunks with semantic splitting...")
        chunks = list(create_chunks(text, max_chars=1000, overlap=200))
        
        if not chunks:
            logger.warning("  No chunks generated, skipping")
            continue
        
        logger.debug(f"  Total chunks created: {len(chunks)}")
        
        metadata = [{
            "source": filename,
            "file_path": file_path,
            "subject_id": subject_id,
            "chunk_index": i,
            "total_chunks": len(chunks)
        } for i in range(len(chunks))]
        
        logger.debug("  Generating embeddings...")
        embeddings = embedder.encode(chunks)
        
        logger.debug("  Adding to vector store...")
        vectorstore.add(embeddings, chunks, metadata)
        
        total_chunks += len(chunks)
        logger.debug("  File processing completed")
    
    logger.info(f"Indexing completed: {total_files} files, {total_chunks} chunks indexed")
    logger.debug(f"VectorStore stats: {vectorstore.get_stats()}")
    
    return vectorstore
