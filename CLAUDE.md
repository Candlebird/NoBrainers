# CLAUDE.md — Unreal Engine Automation Context

## Stack & Environment

- **Engine:** 5.7
- **MCP:** `Plugins/Monolith/Binaries/monolith_proxy.exe` (Monolith plugin — namespace tools for `blueprint`, `material`, `editor`, `cppreflect`, `network`, etc.)

## Task List

- **Start here:** `docs/ParentTaskList.md` is the index of build phases and states which phase is currently active — read it before picking up work so you aren't guessing the phase from git history or Content/. Each phase's detailed task breakdown lives in its own `docs/PHASE_<N>_TASKLIST.md`.

## Execution Rules

- **Never Echo Raw JSON:** Do not repeat full JSON payloads returned by Monolith/MCP tools. Summarize tool outputs in brief bullet points.
- **Single-Action Confirmation:** When executing write/spawn commands in Unreal Engine, state only the changed properties or created objects — not a full narration of every tool call.
- **Limited Testing Capabilities:** Testing capabilities here are limited. Whenever a change requires in-game testing, stop and tell me briefly what you need me to test before continuing.
- **Subagent reports stay short:** A dispatched agent's report back to the orchestrator (or me) should default to the shortest form that still carries every fact the reader needs to act — a builder's report needs its `TOUCHED`/`COMPILE`/`SAVED` fields, not a narrated walkthrough of every tool call. Expand into full detail only when something actually went wrong (a BLOCK, a failure, an ambiguous case) or when explicitly asked.

## Version Control

- **Gotcha:** `git checkout <branch>` / `git merge` can silently half-fail while the Unreal Editor has modified `.uasset` files open. Windows file locking means git can't unlink/overwrite a `.uasset` the editor currently holds a handle on (`unable to unlink ... Invalid argument`) — git does **not** fail atomically here: it happily checks out every file it *can* write, leaves locked ones exactly as they were before the checkout, and only then reports the error and aborts. The result is a working tree silently mixing old-branch and new-branch content, indistinguishable from a clean state via `git status` alone (some files show unexpectedly "modified"/"untracked" — fine, those are just locked ones stuck on newer content; but *other* files may have silently reverted to the older branch's content with no warning). If a checkout/merge reports an unlink error, don't assume the files it didn't mention are safe — diff the working tree against the branch you meant to land on (`git diff <target-branch> --stat`) and reconcile any unexpected differences (`git checkout <target-branch> -- <path>` per-file works fine even mid-mess, since it only touches the exact paths listed) before committing anything.

## Subagents

- **UI/UMG work → `ue-ui-builder`.** Any task touching a WidgetBlueprint (widget trees, layout, custom widget instancing via `ui.add_custom_widget`, or light Blueprint-graph wiring that follows a widget-tree change) should go to this dedicated agent rather than `ue-content-builder` or `ue-blueprint-builder`.
- **Design-alignment review → `ue-vision-keeper`.** Read-only reviewer that grades a plan or landed change against project design docs and returns `ALIGNED`/`DRIFT`/`BLOCK`. Point it at whatever design docs this project settles on.

### Token-Efficient Agent Usage

When dispatching multiple agents (whether in parallel or across a multi-step run), the biggest token drains are redundant discovery and verbose reporting. A few standing rules to avoid that:

- **Share discovery once, don't re-scan per task.** If several agents each need to understand the same area of the codebase, don't dispatch one full-scan agent per task in parallel — that burns tokens on redundant discovery. Instead dispatch a single discovery/architecture agent first, have it return a plan covering all the tasks, then only dispatch follow-up agents for a specific task if it needs more — and point that follow-up at the prior plan so it reuses the existing discovery instead of re-scanning the codebase.
- **Every agent starts cold.** A dispatched agent has no memory of this conversation. Everything it needs (file paths, prior findings, the exact ask) must be handed to it explicitly in its dispatch packet — don't assume it can infer context the way a continued conversation would.
- **Scope queries tightly.** Avoid project-wide scans. Supply explicit paths or exact target names whenever a tool or agent call takes them, rather than letting it search broadly.
- **Background long-running agents; don't poll or guess.** Once a builder/agent is dispatched in the background, wait for its actual report rather than fabricating or predicting what it will say.
- **Keep subagent reports short by default** (see Execution Rules above) — this matters even more at scale, since a wave of five verbose agent reports costs five times as much as one.

## MCP & Monolith Usage Rules

- **Domain Namespaces:** Always prefer Monolith's namespace tools (`blueprint`, `material`, `editor`, `cppreflect`, `network`) over generic fallback actions.
- **Scope Queries Tightly:** Avoid project-wide scans. Always supply explicit package paths (e.g., `/Game/Blueprints/Core/BP_PlayerCharacter`) or target exact Actor classes in scene queries.
- **Error Self-Correction:** If a tool call fails due to invalid arguments or missing paths, inspect the tool schema, fix the payload, and attempt one retry before reporting the issue to me.
- **Node Formatting/Readability:** To auto-layout a Blueprint graph for human readability, call `blueprint.auto_layout` and pass `formatter: 'vesper'` to route through the Vesper Node Cleaner plugin (`Plugins/VesperNodeCleaner/`, a paid Fab/Marketplace plugin) via Monolith's bridge (`Plugins/Monolith/Source/MonolithVesperBridge/`). This is a distinct code path from the tool's default `formatter: 'auto'`/`'monolith'` built-in Sugiyama layout or the `'blueprint_assist'` option — prefer `'vesper'` explicitly when the goal is a clean, human-readable graph, since it gives noticeably better real-world layout results than the built-in formatter. Vesper has no `layout_mode` concept (no pinning of already-placed nodes the way `'new_only'` does on the built-in formatter): passing `layout_mode='selected'` with `node_ids` filters which nodes it touches, but `'all'`/`'new_only'` both just format the whole graph.
