import sqlite3
from pathlib import Path
import os

DB_PATH = Path(os.getenv("DB_PATH", "/data/db/lucia.db"))
SQL_DIR = Path("/app/db/sql")

def init_db():
    # Crear carpeta si no existe
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Conectamos a la base, si existe no se sobreescribe
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    # Ejecutamos solo si la base está vacía
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company';")
    if cursor.fetchone() is None:
        print("Inicializando base de datos...")
        for sql_file in sorted((SQL_DIR / "tables").glob("*.sql")):
            with open(sql_file) as f:
                conn.executescript(f.read())
        print("✅ BBDD inicializada.")
    else:
        print("⚡ BBDD ya existente, no se vuelve a crear.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
