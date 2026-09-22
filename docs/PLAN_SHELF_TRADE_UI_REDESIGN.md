# Plan: Side-by-Side Shelf Trade UI (Inventory + Shelf, Click-to-Transfer Both Ways)

**Status:** Planned, not yet implemented. Written for a fresh Claude Code session to
pick up and execute — it has no memory of the investigation that produced this plan,
so this document is self-contained.

**Origin:** User reported the shelf UI (`WBP_ShelfPanel`) opened but its slot buttons
did nothing when clicked. Root cause (already fixed, see `docs/BUGS.md`): a zero-size
root panel on `WBP_ShelfSlot`. Once slots became visible, the real UX problem surfaced:
the Inventory UI and Shelf UI are two separate, mutually-exclusive full-screen windows
that are never open at the same time, so the existing "select an inventory item, then
click a shelf slot" flow has no way to happen — you'd have to close one window to open
the other. The user wants both panels open simultaneously (inventory on the left, shelf
on the right) so transfers can happen with two clicks in either direction, and wants the
old single-window system cleaned up as part of the change.

---

## 1. Current System (as of this writing — verify unchanged before starting)

### PlayerController (`/Game/Core/PlayerControllers/BP_PlayerController_ZombieStore`)
- `InventoryWidget: WBP_Inventory_C`, `ShelfWidget: WBP_ShelfPanel_C` — instance refs.
- `SelectedInventoryItemID: Name` (default `None`) — the only piece of "selection" state
  that currently exists.
- `OpenInventoryUI()` — creates/adds `WBP_Inventory` to viewport, `Set Input Mode UI Only`,
  shows mouse cursor, adds an Enhanced Input mapping context. Standalone, presumably bound
  to its own keybind, unrelated to shelves.
- `CloseInventoryUI()` — removes `InventoryWidget` from parent, `Set Input Mode Game Only`,
  hides cursor, removes the mapping context.
- `OpenShelfUI(ShelfRef)` — creates/adds `WBP_ShelfPanel` to viewport (or reuses existing
  widget + calls `SetShelf`), `Set Input Mode Game And UI`, shows cursor. Called from the
  shelf's interact path (confirm exact caller — likely `GA_Interact` on `BP_ShelfActor`,
  or the actor's `OnInteract` — search before assuming).
- `CloseShelfUI()` — removes `ShelfWidget` from parent, `Set Input Mode Game Only`, hides
  cursor.
- `Server_StockItemToSlot(Shelf, ItemID, SlotIndex)` — validates the calling player has
  `ItemID`, removes it from their `BP_InventoryComponent` (`Server_RemoveItem`), calls
  `Shelf->SetSlotItem(SlotIndex, ItemID, ...)`.
- `Server_TakeItemFromSlot(Shelf, SlotIndex)` — clears the shelf slot and returns the item
  to the calling player's inventory.

### `WBP_Inventory` (`/Game/UI/WBP_Inventory`)
- Root `CanvasPanel` → `PanelBackground` (Border, **centered**: anchors 0.5/0.5,
  offsets left=-300 top=-200 right=600 bottom=400, i.e. a 600×400 box centered on
  screen) → `SlotContainer` (WrapBox, holds `WBP_InventorySlot` instances) which also
  contains a `ContextMenu` (`WBP_ItemContextMenu`, collapsed by default). Sibling
  `CloseButton` top-right of the panel.
- Functions: `RefreshInventory`, `ShowContextMenuForItem(ItemID, Quantity)`,
  `HideContextMenu`, `SetHoveredItem`/`ClearHoveredItem`/`GetHoveredItemID`, `OnKeyDown`.

### `WBP_InventorySlot` (`/Game/UI/WBP_InventorySlot`)
- `OnClicked (SlotButton)` → `Sequence`: (a) always calls owning `WBP_Inventory`'s
  `ShowContextMenuForItem(CachedItemID, CachedQuantity)`; (b) if `CachedItemID != None`,
  casts `Get Owning Player` to `BP_PlayerController_ZombieStore` and **toggles**
  `SelectedInventoryItemID` (sets it if different/unset, clears it if clicking the
  already-selected item again).
- No visual indicator currently reflects `SelectedInventoryItemID` — clicking "selects"
  invisibly.

### `WBP_ShelfPanel` (`/Game/UI/WBP_ShelfPanel`)
- Root `CanvasPanel` → `PanelBackground` → `RootBox` (VerticalBox: `HeaderBox`
  [`CategoryText`, `BonusText`, `UpgradeReadoutText`, `UpgradeButton`], `SlotContainer`
  [WrapBox, holds `WBP_ShelfSlot` instances]); sibling `CloseButton`. Also **centered**
  on screen (verify exact anchor values before reanchoring — not confirmed identical to
  Inventory's, but same general "centered floating panel" pattern).
- `SetShelf(ShelfRef)` sets `BonusText`/`UpgradeReadoutText`, clears and rebuilds
  `SlotContainer`'s children (one `WBP_ShelfSlot` per `GetNumSlots()`, which reads
  `ShelfRef->StockedItems.Length`), then calls `RefreshAllSlots`.

### `WBP_ShelfSlot` (`/Game/UI/WBP_ShelfSlot`)
- `OnClicked (SlotButton)`:
  - If the slot is occupied (`StockedItems[SlotIndex].Quantity > 0`): calls
    `Server_TakeItemFromSlot(ShelfRef, SlotIndex)` immediately (**no selection needed** —
    asymmetric with the inventory side), then `RefreshSlot`.
  - Else if empty and `SelectedInventoryItemID != None`: calls
    `Server_StockItemToSlot(ShelfRef, SelectedInventoryItemID, SlotIndex)`, clears
    `SelectedInventoryItemID`, then `RefreshSlot`.
  - Else (empty, nothing selected): no-op — this is the "clicking does nothing" symptom
    the user hit.
- `RefreshSlot` also handles the empty-state visuals (collapses `IconImage`/
  `QuantityText`/`MultiplierText` as appropriate) — this logic is correct and doesn't
  need to change.

### Known related items (do not duplicate)
- `docs/BUGS.md` — "Shelf UI has no item-placement slots" entry: **resolved**
  (`WBP_ShelfSlot` root panel fix, CanvasPanel → SizeBox). Update its status further if
  this plan changes `WBP_ShelfSlot`'s click behavior.
- `docs/BUGS.md` — "Orphaned undeletable `BP_ItemDragOperation` asset": unrelated, true
  drag-and-drop was already abandoned for tooling reasons; this plan does **not**
  resurrect drag-and-drop, it stays click-to-transfer. Don't touch that asset as part of
  this work.
- `GetNumSlots()` on `BP_ShelfActor` has a stale description ("Returns the number of
  shelf slots defined by SlotTransforms") that doesn't match its real implementation
  (`StockedItems.Length`). Small unrelated cleanup — fix the description text if a step
  below already has that Blueprint open for editing, otherwise skip it.

---

## 2. Target Design

Open a single combined **Shelf Trade** view when interacting with a shelf: Inventory
panel docked to the left half of the screen, Shelf panel docked to the right half, both
visible at once. Replace the current "select from inventory, hope you can reach a shelf
slot" flow with a fully symmetric **click-to-select, click-to-place** model that works
in both directions:

1. Click an item (in either panel) that isn't currently selected → it becomes the
   **selected transfer item**, with a visible highlight on its slot.
2. Click a valid **empty** destination slot in the *other* panel → the item moves there
   (server RPC fires, both panels refresh, selection clears).
3. Clicking anywhere else while something is selected (an occupied slot, empty space) is
   a no-op for v1 — no swap logic, no reselection is guaranteed to feel dumb but
   predictable is fine for the first pass. (Optional polish, not required: clicking a
   different sourceable item while one is already selected just replaces the selection.)

This removes the old asymmetry where taking an item from a shelf slot was a single
unconditional click but stocking required a separate inventory-side selection step —
now both directions use the same two-click gesture.

### Selection state (replaces `SelectedInventoryItemID`)

Add on `BP_PlayerController_ZombieStore`:
- New enum `E_TradeSource` — `None`, `Inventory`, `Shelf`.
- New struct `S_TradeSelection` — `Source: E_TradeSource`, `ItemID: Name`,
  `ShelfSlotIndex: int` (only meaningful when `Source == Shelf`).
- New variable `CurrentTradeSelection: S_TradeSelection` (replaces
  `SelectedInventoryItemID`).
- New variable `ActiveTradeShelf: Actor` (or a typed `BP_ShelfActor` reference) — the
  shelf currently open in the trade view, so `WBP_InventorySlot`'s click handler can
  call `Server_TakeItemFromSlot` without needing a shelf reference threaded through the
  inventory widget.

Delete `SelectedInventoryItemID` once nothing references it.

### Combined open/close

Add to `BP_PlayerController_ZombieStore`:
- `OpenShelfTradeUI(ShelfRef)` — sets `ActiveTradeShelf = ShelfRef`, creates/shows both
  `WBP_Inventory` and `WBP_ShelfPanel` in the same call, single
  `Set Input Mode Game And UI` + cursor + mapping-context setup (don't do it twice),
  calls `WBP_ShelfPanel::SetShelf(ShelfRef)` and `WBP_Inventory::RefreshInventory()`.
- `CloseShelfTradeUI()` — removes both widgets, resets input mode/cursor, clears
  `ActiveTradeShelf` and `CurrentTradeSelection`.

Retire `OpenShelfUI`/`CloseShelfUI` (fold their bodies into the two functions above).
**Before deleting them**, find every caller (expected: the shelf's interact ability,
e.g. `GA_Interact` on `BP_ShelfActor`, or the actor's own interact function — confirm
via `blueprint.get_dependencies`/a reference search rather than assuming) and repoint
each call to `OpenShelfTradeUI`/`CloseShelfTradeUI`.

Leave `OpenInventoryUI`/`CloseInventoryUI` (the standalone, non-shelf keybind-driven
inventory-only view) alone — they serve a different purpose outside shelf interaction.
If it turns out nothing besides the shelf flow ever calls the standalone versions,
that's worth flagging to the user, but don't delete them speculatively.

### Layout changes

- `WBP_Inventory`'s `PanelBackground` `CanvasPanelSlot`: reanchor from centered to the
  **left half** of the screen (e.g. anchors `min(0,0) max(0.5,1)` with small margins, or
  keep a fixed-size box anchored to the left edge — match whatever anchor convention the
  rest of the project's docked panels use, if any exist as precedent).
- `WBP_ShelfPanel`'s `PanelBackground` `CanvasPanelSlot`: reanchor to the **right half**
  of the screen, mirroring the above.
- Verify at typical playtest resolution (check `docs/` or ask the user for the target
  resolution if unclear) that both panels fit without overlapping and without being cut
  off — a WrapBox-driven slot grid may need a `SizeBox`/explicit width constraint so slot
  counts up to 16 (max shelf tier) still wrap sensibly in a half-screen-wide panel.
- Each panel keeps its own `CloseButton`, but both should call `CloseShelfTradeUI()` (not
  a per-panel close) so closing either side closes the whole trade view.

### Selection visuals

- `WBP_InventorySlot`: add a "selected" visual state (e.g. a highlight border/background
  color swap on `SlotBorder`, or a dedicated outline image toggled visible) plus a
  `SetSelected(bool)` function or similar, driven by comparing
  `CurrentTradeSelection` against this slot's `CachedItemID` on refresh, and toggled
  immediately in the click handler for responsiveness.
- `WBP_ShelfSlot`: same treatment, comparing `CurrentTradeSelection.Source == Shelf &&
  CurrentTradeSelection.ShelfSlotIndex == SlotIndex`.

### Click handler rewrite

**`WBP_InventorySlot::OnClicked`:**
- If this slot has an item (`CachedItemID != None`) **and nothing is currently
  selected**: set `CurrentTradeSelection = {Source: Inventory, ItemID: CachedItemID}`,
  update this slot's selected visual.
- If this slot has an item and it **is** the current selection: clicking again
  deselects (clear `CurrentTradeSelection`) — preserves today's toggle-off behavior.
- If this slot is **empty** and `CurrentTradeSelection.Source == Shelf`: call
  `Server_TakeItemFromSlot(ActiveTradeShelf, CurrentTradeSelection.ShelfSlotIndex)`,
  clear the selection, refresh both panels.
- Otherwise: no-op.
- Decide whether to keep the existing `ShowContextMenuForItem` call (right-click-style
  menu) as-is alongside this, or whether it now conflicts with the new selection click —
  check with the user if the context menu and the new selection gesture are meant to
  coexist on the same click, since currently both fire from the same `OnClicked`.

**`WBP_ShelfSlot::OnClicked`:**
- If this slot is occupied **and nothing is currently selected**: set
  `CurrentTradeSelection = {Source: Shelf, ItemID: <this slot's ItemID>, ShelfSlotIndex:
  SlotIndex}`, update this slot's selected visual. (This **replaces** the old
  "click occupied slot = instant take" behavior — taking now requires clicking the
  destination inventory slot afterward, matching the new symmetric two-click model.)
- If this slot is occupied and it **is** the current selection: deselect.
- If this slot is **empty** and `CurrentTradeSelection.Source == Inventory`: call
  `Server_StockItemToSlot(ActiveTradeShelf, CurrentTradeSelection.ItemID, SlotIndex)`,
  clear the selection, refresh both panels.
- Otherwise: no-op.

Both handlers need to refresh **both** panels after a successful transfer (item counts
in inventory change too, not just the shelf), so call
`WBP_Inventory::RefreshInventory()` and `WBP_ShelfPanel::RefreshAllSlots()` (or the
single-slot equivalents plus a full inventory refresh) after either RPC — the RPCs are
server-authoritative and replicate back, but the local click widget can also
optimistically refresh or just wait for the replicated property to update and refresh
`OnRep`; match whatever refresh pattern the rest of the codebase already uses for
similar server-round-trip UI updates rather than inventing a new one.

---

## 3. Suggested Implementation Steps (dispatch as separate agent calls, per project
convention — see `CLAUDE.md`'s granular-dispatch and subagent-routing rules; each step
below should be independently testable/compilable before moving to the next)

1. **`ue-blueprint-builder`** — Add `E_TradeSource` enum, `S_TradeSelection` struct,
   `CurrentTradeSelection`/`ActiveTradeShelf` variables to
   `BP_PlayerController_ZombieStore`. Don't wire anything to them yet, don't delete
   `SelectedInventoryItemID` yet (keep both temporarily so nothing breaks mid-migration).
2. **`ue-blueprint-builder`** — Add `OpenShelfTradeUI`/`CloseShelfTradeUI`; find and
   repoint the shelf interact caller(s) from `OpenShelfUI`/`CloseShelfUI` to these new
   functions. Leave old `OpenShelfUI`/`CloseShelfUI` in place but unused for now (delete
   in a later cleanup step once the new path is confirmed working).
3. **`ue-ui-builder`** — Reanchor `WBP_Inventory`'s `PanelBackground` to the left half of
   the screen.
4. **`ue-ui-builder`** — Reanchor `WBP_ShelfPanel`'s `PanelBackground` to the right half
   of the screen. (Steps 3/4 are independently visually testable by opening each panel
   on its own via its existing standalone open path, before the combined flow exists.)
5. **`ue-ui-builder`** (+ light Blueprint wiring per its allowed scope) — Add the
   selected-visual treatment to `WBP_InventorySlot` and rewrite its `OnClicked` per the
   spec above, using `CurrentTradeSelection`/`ActiveTradeShelf`.
6. **`ue-ui-builder`** — Same for `WBP_ShelfSlot`.
7. **`ue-blueprint-builder`** — Cleanup pass: delete `SelectedInventoryItemID`, delete
   `OpenShelfUI`/`CloseShelfUI` once confirmed unused, fix `GetNumSlots()`'s stale
   description text while in there.
8. Manual PIE playtest (see below), then update `docs/BUGS.md`/`docs/PHASE_4_TASKLIST.md`
   status notes to reflect the new flow, replacing references to the old single-window
   click-to-transfer description.

## 4. Open Questions for the User (resolve before or during step 1)

- Should the inventory-side `ShowContextMenuForItem` (right-click-style menu) still fire
  on the same click as selection, or does it need a separate input (e.g. actual
  right-click) now that left-click is doing double duty as "select for transfer"?
- Exact left/right split proportions and margins — 50/50, or some other ratio (e.g. give
  the shelf panel more room since it can have up to 16 slots at max tier vs. inventory's
  slot count)?
- Should selecting a *different* item while one is already selected replace the
  selection (quality-of-life) or be a no-op requiring an explicit deselect first (as
  specced above, simpler for v1)?

## 5. Testing Checklist (manual PIE, per `CLAUDE.md`'s limited-testing-capability rule —
the implementing session should stop and ask the user to run these rather than asserting
success itself)

- Interacting with a shelf opens both panels side-by-side, no overlap, both readable.
- Clicking an inventory item highlights it; clicking it again deselects it.
- With an inventory item selected, clicking an empty shelf slot stocks it there, clears
  the selection, and both panels' counts/contents update.
- Clicking an occupied shelf slot highlights it; clicking an empty inventory slot returns
  it to inventory, clears the selection, both panels update.
- Clicking with nothing selected on an empty slot in either panel is a no-op (no error).
- Closing either panel's Close button closes both and restores normal game input mode.
- Repeat as a non-host client in a listen-server session (multiple prior shelf-related
  fixes in this project were host-authority-only bugs — see `docs/BUGS.md` and
  `docs/PHASE_4_TASKLIST.md` Section 6 for that recurring pattern).
