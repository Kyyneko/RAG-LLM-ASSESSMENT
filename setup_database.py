# setup_database.py

from db.connection import setup_database_indexes

if __name__ == "__main__":
    print("Setting up database indexes...")
    setup_database_indexes()
    print("Done!")
