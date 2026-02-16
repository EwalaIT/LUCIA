CREATE TABLE "entity" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER,
    entity_id VARCHAR(150) UNIQUE NOT NULL,
    friendly_name VARCHAR(150),
    unit VARCHAR(10),
    min_value FLOAT,
    max_value FLOAT,
    step FLOAT,
    mode VARCHAR(50),
    selected BOOLEAN DEFAULT 0,
    last_state VARCHAR(50),
    last_updated DATETIME,
    FOREIGN KEY (device_id) REFERENCES device(id) ON DELETE SET NULL
);