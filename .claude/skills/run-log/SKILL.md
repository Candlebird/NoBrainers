---
name: run-log
description: Look up past multi-agent run history for The Steel Caravan without loading full markdown docs into context — get the most recent run's retrospective, or full-text search all runs by keyword. Backed by a local SQLite database (.claude/skills/run-log/run-log.db).
argument-hint: "[latest [N] | search <keyword> | list]"
---

Query the run-log database instead of reading
`docs/16-multiagent-workflow.md` §13 or `docs/16-run-log-archive.md` — this
skill exists because those files cost real tokens to load in full just to
find one prior run's detail, while a database query returns only what's
needed.

Run one of these from the repo root (each is a single `Bash` call, no setup
needed — `node:sqlite` is a Node 22 built-in, nothing to install):

```
node .claude/skills/run-log/query.js latest        # most recent run, full text
node .claude/skills/run-log/query.js latest 3       # 3 most recent runs
node .claude/skills/run-log/query.js list           # every run, one line each
node .claude/skills/run-log/query.js search <word>  # full-text match + snippet
```

Use `list` first when you don't know what you're looking for — it's the
cheapest call (one line per run) and tells you whether `latest` or `search`
is the right next step. Use `search` with the specific term you actually
care about (a mechanic name, an asset path, "BLOCK", a lane slug) rather than
pulling `latest` repeatedly hoping to find it by scanning.

## Writing a new entry (orchestrator only, at retrospective time)

Playbook §5.8 (retrospective) inserts here instead of hand-editing the
markdown log. Pipe one JSON object to `ingest.js`:

```bash
node .claude/skills/run-log/ingest.js <<'EOF'
{
  "date": "2026-09-12",
  "slug": "some-lane-slug",
  "board_path": "docs/runs/2026-09-12-some-lane-slug.md",
  "summary": "one paragraph: what landed, what parked, headline numbers",
  "retrospective": "the full §12 question-by-question answers, as one string",
  "lanes_landed": "commit hash + mechanic, one per lane, semicolon-separated",
  "lanes_parked": "lane + reason, or \"none\""
}
EOF
```

Only `date` and `slug` are required; the rest default to null if omitted.
Rule changes a retrospective produces still go in the numbered sections of
`docs/16-multiagent-workflow.md` as before — only the log entry itself moved
to the database.

## Why a database instead of the markdown log

The markdown log (`docs/16-multiagent-workflow.md` §13 + its archive) is
read in full by whichever agent opens it, even to answer one narrow
question like "did the last run touch `BT_Enemy`?" — cost scales with total
log size, not with how much of it is actually relevant. The database
inverts that: `list` and `search` return only matching rows, and cost stays
flat as the log grows. `run-log.db` is a small binary file checked into the
repo like any other project data; there's nothing to install to read or
write it (`node:sqlite`'s `DatabaseSync`, built into Node 22, backs both
scripts, including FTS5 full-text search for `search`).
