-- ===============================
-- SQLite global configuration
-- ===============================

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA temp_store = MEMORY;
PRAGMA cache_size = -20000;
PRAGMA busy_timeout = 5000;
