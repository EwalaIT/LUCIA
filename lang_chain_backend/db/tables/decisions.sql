CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    goal TEXT,
    reasoning TEXT,
    decision_package_json TEXT,
    action_summary TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'EXECUTED', 'REJECTED', 'FAILED')), -- PENDING, EXECUTED, REJECTED, FAILED
    executed_action TEXT,
    action_result TEXT,
    confidence REAL,
    context_id INTEGER,
    FOREIGN KEY (context_id) REFERENCES contexts(id)
);