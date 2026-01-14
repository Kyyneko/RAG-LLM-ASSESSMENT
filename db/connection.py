import os
import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """
    Membuat dan mengembalikan koneksi baru ke database MySQL.

    Fungsi ini menggunakan variabel lingkungan (.env) untuk membaca
    konfigurasi koneksi, serta memastikan pengelolaan sumber daya dilakukan
    secara aman menggunakan context manager.

    Returns:
        pymysql.connections.Connection: Objek koneksi database aktif.
    """
    password = os.getenv("DB_PASSWORD", "") or ""

    connection_params = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": password,
        "db": os.getenv("DB_NAME", "silab_db"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False
    }

    return pymysql.connect(**connection_params)
