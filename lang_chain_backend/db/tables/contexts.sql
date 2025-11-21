CREATE TABLE contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_type TEXT CHECK(context_type IN ('immediate', 'mid_term', 'long_term')),
    system_state TEXT,
    created_at TEXT NOT NULL
);