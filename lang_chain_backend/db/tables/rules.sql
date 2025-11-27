CREATE TABLE "rules" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_decision_id INTEGER,
    rule_text TEXT NOT NULL,
    priority TEXT CHECK(priority IN ('immediate', 'mid_term', 'long_term')) NOT NULL,
    expires_at DATETIME,
    created_by TEXT CHECK(created_by IN ('decisor', 'evaluator', 'user')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT 1, 
    last_modified DATETIME,
    FOREIGN KEY (origin_decision_id) REFERENCES "decisions"(id)
)