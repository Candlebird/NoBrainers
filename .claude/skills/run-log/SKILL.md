---
name: run-log
description: Look up past multi-agent run history for No Brainers without loading full markdown docs into context — get the most recent run's retrospective, or full-text search all runs by keyword. Backed by a local SQLite database (.claude/skills/run-log/run-log.db).
argument-hint: "[latest [N] | search <keyword> | list]"
---

Query the run-log database instead of scanning old run/retrospective notes by
hand — this skill exists so looking up one prior run's detail doesn't cost
loading a whole markdown archive into context, when this project accumulates
one (there is no `docs/16-multiagent-workflow.md`-style archive here yet;
this database is the record going forward).

Run from the repo root (each is a single `Bash` call, no setup needed —
`node:sqlite` is a Node 22 built-in, nothing to install):

```
node .claude/skills/run-log/query.js latest        # most recent run, full text
node .claude/skills/run-log/query.js latest 3       # 3 most recent runs
node .claude/skills/run-log/query.js list           # every run, one line each
node .claude/skills/run-log/query.js search <word>  # full-text match + snippet
```

Use `list` first if you don't know what you're looking for — it's the
cheapest call (one line per run) and tells you whether `latest` or `search`
is the right next step. Use `search` for a specific term you actually care
about (a mechanic name, asset path, "BLOCK", a lane slug) rather than
pulling `latest` repeatedly hoping to find it by scanning.

## Writing a new entry (retrospective time)

Pipe one JSON object into `ingest.js` instead of hand-editing a markdown log:

```bash
node .claude/skills/run-log/ingest.js <<'EOF'
{
  "date": "2026-09-12",
  "slug": "some-lane-slug",
  "board_path": "docs/runs/2026-09-12-some-lane-slug.md",
  "summary": "one paragraph: landed, parked, headline numbers",
  "retrospective": "the full retrospective question-by-question answers, one string",
  "lanes_landed": "commit hash + mechanic, one per lane, semicolon-separated",
  "lanes_parked": "lane + reason, or \"none\""
}
EOF
```

Only `date` and `slug` are required; the rest can be empty strings if not applicable to the run.

`run-log.db` is a small binary file checked into the repo like any other project data; there's nothing to install to read or write it (`node:sqlite`'s `DatabaseSync`, built into Node 22, backs both scripts, including FTS5 full-text search for `search`).
