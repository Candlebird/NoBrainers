// Shared DB helpers for the run-log skill. Uses Node's built-in node:sqlite
// (experimental as of Node 22, no npm install needed) — this environment has
// no working Python or sqlite3 CLI, so this is the zero-dependency option.
'use strict';

// Suppress the ExperimentalWarning noise on stderr; the module itself is fine.
const origEmit = process.emitWarning;
process.emitWarning = (warning, ...args) => {
  if (typeof warning === 'string' && warning.includes('SQLite')) return;
  return origEmit.call(process, warning, ...args);
};

const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const DB_PATH = path.join(__dirname, '..', 'run-log.db');

const SCHEMA = `
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  slug TEXT NOT NULL,
  board_path TEXT,
  summary TEXT,
  retrospective TEXT,
  lanes_landed TEXT,
  lanes_parked TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS runs_fts USING fts5(
  slug, summary, retrospective, lanes_landed, lanes_parked,
  content='runs', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS runs_ai AFTER INSERT ON runs BEGIN
  INSERT INTO runs_fts(rowid, slug, summary, retrospective, lanes_landed, lanes_parked)
  VALUES (new.id, new.slug, new.summary, new.retrospective, new.lanes_landed, new.lanes_parked);
END;

CREATE TRIGGER IF NOT EXISTS runs_ad AFTER DELETE ON runs BEGIN
  INSERT INTO runs_fts(runs_fts, rowid, slug, summary, retrospective, lanes_landed, lanes_parked)
  VALUES ('delete', old.id, old.slug, old.summary, old.retrospective, old.lanes_landed, old.lanes_parked);
END;
`;

function openDb() {
  const db = new DatabaseSync(DB_PATH);
  db.exec(SCHEMA);
  return db;
}

module.exports = { openDb, DB_PATH };
