"""
Database initializer for the project.

- Synchronously runs all .sql scripts found in db/tables/
  (these scripts should be written using CREATE TABLE IF NOT EXISTS to be idempotent).
- Exposes get_connection(), init_db() and verify_tables().
- Uses sqlite3.Row for row factory so callers can access columns by name.
"""
import sqlite3
import logging
from typing import List
from pathlib import Path
from datetime import datetime

# === Paths ===
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "agent_memory.db"
TABLES_DIR = BASE_DIR / "tables"

# === Configure Logging ===
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("DB_INIT")


# === Connection Helper ===
def get_connection():
    """
    Return a persistent connection to the SQLite database.
    Creates the database file if it doesn't exist.
    """
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        logger.debug(f"Connected to database: {DB_PATH}")
        return conn
    except sqlite3.Error as e:
        logger.exception(f"Failed to connect to database: {e}")
        raise

                       
# === Initialization Function ===
def init_db():
    """
    Initialize the SQLite database by executing all .sql files in /tables.
    Adds detailed logging and error handling.
    """
    db_exists = DB_PATH.exists()

    if db_exists:
        logger.info("📁 Database already exists → Skipping creation of tables.")
        verify_tables()
        return

    logger.info("🚀 Database not found. Creating fresh DB and running SQL scripts...")
    start_time = datetime.now()

    # Validate tables directory
    if not TABLES_DIR.exists() or not TABLES_DIR.is_dir():
        logger.error("❌ Tables directory not found: %s", TABLES_DIR)
        return
    
    sql_files: List[Path] = sorted(TABLES_DIR.glob("*.sql"))
    if not sql_files:
        logger.warning("⚠️ No .sql files found in directory: %s", TABLES_DIR)
        return

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        for sql_file in sql_files:
            logger.info("📄 Processing SQL file: %s", sql_file.name)
            try:
                sql_script = sql_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.exception("Failed to read SQL file %s: %s", sql_file, e)
                raise

            try:
                cursor.executescript(sql_script)
                logger.info("✅ Executed: %s", sql_file.name)
            except sqlite3.Error as e:
                logger.error("❌ Error executing %s: %s", sql_file.name, e)
                conn.rollback()
                raise

        conn.commit()
        logger.info("🎯 All SQL scripts executed successfully!")
    except Exception as e:
        logger.exception("Critical error during DB initialization: %s", e)
        # Let exception propagate to caller if desired
        raise
    finally:
        if conn:
            try:
                conn.close()
                logger.debug("Database connection closed.")
            except Exception:
                logger.exception("Error closing database connection.")
        elapsed = datetime.now() - start_time
        logger.info("⏱ Initialization completed in %.2fs", elapsed.total_seconds())


# === Utility: Check Tables ===
def verify_tables():
    """
    Verify that all expected tables exist in the database.
    """
    try:
        sql_files = sorted(TABLES_DIR.glob("*.sql"))
    except Exception:
        sql_files = []

    expected_tables = [p.stem for p in sql_files]  # assumes file name equals table name or descriptive

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing = [row["name"] for row in cursor.fetchall()]

        missing = [t for t in expected_tables if t not in existing]
        if missing:
            logger.warning("⚠️ Missing tables (based on .sql filenames): %s", missing)
        else:
            logger.info("✅ All expected tables appear in the database.")
        return existing
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        init_db()
        tbls = verify_tables()
        logger.info("Existing DB tables: %s", tbls)
    except Exception as e:
        logger.exception("Initialization failed: %s", e)
        raise
