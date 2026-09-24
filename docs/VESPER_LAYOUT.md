# Vesper Clean Graph — Layout Rules

This page describes what the VesperNodeCleaner plugin (`Plugins/VesperNodeCleaner/`) does when it formats a Blueprint graph. The implementation is in `Private/VesperGraphLayout.cpp`.

## Ways to run it

- **Blueprint editor toolbar → "Clean Graph"**, or right-click → **Vesper: Clean Graph**. Formats the selected nodes, or the whole graph when fewer than 2 nodes are selected. It is one undo step (Ctrl+Z).
- **Monolith:** `blueprint_query auto_layout` with `formatter: 'vesper'`. `layout_mode: 'selected'` with `node_ids` limits it to those nodes; any other mode formats the whole graph. It goes through `Plugins/Monolith/Source/MonolithVesperBridge/`.
- **Right-click → Vesper: Auto-Fit Comment Box** resizes the selected comments to fit what is inside them.

If the graph is open in an editor tab, Vesper measures each node's real on-screen size and pin positions. If not (for example, a Monolith call on a closed asset), it estimates them from pin counts and title lengths. For the most accurate result through Monolith, open the Blueprint on the graph you are formatting first.

## Rules

1. **Function blocks.** Every connected set of exec wires is one block, for example an event and everything it runs. A pure node (no exec pins) belongs to the first exec node it feeds, in exec order. Pure nodes that feed no exec node form their own "data" blocks.
2. **Exec wires are straight.** Each exec node is placed so its entry pin is at the same height as the output pin that feeds it.
3. **Branches get their own rows.** The first exec output continues on the same row. Every other output (Branch False, Sequence Then 1+, Switch cases, ...) starts a new straight row below everything placed so far.
4. **Inputs stack below their node.** A node's data inputs are laid out to its left, in pin order:
   - The first input is placed so its wire is straight.
   - Each later input goes directly under the whole chain of the previous one, `StackGap` apart.
   - The same rule applies recursively up every chain, so the nodes feeding the first input line up with it.
   - Pure nodes with several inputs (Append, math, Make Struct, ...) follow the same rule.
5. **Below bias.** Inputs never go above their node's exec wire. An input of a pure node may rise at most `AboveTolerance` above that node's top edge. That is the only case where something sits above its consumer, and only to keep a first wire straight.
6. **Shared getters.** A plain self-variable getter read by several exec nodes gets one copy per exec node, so every read has a short straight wire. Pure function calls are never duplicated.
7. **Grouping.** Blocks are grouped when at least 2 match one of these:
   - Input events → **Input Events**
   - BeginPlay / Tick / EndPlay / Construct / ... → **Lifecycle Events**
   - Overlap / Hit events → **Collision & Overlap Events**
   - Other engine event overrides → **Event Overrides**
   - Custom events sharing a name prefix (`Shop_Open`, `Shop_Close`, or `ShopOpen`, `ShopClose`) → **Shop Events**
   - Blocks that mostly touch the same variables or functions (≥50% overlap) → **Uses <Member>**

   Single loose nodes and data-only blocks collect into **Unconnected Nodes**, placed last.
8. **Comment boxes.**
   - A solo block gets a titled comment. The title is the event name, or the function name for a function graph's entry.
   - A group gets an outer comment titled `<Group> (N)`, and each block inside it gets a smaller inner comment.
   - Blocks and groups stack top to bottom in their original top-to-bottom order.
   - **Function and macro graphs get no generated comments.** The graph's name already says what the box would. Blocks are still laid out and grouped the same way. Comments left by earlier runs are removed, and your own comments are kept.
9. **Re-running is safe.**
   - Generated comments are tagged, so each run deletes and regenerates them.
   - Your own comments are never deleted. If one of your comments wraps exactly one block, including its event, Vesper uses it as that block's frame and keeps your title and color.
   - Any other comment of yours is resized to fit the nodes it wrapped before the run.

## Tuning (`Config/DefaultEditor.ini`)

Every value is optional. The defaults are shown. Changes take effect on the next Clean Graph with no restart, because the settings are read on every run.

```ini
[VesperNodeCleaner]
ExecGap=50              ; gap between exec nodes (room for inputs is added on top)
DataGap=32              ; gap between an input node and the node it feeds
StackGap=14             ; vertical gap between stacked inputs
BranchRowGap=36         ; vertical gap between branch rows
ExecLaneClearance=8     ; inputs stay this far below the exec wire
AboveTolerance=12       ; how far a straight first input may rise above a pure node
BlockGap=100            ; gap between blocks and groups
GroupInnerGap=40        ; gap between blocks inside a group
CommentPadding=28
CommentFontSize=18
InnerCommentFontSize=14
bGenerateComments=True
bInnerGroupComments=True
bGroupSimilar=True
bDuplicateSharedGetters=True
SingleColor=(R=0.10,G=0.28,B=0.50,A=1.0)
GroupColor=(R=0.38,G=0.20,B=0.52,A=1.0)
InnerColor=(R=0.16,G=0.16,B=0.18,A=1.0)
LooseColor=(R=0.30,G=0.30,B=0.30,A=1.0)
```

## Rebuilding after plugin changes

Changes to plugin headers need a full UBT build with the editor closed. Run:

```
powershell -ExecutionPolicy Bypass -File .claude/monolith/rebuild_editor.ps1          # close, build, relaunch
powershell -ExecutionPolicy Bypass -File .claude/monolith/rebuild_editor.ps1 -NoLaunch
powershell -ExecutionPolicy Bypass -File .claude/monolith/rebuild_editor.ps1 -Clean   # also wipes the plugin's Binaries/Intermediate
```

The script tries to close the editor normally and force-closes it after 60 seconds, so save your work first.
