CREATE TABLE "decisions" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal TEXT,
    reasoning TEXT,
    decision_package_json TEXT,
    action_summary TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK(status IN ('PENDING', 'EXECUTED', 'REJECTED', 'FAILED')),
    executed_action TEXT,
    target_entity TEXT,
    action_result TEXT,
    confidence REAL,
    notes TEXT,
    rule_proposals_json TEXT,
    rule_cot TEXT,
    rule_status TEXT DEFAULT 'NONE' CHECK (rule_status IN ('NONE', 'IN_PROGRESS', 'RULES_READY', 'RULES_APPLIED', 'RULES_FAILED')),
    created_at TEXT NOT NULL 
);