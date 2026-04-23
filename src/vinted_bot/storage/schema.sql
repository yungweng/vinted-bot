CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY,
  title TEXT,
  brand TEXT,
  size TEXT,
  condition TEXT,
  color TEXT,
  price REAL,
  buyer_protection REAL,
  shipping REAL,
  currency TEXT,
  uploaded_at TEXT,
  url TEXT UNIQUE,
  description TEXT,
  ocr_text TEXT,
  fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS images (
  item_id INTEGER NOT NULL,
  idx INTEGER NOT NULL,
  local_path TEXT NOT NULL,
  PRIMARY KEY (item_id, idx),
  FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS classifications (
  item_id INTEGER PRIMARY KEY,
  verdict TEXT NOT NULL,
  reason TEXT,
  model TEXT,
  classified_at TEXT,
  raw_response TEXT,
  FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS user_actions (
  item_id INTEGER PRIMARY KEY,
  action TEXT,
  decided_at TEXT,
  FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE INDEX IF NOT EXISTS idx_classifications_verdict ON classifications(verdict);
CREATE INDEX IF NOT EXISTS idx_items_fetched_at ON items(fetched_at DESC);
