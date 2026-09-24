# CLAUDE.md — Unreal Engine Automation Context

## Stack & Environment

- **Engine:** 5.7
- **MCP:** `Plugins/Monolith/Binaries/monolith_proxy.exe` (Monolith plugin, with namespace tools for `blueprint`, `material`, `editor`, `cppreflect`, `network`, and so on).
- **Default session model:** Sonnet (set in `.claude/settings.json`). The main session runs the orchestration: reading plans and reports and dispatching agents. That work doesn't need Opus, and running it on Opus is the most expensive part of a long run. Only `ue-architect` runs on Opus. Switch with `/model opus` for a session that needs it.

## Task List

- **Start here:** `docs/ParentTaskList.md` is the index of build phases and says which phase is active. Read it before picking up work so you aren't guessing the phase from git history or `Content/`. Each phase's detailed tasks live in its own `docs/PHASE_<N>_TASKLIST.md`. The phase file is authoritative when it disagrees with the index.

## Bug Tracking

- **`docs/BUGS.md` is the single tracker for unresolved bugs, known issues, and known limitations.** When you find one during implementation, add an entry there (Area/Repro/Actual/Expected/Status). At the place you found it (e.g. a phase tasklist STATUS NOTE), leave only a pointer: `See docs/BUGS.md — "<entry title>."` Don't write the full description there.

## Execution Rules

- **Never echo raw JSON.** Don't repeat full JSON payloads from Monolith/MCP tools. Summarize them in brief bullets.
- **Single-action confirmation.** After a write or spawn in Unreal, state only the properties changed or objects created. Don't narrate every tool call.
- **Limited testing capabilities.** When a change needs in-game testing, stop and tell me briefly what to test before continuing.
- **Short subagent reports.** Builders report in the fixed format in "Builder report format" below. Expand into detail only when something went wrong (a failure, a BLOCK, an ambiguous case) or when asked.

## Version Control

- **Gotcha: a checkout or merge can half-fail while the editor is open.** While the Unreal Editor holds modified `.uasset` files open, Windows file locking stops git from unlinking or overwriting them (`unable to unlink ... Invalid argument`). Git doesn't fail atomically here. It checks out every file it *can* write, leaves the locked ones as they were, and only then reports the error. The working tree ends up mixing both branches' content, and `git status` alone can't show which files are wrong. After an unlink error, don't assume unmentioned files are safe. Run `git diff <target-branch> --stat` and fix any unexpected difference with `git checkout <target-branch> -- <path>`, file by file, before committing. That command is safe even mid-mess, because it only touches the paths you list.

## Subagents

### Roles

| Agent | Model | Job |
|---|---|---|
| `ue-scout` | Haiku | Read-only fact gathering for large features: paths, signatures, graph summaries. Hands a fact sheet to the architect. |
| `ue-architect` | Opus 5.5 | Read-only planner. Makes every design decision and outputs dispatch-ready task packets. |
| `ue-blueprint-builder` | Sonnet | Blueprint graphs, DataAssets, DataTables, GAS, behavior trees. |
| `ue-cpp-builder` | Sonnet | C++ under `Source/GASDocumentation/`, plus compiling it. |
| `ue-ui-builder` | Sonnet | WidgetBlueprints, plus the light graph wiring that follows a widget-tree change. |
| `ue-content-builder` | Sonnet | Materials, meshes, Niagara, audio, animation, level sequences. |
| `ue-test-writer` | Sonnet | New `Test_*` checks in `Content/Tests/Automation/`. |
| `ue-test-runner` | Haiku | Runs the test bed and reports PASS/FAIL. |
| `ue-vision-keeper` | Sonnet | Read-only design-alignment review: `ALIGNED` / `DRIFT` / `BLOCK`. |
| `ue-git-manager` | Haiku | Commits, pushes, PRs. |

### Choosing the path: match the effort to the change

- **Small change** (one asset, no Blueprint-vs-C++ question, e.g. a bug fix or tweak): dispatch the right builder directly with a packet you write yourself, using the architect's packet template (`.claude/agents/ue-architect.md`). Skip the scout, the architect, and both vision gates.
- **Feature** (2+ assets, or it needs a Blueprint-vs-C++ decision): `ue-architect` → vision gate 1 on the plan → builders → `ue-test-writer` / `ue-test-runner` → vision gate 2 on the landed change → `ue-git-manager`.
- **Large feature** (4+ assets, or it touches systems whose assets you can't name yet): dispatch `ue-scout` first, then pass its fact sheet to `ue-architect` so Opus reasons over gathered facts instead of doing the lookups itself. Then follow the feature path.

### Dispatching the plan

- **Dispatch the architect's task packets as written.** Each one is self-contained: it has every name, type, and signature decided, so a Sonnet builder can run it without design calls. Paste the packet verbatim, add the reports of any tasks it depends on, and add nothing else.
- **One builder call per asset per dependency step.** Each call has a fixed cost: the system prompt, the tool schemas, and a cold read of the asset. So consecutive changes to the same asset go in one call. Split into separate calls only when something must happen in between (e.g. a C++ header change the Blueprint depends on), or when the assets are different. Never hand one agent a whole multi-asset spec. A 7-step spec in one call once ran to about 1M tokens.
- **Run independent tasks in parallel.** Tasks the architect marks parallel (no shared assets, no dependency) go out together in one message.
- **Every graph edit ends with a Vesper pass by the builder that made it.** `ue-blueprint-builder`, `ue-ui-builder`, and `ue-test-writer` run `blueprint.auto_layout` with `formatter: 'vesper'` on each graph they edited, then compile and save. They report the result in the `VESPER` field. No separate cleanup agent is needed. If a report shows `VESPER: failed` or the field is missing, re-dispatch only that asset's layout step to the same builder.

### When a task fails

1. **Retry once:** re-dispatch the same packet to the same builder, adding its failure report (error text and what landed).
2. **If it fails again, escalate only that task:** send `ue-architect` the task packet, both failure reports, and the current state of the assets, and ask for a replacement packet for that task alone. Never re-plan the whole feature because one task failed.
3. **If the replacement also fails,** stop and report to me.

### Builder report format

Every builder ends with exactly this block. Leave a field out only when it doesn't apply.

```
TASK: <task number/title from the packet>
TOUCHED: <asset or file paths, (new)/(edit)>
CHANGES: <short list: functions/variables/nodes/widgets/properties added or changed>
COMPILE: ok | <error summary>
VESPER: <graphs formatted> | failed: <reason> | n/a
SAVED: yes | no
USER TEST: <what to test in-game> | none
NOTES: <gotchas found, deviations from the packet, blockers> | none
```

### Token rules

- **Discover once.** Don't send several agents to scan the same area. The scout or the architect does it once, and the packets carry the findings forward.
- **Every agent starts cold.** A dispatched agent can't see this conversation. Everything it needs goes in the packet: paths, prior findings, the exact ask.
- **Scope tightly.** Give exact asset paths and names. No project-wide scans.
- **Background agents: wait, don't guess.** Wait for the actual report. Never predict or invent it.
- **Measure.** At the end of a feature run, log it with the `run-log` skill. In `summary`, put the total tokens for each agent call (from its completion notification) and the run total, so runs can be compared over time.

## MCP & Monolith Usage Rules

- **Param lookup.** To get an action's exact params, grep `.claude/monolith/SCHEMAS.md` for `^## <ns>.<action> ` with `-A 12`. Never Read the file whole. After a Monolith update, regenerate it with `.claude/monolith/build_schema_sheet.py`. A PreToolUse hook (`fix_params.py`) auto-corrects common param-name mistakes. A PostToolUse hook (`compact_output.py`) compacts `get_graph_data`/`get_node_details` output (set `MONOLITH_RAW=1` to disable it).
- **Domain namespaces.** Prefer Monolith's namespace tools (`blueprint`, `material`, `editor`, `cppreflect`, `network`) over generic fallback actions.
- **Scope queries tightly.** Always give explicit package paths (e.g. `/Game/Blueprints/Core/BP_PlayerCharacter`) or exact Actor classes.
- **Error self-correction.** If a call fails on invalid arguments or a missing path, check the schema, fix the payload, and retry once before reporting to me.
- **Graph layout: Vesper.** Call `blueprint.auto_layout` with `asset_path`, `graph_name`, and `formatter: 'vesper'`. That routes through the Vesper Node Cleaner plugin (`Plugins/VesperNodeCleaner/`) via `Plugins/Monolith/Source/MonolithVesperBridge/`. It lays graphs out much better than the default `'auto'`/`'monolith'` formatter, so always name it explicitly.
  - **Scope:** `layout_mode` only matters as `'selected'` with `node_ids`. Any other value formats the whole graph, since Vesper doesn't pin already-placed nodes.
  - **Re-running is safe:** its generated comment boxes are tagged and regenerated each run, and your own comments are kept.
  - **Node sizes:** Monolith can't open an asset in the editor. If the graph is already open, Vesper measures real node sizes. If not, it estimates them from pin counts, which is fine for routine passes.
  - **Always recompile after it runs.**
  - **More detail:** the rules, the `[VesperNodeCleaner]` ini tunables, and the rebuild script (`.claude/monolith/rebuild_editor.ps1`) are in `docs/VESPER_LAYOUT.md`.
