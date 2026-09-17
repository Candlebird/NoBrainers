#!/usr/bin/env node
// Writer side, used by the orchestrator at retrospective time (playbook §5.8)
// instead of hand-editing docs/16-multiagent-workflow.md §13 / the archive
// file. Reads one JSON object from stdin:
//   { "date": "2026-09-11", "slug": "mixed-lanes",
//     "board_path": "docs/runs/2026-09-11-mixed-lanes.md",
//     "summary": "one paragraph", "retrospective": "full §12 answers text",
//     "lanes_landed": "89225b6 RTS Move-clear, ...", "lanes_parked": "..." }
// Usage: node ingest.js < entry.json
'use strict';

const { openDb } = require('./lib/db');

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

async function main() {
  const raw = await readStdin();
  let entry;
  try {
    entry = JSON.parse(raw);
  } catch (e) {
    console.error('ingest.js expects a single JSON object on stdin:', e.message);
    process.exit(1);
  }
  if (!entry.date || !entry.slug) {
    console.error('entry needs at least "date" and "slug"');
    process.exit(1);
  }

  const db = openDb();
  db.prepare(`
    INSERT INTO runs (date, slug, board_path, summary, retrospective, lanes_landed, lanes_parked)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(
    entry.date,
    entry.slug,
    entry.board_path || null,
    entry.summary || null,
    entry.retrospective || null,
    entry.lanes_landed || null,
    entry.lanes_parked || null
  );
  console.log(`logged: ${entry.date} — ${entry.slug}`);
}

main();
