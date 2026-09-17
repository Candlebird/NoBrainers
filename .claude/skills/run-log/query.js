#!/usr/bin/env node
// Read-only CLI an agent runs to check the run log without loading
// docs/16-multiagent-workflow.md's log section or the archive file into
// context. Usage:
//   node query.js latest [N]        most recent N runs (default 1), full text
//   node query.js list              date | slug | one-line summary, all runs
//   node query.js search <keyword>  FTS5 match over slug/summary/retro/lanes
'use strict';

const { openDb } = require('./lib/db');

function printRun(row) {
  console.log(`### ${row.date} — ${row.slug}  (board: ${row.board_path || 'n/a'})`);
  if (row.lanes_landed) console.log(`Landed: ${row.lanes_landed}`);
  if (row.lanes_parked) console.log(`Parked: ${row.lanes_parked}`);
  if (row.summary) console.log(`\n${row.summary}`);
  if (row.retrospective) console.log(`\nRetrospective:\n${row.retrospective}`);
  console.log('');
}

function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  const db = openDb();

  if (cmd === 'latest') {
    const n = Number(rest[0]) || 1;
    const rows = db.prepare(
      'SELECT * FROM runs ORDER BY date DESC, id DESC LIMIT ?'
    ).all(n);
    if (rows.length === 0) { console.log('(run log is empty)'); return; }
    rows.forEach(printRun);
    return;
  }

  if (cmd === 'list') {
    const rows = db.prepare(
      'SELECT date, slug, summary FROM runs ORDER BY date DESC, id DESC'
    ).all();
    if (rows.length === 0) { console.log('(run log is empty)'); return; }
    for (const r of rows) {
      const oneLine = (r.summary || '').split('\n')[0].slice(0, 100);
      console.log(`${r.date}\t${r.slug}\t${oneLine}`);
    }
    return;
  }

  if (cmd === 'search') {
    const keyword = rest.join(' ').trim();
    if (!keyword) { console.error('usage: node query.js search <keyword>'); process.exit(1); }
    const rows = db.prepare(`
      SELECT runs.*, snippet(runs_fts, -1, '**', '**', '…', 20) AS snip
      FROM runs_fts JOIN runs ON runs.id = runs_fts.rowid
      WHERE runs_fts MATCH ?
      ORDER BY rank
    `).all(keyword);
    if (rows.length === 0) { console.log(`(no matches for "${keyword}")`); return; }
    for (const r of rows) {
      console.log(`### ${r.date} — ${r.slug}  (board: ${r.board_path || 'n/a'})`);
      console.log(r.snip);
      console.log('');
    }
    return;
  }

  console.error('usage: node query.js <latest [N] | list | search <keyword>>');
  process.exit(1);
}

main();
