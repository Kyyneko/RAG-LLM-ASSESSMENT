# db/connection.py
import os
import pymysql
from dotenv import load_dotenv

# Load konfigurasi dari file .env
load_dotenv()


# ENHANCEMENT: SQL untuk membuat indexes yang optimal
RECOMMENDED_INDEXES = """
-- Indexes untuk optimasi performa query

CREATE INDEX IF NOT EXISTS idx_sessions_subject_id ON sessions(subject_id);
CREATE INDEX IF NOT EXISTS idx_rag_docs_subject_indexed ON rag_source_documents(subject_id, is_indexed);
CREATE INDEX IF NOT EXISTS idx_rag_docs_hash ON rag_source_documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_assessments_session_id ON assessments(session_id);
CREATE INDEX IF NOT EXISTS idx_assessments_subject_id ON assessments(subject_id);
CREATE INDEX IF NOT EXISTS idx_rag_docs_composite ON rag_source_documents(subject_id, is_indexed, created_at);
"""

def setup_database_indexes():
    """
    Menjalankan pembuatan indexes yang direkomendasikan.
    Panggil fungsi ini saat setup awal database.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        for statement in RECOMMENDED_INDEXES.split(';'):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ Database indexes created successfully")
    except Exception as e:
        print(f"⚠️ Error creating indexes: {str(e)}")


def get_connection():
    """
    Membuat dan mengembalikan koneksi baru ke database MySQL.

    Fungsi ini menggunakan variabel lingkungan (.env) untuk membaca
    konfigurasi koneksi, serta memastikan pengelolaan sumber daya dilakukan
    secara aman menggunakan context manager.

    Returns:
        pymysql.connections.Connection: Objek koneksi database aktif.
    """
    password = os.getenv("MYSQL_PASSWORD", "") or ""

    connection_params = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": password,
        "db": os.getenv("MYSQL_DB", "silab_db"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False
    }

    return pymysql.connect(**connection_params)


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    Menjalankan perintah SQL dengan penanganan kesalahan dan manajemen transaksi.

    Args:
        query (str): Query SQL yang akan dijalankan.
        params (tuple | list, optional): Parameter untuk query (default: None).
        fetch_one (bool, optional): Jika True, mengembalikan satu baris hasil query.
        fetch_all (bool, optional): Jika True, mengembalikan semua hasil query.

    Returns:
        Any: Hasil eksekusi query.
              - Jika `fetch_one` = True → dict baris tunggal.
              - Jika `fetch_all` = True → list of dicts.
              - Jika tidak keduanya → lastrowid untuk operasi INSERT.

    Raises:
        Exception: Jika terjadi kesalahan saat menjalankan query.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())

            if fetch_one:
                result = cur.fetchone()
            elif fetch_all:
                result = cur.fetchall()
            else:
                result = cur.lastrowid

            conn.commit()
            return result

    except Exception as e:
        conn.rollback()
        print(f"Database error: {str(e)}")
        raise e

    finally:
        conn.close()
