CREATE TABLE ha_sensor_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    current_value REAL,
    attributes TEXT  -- JSON data (unit, friendly_name, etc.)
);