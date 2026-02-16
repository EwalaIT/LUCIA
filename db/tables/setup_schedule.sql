CREATE TABLE "setup_schedule" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setup_id INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    days VARCHAR(10) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    temp_min FLOAT NOT NULL,
    temp_max FLOAT NOT NULL,
    active BOOLEAN DEFAULT 1,
    FOREIGN KEY (setup_id) REFERENCES setup(id) ON DELETE CASCADE,
    FOREIGN KEY (zone_id) REFERENCES zone(id) ON DELETE CASCADE
)