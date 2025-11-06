# rag/chunker.py

def create_chunks(text: str, max_chars: int = 1500, overlap: int = 300):
    """
    Memecah teks dengan mempertimbangkan struktur semantik (paragraf dan kalimat).
    
    OPTIMIZATION: Increased default max_chars from 1000 to 1500 and overlap from 200 to 300
    untuk menjaga konteks yang lebih kaya, terutama untuk dokumen teknis programming.
    
    Metode ini lebih baik dari chunking berbasis karakter mentah karena:
    - Menghindari pemotongan di tengah kalimat
    - Mempertimbangkan batas paragraf
    - Menjaga konteks yang lebih koheren
    
    Args:
        text (str): Teks input yang akan dipecah.
        max_chars (int, optional): Jumlah maksimum karakter per chunk (default: 1500).
        overlap (int, optional): Jumlah karakter tumpang tindih antar chunk (default: 300).
        
    Yields:
        str: Potongan teks (chunk) hasil pemrosesan.
    """
    if not text or not text.strip():
        return
    
    # Pisahkan berdasarkan paragraf terlebih dahulu
    paragraphs = text.split('\n\n')
    current_chunk = ""
    previous_chunk_tail = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Jika menambahkan paragraf ini tidak melebihi limit
        if len(current_chunk) + len(para) + 2 <= max_chars:  # +2 untuk \n\n
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
        else:
            # Paragraf terlalu panjang atau chunk sudah penuh
            if current_chunk:
                # Simpan chunk yang ada dengan overlap dari chunk sebelumnya
                full_chunk = previous_chunk_tail + current_chunk
                yield full_chunk.strip()
                
                # Simpan tail untuk overlap di chunk berikutnya
                if len(current_chunk) > overlap:
                    previous_chunk_tail = current_chunk[-overlap:]
                else:
                    previous_chunk_tail = current_chunk
                current_chunk = ""
            
            # Jika paragraf sendiri terlalu panjang, pecah berdasarkan kalimat
            if len(para) > max_chars:
                sentences = _split_into_sentences(para)
                sentence_chunk = ""
                
                for sent in sentences:
                    if len(sentence_chunk) + len(sent) + 1 <= max_chars:
                        sentence_chunk = sentence_chunk + " " + sent if sentence_chunk else sent
                    else:
                        if sentence_chunk:
                            full_chunk = previous_chunk_tail + sentence_chunk
                            yield full_chunk.strip()
                            
                            if len(sentence_chunk) > overlap:
                                previous_chunk_tail = sentence_chunk[-overlap:]
                            else:
                                previous_chunk_tail = sentence_chunk
                        sentence_chunk = sent
                
                # Sisa kalimat menjadi current_chunk berikutnya
                if sentence_chunk:
                    current_chunk = sentence_chunk
            else:
                # Paragraf tidak terlalu panjang, jadikan sebagai current_chunk baru
                current_chunk = para
    
    # Yield chunk terakhir
    if current_chunk:
        full_chunk = previous_chunk_tail + current_chunk
        yield full_chunk.strip()


def _split_into_sentences(text: str) -> list[str]:
    """
    Memecah teks menjadi kalimat-kalimat dengan improved handling.
    
    Args:
        text (str): Teks yang akan dipecah.
        
    Returns:
        list[str]: Daftar kalimat hasil pemecahan.
    """
    import re
    
    # Split berdasarkan titik, tanda tanya, atau tanda seru
    # Pattern ini menangani kalimat yang dimulai dengan huruf kapital
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    
    # Fallback: jika tidak ada sentence boundary yang jelas dan teks sangat panjang
    if len(sentences) == 1 and len(text) > 1500:
        # Split berdasarkan kata dengan batasan panjang
        words = text.split()
        current = []
        result = []
        current_len = 0
        
        for word in words:
            current.append(word)
            current_len += len(word) + 1  # +1 untuk spasi
            if current_len >= 1000:
                result.append(" ".join(current))
                current = []
                current_len = 0
        
        if current:
            result.append(" ".join(current))
        
        return result
    
    # Bersihkan hasil splitting
    return [s.strip() for s in sentences if s.strip()]


def create_chunks_list(text: str, max_chars: int = 1500, overlap: int = 300) -> list[str]:
    """
    Versi berbasis list dari fungsi create_chunks().
    Mengubah generator menjadi list untuk kemudahan penggunaan.
    
    OPTIMIZATION: Updated default parameters to match create_chunks().
    
    Args:
        text (str): Teks input yang akan dipecah.
        max_chars (int, optional): Jumlah maksimum karakter per chunk (default: 1500).
        overlap (int, optional): Jumlah karakter tumpang tindih antar chunk (default: 300).
        
    Returns:
        list[str]: Daftar potongan teks hasil pemrosesan.
    """
    return list(create_chunks(text, max_chars, overlap))
