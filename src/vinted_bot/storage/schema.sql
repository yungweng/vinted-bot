CREATE TABLE IF NOT EXISTS app_config (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS searches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  url TEXT NOT NULL,
  ja_prompt TEXT,
  nein_prompt TEXT,
  vielleicht_prompt TEXT,
  sonderregeln TEXT,
  max_entries INTEGER,
  model TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  error TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_searches_created_at ON searches(created_at DESC);

CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vinted_id INTEGER NOT NULL,
  search_id INTEGER NOT NULL,
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
  url TEXT,
  description TEXT,
  ocr_text TEXT,
  fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(search_id, vinted_id),
  FOREIGN KEY (search_id) REFERENCES searches(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_items_search ON items(search_id);
CREATE INDEX IF NOT EXISTS idx_items_fetched_at ON items(fetched_at DESC);

CREATE TABLE IF NOT EXISTS images (
  item_id INTEGER NOT NULL,
  idx INTEGER NOT NULL,
  local_path TEXT NOT NULL,
  PRIMARY KEY (item_id, idx),
  FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS classifications (
  item_id INTEGER PRIMARY KEY,
  verdict TEXT NOT NULL,
  reason TEXT,
  model TEXT,
  classified_at TEXT,
  raw_response TEXT,
  FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_classifications_verdict ON classifications(verdict);

CREATE TABLE IF NOT EXISTS user_actions (
  item_id INTEGER PRIMARY KEY,
  action TEXT,
  decided_at TEXT,
  FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);
