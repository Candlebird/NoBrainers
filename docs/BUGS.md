# Known Bugs

## Decorative barrel actor has auto-generated name / no outliner folder

- **Area:** Playtest map population (`docs/PHASE_4_TASKLIST.md` Section 5)
- **Repro:** N/A — cosmetic placement issue, not a runtime repro.
- **Actual:** One decorative barrel actor in the playtest map landed with an
  auto-generated name and no outliner folder.
- **Expected:** Actor should have a descriptive name and sit in the correct outliner folder
  like other placed decoration.
- **Status:** Open, cosmetic only, no gameplay impact.

## Orphaned undeletable `BP_ItemDragOperation` asset in `Content/UI/`

- **Area:** UI content cleanup (`docs/PHASE_4_TASKLIST.md` Section 6)
- **Repro:** N/A — asset-cleanup issue, not a runtime repro.
- **Actual:** `BP_ItemDragOperation` (an abandoned drag subclass from an aborted attempt) is
  inert, has zero references, and cannot be deleted via Monolith.
- **Expected:** Orphaned asset should be removable from `Content/UI/`.
- **Status:** Open. Root cause is a confirmed Monolith MCP tooling gap —
  `blueprint.add_node` has no support for `ConstructObjectFromClass`/any object-construction
  node type, which blocks the tooling path that would normally clean this up.

## Meta-currency awarding is host-local only in listen-server co-op

- **Area:** Run-summary / meta-currency payout (`docs/PHASE_5_TASKLIST.md` Task 3.2)
- **Repro:** Complete a run in listen-server co-op as a non-host client.
- **Actual:** Meta-currency earned at run end is only awarded/saved for the host, since the
  save system is gated on host authority.
- **Expected:** All connected players should have their earned meta-currency persisted, not
  just the host.
- **Status:** Open, known limitation (pre-existing, not introduced by the run-summary work).

## Zombie loot-drop impulse is likely a visual no-op

- **Area:** Zombie loot drops (`docs/PHASE_3_TASKLIST.md` Task 6.1)
- **Repro:** Kill a zombie in PIE and observe the spawned `BP_ItemPickup` drop.
- **Actual:** `AddImpulse` is applied to the dropped pickup, but `BP_ItemPickup`'s
  `InteractionMesh` doesn't have `bSimulatePhysics` enabled, so the impulse likely has
  nothing to act on — no visible scatter-on-drop.
- **Expected:** Dropped loot should visibly scatter with a slight impulse.
- **Status:** Open. Likely a one-line fix (enable `bSimulatePhysics` on `BP_ItemPickup`'s
  `InteractionMesh`) if the scatter feel is wanted.

## Ammo replication is unconditioned (bandwidth concern)

- **Area:** `BP_EquipmentComponent::EquipmentSlots` replication (`docs/PHASE_3_TASKLIST.md`
  Task 2.1)
- **Repro:** N/A — architectural/bandwidth concern, not a functional repro.
- **Actual:** `COND_OwnerOnly`-style replication conditioning on ammo isn't achievable in
  Blueprint (lifetime conditions are C++-only), so ammo rides `EquipmentSlots`' existing
  unconditional replication.
- **Expected:** Ammo updates should ideally replicate only to the owning client.
- **Status:** Open, known limitation. Fine at current low update frequency (equip/reload
  only); flagged as a bandwidth concern to revisit now that `Server_ConsumeAmmo` fires every
  shot (landed in task 2.2).

## NavMesh `RuntimeGeneration` override doesn't retroactively apply to existing levels

- **Area:** Breach-point nav integration (`docs/PHASE_3_TASKLIST.md` Task 5.1/5.2)
- **Repro:** Open an existing test level that already had a `RecastNavMesh-Default` actor
  placed before `Config/DefaultEngine.ini`'s `RuntimeGeneration=DynamicModifiersOnly`
  override was added.
- **Actual:** That actor keeps whatever `RuntimeGeneration` it was serialized with — the
  project-level `DynamicModifiersOnly` override only applies to newly-created nav data — so
  the breach `NavModifier` toggle won't rebuild pathing at runtime.
- **Expected:** Breach points should open the nav footprint at runtime in any level.
- **Status:** Open, known limitation/gotcha. Needs a manual check/set of `RuntimeGeneration`
  in-editor (or a re-placed Nav Mesh Bounds Volume) per existing level before the
  breach-triggered nav opening will work.

## Monolith tooling: `auto_layout(formatter="vesper")` can silently duplicate/corrupt nodes

- **Area:** Monolith MCP tooling gotcha, discovered while building `GA_BP_MeleeAttack`
  (`docs/PHASE_3_TASKLIST.md` Task 3.1/3.2)
- **Repro:** Call `blueprint_query auto_layout(formatter="vesper")` on a graph; the call
  itself reports clean success.
- **Actual:** On at least one occasion this silently duplicated 3 `K2Node_CallFunction`
  nodes and repointed some existing connections onto the duplicates (one duplicate had a
  degraded/generic pin type), causing a real compile error that only surfaced on a
  subsequent `compile_blueprint` — not on the `auto_layout` call itself.
- **Expected:** `auto_layout` should not corrupt the graph, or should report the corruption
  if it occurs.
- **Status:** Open, tooling gotcha (not yet reported upstream). Workaround: always recompile
  immediately after any vesper `auto_layout` call and inspect the graph if errors appear.

## Shelf UI has no item-placement slots — only upgrade/close buttons and text

- **Area:** `BP_ShelfActor` shelf UI (click-to-transfer stocking, see
  `docs/PHASE_4_TASKLIST.md` Section 6 and `docs/ParentTaskList.md`)
- **Repro:** Interact with a `BP_ShelfActor` in PIE to open its UI window.
- **Actual:** The shelf window only shows an upgrade button, a close button, and some
  text. There is no way to place a sellable item from inventory into one of the shelf's
  slots.
- **Expected:** The player should be able to put their sellable items into the shelf's
  slots (click-to-transfer stocking/taking, per the tier-based slot counts documented
  in the design docs — 4→6→8→12→16 slots across Tier1–Tier4).
- **Status:** Root-caused. `WBP_ShelfPanel::SetShelf`'s for-loop and `StockedItems`
  are correct — `GetNumSlots()` reads `StockedItems.Length` (its "defined by
  SlotTransforms" description text is stale/inaccurate; `SlotTransforms` isn't
  referenced at all) and returns 4 at runtime, so 4 `WBP_ShelfSlot` instances are
  genuinely created and added to `SlotContainer`. The real bug is in
  `WBP_ShelfSlot`'s widget tree: its root `CanvasPanel` holds `SlotButton` via
  stretch/fill anchors (offsets are margins under fill anchors, not
  position+size), and a `CanvasPanel`'s desired size ignores stretch-anchored
  children — so each `WBP_ShelfSlot` instance's own desired size resolves to
  ~zero, and `SlotContainer` (a `WrapBox`, which sizes children to their desired
  size) renders all 4 slots at zero size. Fix in progress: change
  `WBP_ShelfSlot`'s root from `CanvasPanel` to a `SizeBox`
  (`WidthOverride=100`/`HeightOverride=30`) wrapping `SlotButton` directly.

## Monolith tooling: `add_node` with `MakeStruct` for Vector/Transform can produce uncompilable nodes

- **Area:** Monolith MCP tooling gotcha, discovered while building zombie loot drops
  (`docs/PHASE_3_TASKLIST.md` Task 6.1)
- **Repro:** Call `blueprint_query add_node` with `node_type="MakeStruct"` targeting a
  Vector or Transform struct.
- **Actual:** Intermittently produces nodes that fail to compile ("structure ... is not a
  BlueprintType"), reproducing regardless of which specific MakeStruct call is used.
- **Expected:** `MakeStruct` nodes for Vector/Transform should compile.
- **Status:** Open, tooling gotcha (not yet reported upstream). Workaround: use
  `KismetMathLibrary::MakeVector`/`MakeTransform` CallFunction nodes instead, which compile
  cleanly.

## `GatherSessionState` logs a benign "Accessed None" for players with no PlayerState yet

- **Area:** `BP_GameInstance_NoBrainers::GatherSessionState`
- **Repro:** Start a run; at day-phase start (`BP_GameMode_ZombieStore::StartDayPhase` →
  `SaveSession` → `GatherSessionState`) a hero pawn can exist before its `PlayerState` has
  replicated/been assigned.
- **Actual:** The `Add` node's player-name field is built from a `Select(Index =
  IsValid(Pawn->PlayerState))`, but `K2Node_Select` evaluates both option pins regardless of
  the index — so `GetPlayerName(PlayerState)` runs on a None target and logs "Accessed None
  trying to read (real) property PlayerState in Pawn" even though the `IsValid` guard already
  makes the final output correctly fall back to `""`.
- **Expected:** No error should log when the guard already handles the null case correctly.
- **Status:** Open, cosmetic/log-noise only — no functional break (saved `PlayerName` for that
  slot is just `""`). Optional cleanup: replace the `Select` with a `Branch` on
  `IsValid(PlayerState)` so `GetPlayerName` is only called on the true branch.
