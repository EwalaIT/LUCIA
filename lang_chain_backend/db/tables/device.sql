CREATE TABLE "device" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ha_device_id VARCHAR(150),
    zone_id INTEGER,
    name VARCHAR(150) NOT NULL,
    type VARCHAR(50),
    last_sync DATETIME,
    FOREIGN KEY (zone_id) REFERENCES zone(id) ON DELETE SET NULL
);