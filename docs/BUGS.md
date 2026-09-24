# Known Bugs

## Stray `Content/GASDocumentation/Maps/Map_Startup.uasset` alongside `Map_Startup.umap` (RESOLVED)

- **Area:** `docs/PHASE_3_TASKLIST.md` Map_Startup cleanup pass (breach-point fix session,
  2026-09-24), flagged by `ue-vision-keeper` during gate-2 review as out-of-scope-but-worth-noting.
- **Repro:** `git status` showed `Content/GASDocumentation/Maps/Map_Startup.uasset` as untracked,
  sitting next to the real level file `Map_Startup.umap`. A `.umap`-named level should never have
  a `.uasset` twin with the same base name — this looked like a leftover from a Monolith save
  operation during the Map_Startup edit pass, not an intentional asset.
- **Actual:** An orphaned file sat in source control's untracked list.
- **Expected:** Only `Map_Startup.umap` (plus its `.umap`-adjacent build artifacts, which are
  gitignored) should exist for this level.
- **Status:** RESOLVED (2026-09-24). Confirmed nothing references `Map_Startup.uasset` (a
  repo-wide grep of `.uasset`/`.umap` files for the name found only `Map_Startup.umap` itself),
  and it was a valid-but-unrelated Unreal package header, not part of the real level — deleted.
  `Map_Startup.umap` (the real level, already committed and verified working via the breach-point
  fix's test-bed runs) is untouched.

## `BP_CustomerSpawner::ActiveCustomers` is not actually replicated

- **Area:** `BP_CustomerSpawner`, found while adding `Server_AutoSellActiveCustomers` (day-end
  auto-sell of in-store customer carts, overnight session 2026-09-23).
- **Repro:** `get_variables` on `BP_CustomerSpawner` shows `ActiveCustomers` (array of
  `BP_Customer` refs) has `replicated: false`, despite doc/summary language elsewhere
  describing it as replicated.
- **Actual:** Server-authoritative logic that reads/mutates this array (e.g. the new
  auto-sell function) works fine since it only ever runs on the server, but clients have no
  synced view of it if anything ever needs to read `ActiveCustomers` client-side.
- **Expected:** Either mark it replicated if client-side reads are ever needed, or document
  that it's intentionally server-only state.
- **Status:** Open, not investigated further — out of scope for the auto-sell task that found
  it. No known current caller needs client-side access, so not urgent.

## `blueprint.auto_layout` can't disambiguate duplicate-named anim state-machine subgraphs

- **Area:** VesperNodeCleaner graph layout (`blueprint.auto_layout`), found during the
  project-wide Vesper cleanup sweep on `ABP_Hero` (AnimBlueprint).
- **Repro:** `ABP_Hero`'s state machines (Locomotion, HitReacts, Statuses, ...) contain many
  subgraphs that share the same name across different states — 10 graphs named `Transition`
  and 4 named `AnimationTransitionGraph_0` in this asset alone. Calling `blueprint.auto_layout`
  with `graph_name: Transition` twice in a row returns identical `nodes_formatted` counts both
  times, confirming it always resolves to the same first match rather than iterating instances.
- **Actual:** Only one instance of each duplicate graph name gets laid out; the rest are
  unreachable through this API and keep their old layout.
- **Expected:** Some way to target a specific subgraph instance — e.g. a parent-graph or
  graph-path parameter — so every state's transition graph can be reached individually.
- **Status:** Open, low priority — cosmetic only (unreached graphs just keep prior layout, no
  logic/compile impact). Likely affects other AnimBlueprints with state machines too
  (`ABP_Zombie`, `ABP_Minion`), not yet confirmed there.

## Vesper auto_layout fails silently ("0 nodes formatted") on `BP_DefenseBase.RefreshDefenseVisual`

- **Area:** VesperNodeCleaner graph layout (`blueprint.auto_layout`, `formatter: 'vesper'`),
  found during the project-wide Vesper cleanup sweep (folder-by-folder, see run-log).
- **Repro:** `blueprint.auto_layout` with `asset_path: /Game/Defense/BP_DefenseBase`,
  `graph_name: RefreshDefenseVisual`, `formatter: vesper`. The graph has 2 nodes.
- **Actual:** Vesper reports "0 nodes formatted" and leaves the graph's existing layout
  untouched. Reproduced twice (one retry), same result both times.
- **Expected:** The graph's 2 nodes should be laid out like any other small function graph.
- **Status:** Open, low priority — cosmetic only, no logic/compile impact. Only graph seen
  to hit this in the full-project sweep; other 2-node graphs elsewhere laid out fine.

## Reload doesn't replenish magazine — GAS tag removal warning (RESOLVED 2026-09-24)

- **Area:** Weapon reload (`BP_EquipmentComponent`, `docs/PHASE_3_TASKLIST.md` ammo & reload
  section). No dedicated GAS reload ability exists — all reload logic (tag add/remove,
  timer-based completion, ammo math) lives in `BP_EquipmentComponent`'s
  `Server_Reload`/`FinishReload`/`CancelReload` functions.
- **Repro:** Automation test `Test_Equipment_ReloadReplenishesMagazine` in
  `Content/Tests/Automation` (`BP_TestController`), run via the standard PIE-smoke test-runner flow.
- **Root cause (two unrelated bugs in the same area):**
  1. `DT_AmmoTypes` rows `RifleAmmo` and `ShotgunShells` had `DefaultStockpile=0`.
     `EnsureAmmoCategorySeeded` seeds a zero-reserve `AmmoPool` entry from that field, so
     `GetActiveAmmo().Reserve` was permanently 0 for any Rifle/LongRifle/Shotgun weapon.
     `CanReload` requires `Reserve>0`, so `Server_Reload`'s inner branch silently never ran for
     those weapons — no timer, no tag, no ammo replenished, no error logged. `PistolAmmo` (48)
     was unaffected and always worked.
  2. `Server_EquipItem` and `Server_SetActiveSlot` both unconditionally called `CancelReload()`
     on every code path, and `CancelReload` unconditionally called
     `RemoveLooseGameplayTags(State.Weapon.Reloading)` regardless of whether a reload was ever
     started — firing the "tag not in container" warning on every weapon equip or slot switch,
     not just during an actual interrupted reload.
- **Fix:** Set `RifleAmmo.DefaultStockpile=90` and `ShotgunShells.DefaultStockpile=24` in
  `DT_AmmoTypes`, matching each weapon's existing `DT_Weapons.DefaultReserveAmmo`. Gated both
  `CancelReload()` calls behind a `bIsReloading` check (`Branch` node) so the tag-removal path
  only runs when a reload was actually in progress.
- **Verified:** Full test-bed run, session-scoped log read: 16/16 tests pass including
  `Test_Equipment_ReloadReplenishesMagazine`; zero `State.Weapon.Reloading` tag warnings in the
  session log; no regressions in the rest of the suite.

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
- **Status:** Fixed, needs in-PIE confirmation. `BP_GameMode_ZombieStore::EndRun`'s direct
  `AddMetaCurrency`/`RecordRunEnded` calls (which only ever ran against the host's own
  GameInstance) were removed and replaced with a `For Each Loop` over the GameState's
  PlayerArray that calls a new reliable owning-client RPC,
  `Client_AwardRunResults(MetaCurrencyAwarded, FinalDay)`, on
  `BP_PlayerController_ZombieStore` — each connected player (host included, exactly once)
  now runs `AddMetaCurrency`/`RecordRunEnded` against their own local GameInstance/save.
  Every player receives the same full run-wide payout (no per-player split — confirmed with
  the user; `S_RunSummary` has no per-player fields to split by).

## Zombie loot-drop impulse is likely a visual no-op

- **Area:** Zombie loot drops (`docs/PHASE_3_TASKLIST.md` Task 6.1)
- **Repro:** Kill a zombie in PIE and observe the spawned `BP_ItemPickup` drop.
- **Actual:** `AddImpulse` is applied to the dropped pickup's `InteractionMesh`.
- **Expected:** Dropped loot should visibly scatter with a slight impulse.
- **Status:** Closed. Re-verified `BP_ItemPickup`'s `InteractionMesh` component template
  directly — `bSimulatePhysics` was already `True` (Mobility `Movable`, `CollisionEnabled`
  `QueryAndPhysics`, profile `BlockAllDynamic`), so the earlier read that flagged this was
  stale. `Server_RollAndSpawnLoot` in `BP_ZombieBase` targets `InteractionMesh` correctly
  with `bVelChange=true`. No graph or property change was needed; confirmed in-game test
  still recommended to eyeball the scatter feel.

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
- Note 2026-09-23: already satisfied for `Map_Startup` and `Test_Level_Zero`. Both have a
  `RecastNavMesh-Default` actor set to `DYNAMIC`, and `DefaultEngine.ini` sets
  `RuntimeGeneration=Dynamic`.
- **RESOLVED for `Map_Startup` (2026-09-24):** forced a full static navmesh rebuild
  (`ai_query.rebuild_navigation`, `save_after: true`) after cutting the 3 physical wall
  gaps for `BP_BreachPoint_Wall8/9/10`. `validate_nav_points` now confirms a full
  (non-partial) path from a point outside each breach through its gap to the interior
  checkout area for all three breach points.

## Customers walk to world origin (0,0,0) instead of shopping

- **Area:** Customer AI — `/Game/AI/Customer/BT_Customer`,
  `/Game/Interactable/BP_CheckoutCounter`.
- **Repro:** Play `Map_Startup`, start Day phase, watch spawned customers.
- **Actual:** Customers ignore the shelves and walk toward (0,0,0).
- **Expected:** Customers browse shelves, queue at the counter, check out, and leave through
  `BP_CustomerExitPoint`.
- **Root cause (2026-09-23, ue-architect):**
  1. `BT_Customer`'s "Queue For Checkout" branch (second child of the root Selector) was
     gated by two "SelfActor Is Set" decorators, which are always true, so every new
     customer joined the queue at once instead of shopping first.
  2. `BP_CheckoutCounter::GetQueueSpotLocation` had its Entry→Return exec wire missing, so
     it always returned `(0,0,0)`. `BTT_JoinCheckoutQueue` wrote that into
     `QueueSpotLocation` and `BTT_WaitInCheckoutQueue` moved the customer there. Both
     `Select` nodes in the function were also reversed (option 0 is the false case), and
     queue spot 0 was the counter's own center, which is off the navmesh.
  3. "Browse Shelf" was gated by `ReadyToCheckout` Is Set (should be Is Not Set) and "Leave
     Empty Handed" by `HasPurchasedItem` Is Set (should be Is Not Set), so shopping could
     never run at all.
  4. Minor: `BP_CustomerExitPoint`'s `ExitMarkerMesh` (BlockAllDynamic) and the overlap-only
     boxes on `BP_ShelfActor`, `BP_CheckoutCounter`, and `BP_DefenseSocket` had
     `CanEverAffectNavigation` on and cut small holes in the navmesh.
  - Not the cause: the navmesh itself (`Map_Startup` has a working `NavMeshBoundsVolume`
    and `Dynamic` `RecastNavMesh`), and the `TargetShelf`/`AssignedCounter` blackboard keys
    (Object keys — an unset one makes `MoveTo` fail, it does not send the customer to the
    origin).
- **Status:** Fixed 2026-09-24. Tasks 1–6 landed (counter function rewire incl. navmesh
  projection, BT decorator fix, nav flags on the 4 marker/interaction components,
  `ArchetypeRow` RepNotify) and verified by automation: `Test_CheckoutQueueOrdering` and the
  new `Test_CheckoutQueueSpotLocation` (added to `BP_TestController`) both pass. Still needs
  a manual in-game check in `Map_Startup` (Build Paths, PIE with 1 then 2 players — shopping
  → queue → checkout → exit flow, no walking to (0,0,0), and archetype walk-speed
  differences visible to a client) before closing this out completely.

## Test_Level_Zero has no checkout counter or customer exit point

- **Area:** Levels — `/Game/Levels/Test_Level_Zero`.
- **Actual:** The level has shelves and a customer spawner but no `BP_CheckoutCounter` or
  `BP_CustomerExitPoint`, so customers can't finish the shopping loop there.
- **Expected:** Use `Map_Startup` for customer loop testing, or add both actors.
- **Status:** Known limitation.

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
- **Status:** Fix landed, awaiting confirmation (Vesper layout rewrite, 2026-09). The cause
  was the old `SplitFanOutNodes` step, which copied pure `K2Node_CallFunction` nodes that fed
  several consumers and rewired links onto the copies. The rewritten
  `VesperGraphLayout.cpp` never duplicates function calls. It only duplicates plain
  self-variable getters (`K2Node_VariableGet` with no linked inputs), verifies the copy's
  output pin type before moving any link, and can be switched off with
  `bDuplicateSharedGetters=False` under `[VesperNodeCleaner]` in `Config/DefaultEditor.ini`.
  Keep recompiling after vesper `auto_layout` calls until this has held up for a while,
  then close this entry.

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
  **RESOLVED (2026-09-24, overnight session):** confirmed via `ui_query` that
  `WBP_ShelfSlot`'s root is now a `SizeBox` (`WidthOverride=100`/`HeightOverride=30`,
  both override flags true) wrapping `SlotButton` → `SlotBorder` → `SlotContent`
  (`VerticalBox` with `IconImage`/`ItemNameText`/`QuantityText`/`MultiplierText`) exactly
  as planned. The fix was already landed in a prior session; only this status line was
  stale. The root node's internal variable name is still literally `"CanvasPanel"` (a
  leftover from before the class swap) — cosmetic only, not worth a rename pass. Still
  needs a real in-PIE confirmation that stocked slots render at visible (non-zero) size
  and are clickable for transfer.

## Customer NPCs never spawn — `BP_CustomerSpawner` cast failure has no retry, and re-spawn timer never re-arms

- **Area:** Customer spawning (`BP_CustomerSpawner`, `docs/PHASE_4_TASKLIST.md` Section 5 / `docs/PHASE_2_TASKLIST.md` Task 4.1)
- **Repro:** Play any run to Day phase in PIE. No customer NPCs ever appear at shelves,
  across any number of day/night cycles.
- **Actual:** Originally two compounding bugs were reported and have since been confirmed
  fixed and landed correctly:
  1. `BeginPlay`'s `Cast To BP_GameState_ZombieStore` `CastFailed` exec pin is now wired
     to a `Delay (0.5s)` → retry-the-cast loop, so a first-tick GameState race no longer
     permanently disables the spawner.
  2. `TrySpawnCustomer`'s "spawn allowed" success branch now re-arms
     `SpawnTimerHandle` via `K2_SetTimer(FunctionName="TrySpawnCustomer", Time=GetCurrentSpawnInterval())`
     after adding the new customer to `ActiveCustomers`, so spawning continues past one
     customer per day-phase transition.

  ~~Ruled out during investigation: ... archetype weighted-pick/nav-projection logic (both
  have correct fallbacks).~~ — **This was wrong.** Follow-up investigation found the real
  remaining root cause plus one hardening gap, both in `BP_CustomerSpawner`, now fixed:
  3. **`GetSpawnTransform` had an inverted `Select` node.** The `Select` driven by
     `K2_ProjectPointToNavigation`'s `ReturnValue` (true = projection succeeded) had its
     two option pins wired backwards: Option `0` ("false"/projection-failed slot) received
     `ProjectedLocation`, and Option `1` ("true"/succeeded slot) received the raw,
     un-projected `Location`. Net effect: whenever projection succeeded, the function used
     the raw un-projected point (potentially off-navmesh/floating); whenever projection
     failed, it used `ProjectedLocation` from the very call that just reported failure
     (effectively a zeroed/default vector), spawning customers at/near world origin.
     Fixed by swapping the two option-pin wirings so Option `0` (failed) now receives the
     raw `Location` fallback and Option `1` (succeeded) now receives `ProjectedLocation`.
  4. **Unwired `CastFailed` on `Cast To BP_Customer` in `TrySpawnCustomer`.** If the
     `SpawnActor` result failed to cast to `BP_Customer`, the function silently dead-ended
     with no re-arm, permanently stalling further spawns after one failed spawn attempt.
     Fixed by wiring `CastFailed` into the existing `K2_SetTimer` re-arm call so a failed
     spawn attempt still reschedules the next `TrySpawnCustomer` tick.
- **Expected:** Customer NPCs should reliably spawn every day phase, up to the concurrent
  cap, for the duration of the day, at valid navmesh-projected spawn point locations.
- **Status:** All four fixes above are landed and the Blueprint compiles clean (0
  errors/warnings). **Still unverified in PIE** — someone needs to actually run a day
  phase in-editor and confirm customer NPCs now appear at real spawn points (not at world
  origin). Note this project has a separate known bug (tracked elsewhere in this file)
  where NavMesh `RuntimeGeneration` config overrides don't retroactively apply to already-
  built navmesh data in existing levels — if `Map_Startup`'s navmesh predates that config
  change, it may need a manual navmesh rebuild in-editor before spawn-point projection
  will actually succeed at runtime. This PIE verification (and the possible manual navmesh
  rebuild) is an open follow-up, not resolved here.

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

## Zombies never retarget — stay locked on a dead player's corpse

- **Area:** Zombie AI targeting (`/Game/GASDocumentation/Characters/Minions/BTS_FindClosestPlayer`,
  `docs/PHASE_3_TASKLIST.md` Task 4.2)
- **Repro:** Let a zombie kill a player in PIE. The zombie keeps standing over/swinging at
  the dead player instead of retargeting another player or entering a search state.
- **Actual:** `BTS_FindClosestPlayer`'s `Event Receive Tick AI` does
  `GetAllActorsOfClass(BP_HeroCharacter_C)` → `GetClosestActor` → writes `TargetActor`,
  with no filter for whether a hero is alive. Dead heroes are never destroyed
  (`AGDHeroCharacter::FinishDying()` deliberately skips `Super::FinishDying()`'s `Destroy()`
  call), so a corpse remains a valid, nearest actor forever and keeps getting rewritten into
  `TargetActor` every service tick. `BT_Zombie`'s chase-branch `TargetActor Is Set` decorator
  never fails, so the zombie never re-evaluates.
- **Expected:** A zombie whose target dies should retarget another living player (or clear
  `TargetActor` and enter search/idle if none are alive).
- **Status:** Fixed. `BTS_FindClosestPlayer`'s `EventGraph` now clears/rebuilds a local
  `AliveHeroActors` array each tick via a `ForEachLoop` over `GetAllActorsOfClass`'s output,
  filtering with `IsAlive()` on each hero before adding, and feeds the filtered array into
  `GetClosestActor` instead of the raw actor list. Compiles with 0 errors/0 warnings.
  Needs in-PIE verification (kill a player, confirm the zombie retargets a living player or
  clears `TargetActor`).

## Zombies can damage other zombies (no faction filter on melee sweep)

- **Area:** Zombie melee combat (`/Game/Characters/BP_ZombieAttackComponent::PerformMeleeAttack`,
  `docs/PHASE_3_TASKLIST.md` Task 4.1)
- **Repro:** Multiple zombies clustered near each other in PIE; watch for zombies taking
  damage/dying with no player nearby.
- **Actual:** `PerformMeleeAttack`'s box sweep uses `ObjectTypeQuery1/2/3`
  (WorldStatic/WorldDynamic/Pawn) with only the swinging zombie itself in `ActorsToIgnore`,
  and the only damage gate is "does the hit actor have a valid AbilitySystemComponent" —
  true for every zombie (all derive from `AGDCharacterBase`). No team/faction/class check
  exists anywhere in the function, so a zombie's swing damages any other zombie caught in
  the sweep. `BP_DefenseBase` actors have no ASC so they're unaffected (correctly routed to
  the separate `BPI_Breachable` damage path instead).
- **Expected:** Zombie melee should not damage other zombies, while still damaging players
  and defense nodes normally.
- **Status:** Fixed and verified. Added a Branch at the top of the sweep's loop body (before
  the existing ASC-validity Branch) that tests `NOT ClassIsChildOf(GetObjectClass(HitActor),
  BP_ZombieBase_C)` (pure `GameplayStatics::GetObjectClass` + `KismetMathLibrary::
  ClassIsChildOf` + `Not_PreBool`, no exec-pin cast-fail branching). False path (hit actor
  is a zombie) skips straight to the next loop iteration; true path falls through into the
  existing ASC-validity chain unchanged. Player-vs-zombie and zombie-vs-defense-node damage
  paths are untouched. Blueprint compiles with 0 errors/0 warnings. Verified via automation:
  `Test_Zombie_NoFriendlyFire` in `BP_TestController` spawns an attacker and victim zombie,
  calls `PerformMeleeAttack` on the attacker targeting the victim, and asserts the victim's
  health is unchanged afterward. Confirmed passing in a clean single-session PIE automation
  run.

## Dead zombies keep rotating/attacking during their despawn delay

- **Area:** Zombie death/despawn (`/Game/Characters/BP_ZombieBase::HandleZombieDied`,
  `docs/PHASE_3_TASKLIST.md` Task 4.3)
- **Repro:** Kill a zombie in PIE and watch it during its ~7s despawn delay (`BodyDespawnDelay`).
- **Actual:** `AGDCharacterBase::Die()` disables collision/gravity and plays the death montage
  but never touches the AIController, behavior tree, or movement mode. `HandleZombieDied`
  (bound to `OnCharacterDied`) only rolls loot and starts the despawn timer — it never stops
  AI. So for the full despawn delay, `AIC_Zombie` keeps possessing the corpse, `BT_Zombie`
  keeps ticking, `BTS_FindClosestPlayer` keeps updating `TargetActor`, and
  `BTT_ZombieMeleeAttack` keeps firing — the corpse visibly yaws toward the player
  (`bUseControllerRotationYaw = true`) and can keep dealing melee damage after death.
- **Expected:** AI logic/rotation/attacks should stop the moment a zombie dies, not just
  visually mask it via the death animation — before the despawn delay elapses.
- **Status:** Fixed and verified. In `HandleZombieDied`'s existing `HasAuthority`-gated
  branch, before the existing loot/despawn logic (`Get Actor Of Class(BP_ZombieSpawnerManager)`
  → `Server_RollAndSpawnLoot` → `BeginBodyDespawn`), added: `Get Controller` → `Cast To
  AIC_Zombie` (CastFailed skips straight to the existing loot/despawn chain) → on success:
  `Stop Movement`, `Clear Focus` (Gameplay priority), `Get BrainComponent` → `Stop Logic`
  (reason "Died"), `Set bUseControllerRotationYaw = false` on self, `Get CharacterMovement`
  → `Disable Movement` — then continues into the unchanged loot/despawn chain. No
  `UnPossess` added; the controller stays possessing the corpse, only its AI/movement/
  rotation is stopped. Verified via automation: `Test_Zombie_StopsLogicOnDeath` (added to
  `BP_TestController`) applies lethal damage to a spawned zombie and asserts
  `BrainComponent::IsRunning() == false` and `bUseControllerRotationYaw == false` shortly
  after death. First version of the test used `GameplayStatics::ApplyDamage`, which does
  nothing here — `AGDCharacterBase` has no `TakeDamage` override; health lives entirely in
  a GAS `AttributeSetBase`, so `Die()` only fires from GAS attribute-change logic. Fixed the
  test to apply damage via a `GameplayEffect` (`GE_MeleeDamage` + `SetByCallerMagnitude`
  on tag `Data.Damage`), matching the pattern the already-passing
  `Test_Zombie_RetargetsAfterTargetDies` uses to kill the player. Confirmed passing in a
  clean single-session 22/22 PIE automation run.

## Store escalation's "cash pool" and "breach point" scaling are unimplemented (deferred scope)

- **Area:** Store Advertisement System (`/Game/Core/Components/BP_StoreEscalationComponent`,
  `docs/PHASE_5_TASKLIST.md` Task 1.1)
- **Repro:** N/A — known gap, not a regression.
- **Actual:** Task 1.1's spec text says `CustomerVolumeMultiplier` should affect "cash pool"
  and `ZombieHordeSizeMultiplier` should affect "spawn frequency at breach points." Neither
  was implemented: (1) there is no customer wallet/spend-budget field anywhere in the data
  model (`S_CustomerArchetypeData` only has `CustomerType`/`PreferredCategories`/
  `MaxPriceMultiplier`/`WalkSpeed`/`MeshVariations`), so there's no cash-pool value to scale
  without inventing a new per-archetype field with its own design implications; (2)
  `BP_ZombieSpawnerManager` spawns zombies at its own designer-placed `SpawnPoints` array,
  not at `BP_BreachPoint` actors (breach points are a BT pathing/target concern via
  `BTS_ZombieBreachDecision`, unrelated to spawn cadence), so "breach point spawn frequency"
  doesn't map onto any existing spawn-rate knob without re-plumbing the spawner.
- **Expected:** Either a design decision on what "cash pool" and "breach point spawn
  frequency" should concretely mean here, or the task spec updated to drop these two
  clauses since the shipped system covers spawn rate/cap, horde size, and zombie stat
  scaling without them.
- **Status:** Open — deliberately deferred, not a bug in the landed system. Everything else
  in Task 1.1/1.2 is built and compiles clean; see `docs/PHASE_5_TASKLIST.md` Status Note
  (1.1/1.2) for what shipped.

## `GatherSessionState` logs a benign "Accessed None" for players with no PlayerState yet (RESOLVED)

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
- **Status:** RESOLVED (2026-09-24). Replaced the `Select` node with a `Branch` on
  `IsValid(PlayerState)`, gating `GetPlayerName(PlayerState)` behind the true branch via a new
  local string variable `ResolvedPlayerName` (set from `GetPlayerName` on true, set to `""` on
  false). Compiles clean; behavior unchanged (saved `PlayerName` for an unassigned slot is still
  `""`), but `GetPlayerName` is no longer called on a None `PlayerState`.

## `OnEventChanged` dispatcher doesn't reach remote clients (host-only event banner)

- **Area:** `BP_GameState_ZombieStore::SetActiveEvent` / `SetPendingEvent` / `ClearActiveEvent`
  (Phase 5 Task 2.2, customer event scheduler).
- **Repro:** `BP_GameMode_ZombieStore`'s event scheduling (`EvaluateDailyEvent`,
  `AnnounceUpcomingEvent`, `ApplyEventToSpawners`) calls these three GameState functions to
  push event state. Each is gated by a `HasAuthority` branch and only sets its replicated
  variable (`ActiveEventRow`, `PendingEventRow`, `PendingEventDay`) — and now broadcasts the new
  `OnEventChanged(EventRow, bIsUpcoming)` dispatcher — inside the true (server) branch.
- **Actual:** `ActiveEventRow` and `PendingEventRow` are marked `replicated: true` but have no
  `OnRep_*` handler (unlike `CurrentPhase`/`ZombiesRemaining`/`StoreCash`, which all have one).
  Since `OnEventChanged`'s broadcast lives inside the server-only `HasAuthority` branch, it only
  fires on the server/listen-host — remote clients receive the replicated variable value but
  have no reactive path (no OnRep, no dispatcher) that fires when it changes.
- **Expected:** In listen-server co-op, all clients should see `OnEventChanged` fire (and any UI
  bound to it, e.g. `WBP_EventBanner`, react) whenever an event becomes active/pending/cleared,
  not just the host.
- **Status:** Fixed, needs in-PIE confirmation. Added `OnRep_ActiveEventRow`/
  `OnRep_PendingEventRow` on `BP_GameState_ZombieStore`, each broadcasting `OnEventChanged`
  (mirroring `OnRep_StoreCash`'s single-node body) and bound as the RepNotify handler for
  `ActiveEventRow`/`PendingEventRow` respectively. **Correction to this entry's original
  proposed fix:** the existing `OnEventChanged` broadcasts inside `SetActiveEvent`/
  `SetPendingEvent`/`ClearActiveEvent`'s `HasAuthority` branches were kept, not moved — RepNotify
  never fires on the authority itself, so removing them would silently break the host/listen-
  server's own event banner. The two OnReps are an added client-side path alongside the
  existing server-side broadcast, not a replacement for it. As of this fix, `OnEventChanged`
  has no bound consumers yet (`WBP_EventBanner` polls `GetActiveEventRow`/`GetPendingEventRow`
  off the replicated GameState vars directly rather than binding the dispatcher), so this was
  a correctness/consistency fix rather than a live UI outage.

## `UnlockBlueprint`/`AddMetaCurrency`/`RecordRunEnded` silently wipe `UnlockedWeaponIDs`/`UnlockedPerkIDs`

- **Area:** `BP_GameInstance_NoBrainers::UnlockBlueprint`, `::AddMetaCurrency`,
  `::RecordRunEnded` (Phase 5 Task 4.2, Save/Load Manager).
- **Repro:** Call any of these three pre-existing functions after `S_SaveMeta` gained the new
  `UnlockedWeaponIDs`/`UnlockedPerkIDs` fields (added alongside this task). Each function reads
  `CachedMeta.MetaData` via `Break S_SaveMeta`, then rebuilds the struct via `Make S_SaveMeta`
  to write back — but the `Make` nodes never wire the `UnlockedWeaponIDs_12_...` /
  `UnlockedPerkIDs_14_...` input pins to the corresponding `Break` outputs, leaving them at the
  node's default (empty array).
- **Actual:** Any call to `UnlockBlueprint`, `AddMetaCurrency`, or `RecordRunEnded` resets
  `UnlockedWeaponIDs` and `UnlockedPerkIDs` to empty on the saved meta, discarding any
  previously unlocked weapons/perks.
- **Expected:** These functions should pass through fields they're not modifying unchanged, the
  way the new `UnlockWeapon`/`UnlockPerk`/`TrySpendMetaCurrency` functions (added in this same
  task) correctly do.
- **Status:** Fixed. Connected `Break S_SaveMeta`'s `UnlockedWeaponIDs_12_...` and
  `UnlockedPerkIDs_14_...` output pins straight through to the corresponding `Make S_SaveMeta`
  input pins in `UnlockBlueprint`, `AddMetaCurrency`, and `RecordRunEnded` (pure passthrough, no
  other logic changed). Verified `UnlockPerk`/`TrySpendMetaCurrency`/`UnlockWeapon` were already
  wired correctly, and `LoadOrCreateMeta` intentionally leaves both arrays at empty-array default
  since it only runs for a brand-new save. Blueprint compiles with 0 errors/0 warnings and was
  saved.

## Monolith tooling: `blueprint.add_struct_field`'s `type` param silently corrupts on an unrecognized token

- **Area:** Monolith plugin, `MonolithBlueprintStructActions.cpp` (`blueprint.add_struct_field`
  action, added during Phase 5 Task 4.1 to add a field to an existing UserDefinedStruct without
  breaking live Make/Break call sites).
- **Repro:** Call `blueprint.add_struct_field` with a `type` value that isn't in the action's
  recognized lowercase vocabulary (`"name"`, `"bool"`, `"int"`, `"float"`, `"string"`, `"text"`,
  `"Vector"`, `"Rotator"`, `"Transform"`, `"object:ClassName"`) — e.g. the C++-style `"FName"`
  instead of `"name"`.
- **Actual:** The action does not error or reject the call. It silently falls back to creating a
  `bool` field instead. This actually happened once on `S_KioskCatalogEntry.RequiredUnlockID`
  (Task 4.3), corrupting the field until caught and re-added with the correct `"name"` token.
- **Expected:** An unrecognized `type` token should fail the action with an explicit error
  listing valid tokens, not silently substitute `bool`.
- **Status:** Open (tooling, not game code). Workaround: always double-check the created field's
  actual type after calling `add_struct_field`/`remove_struct_field`, and use the exact
  lowercase token vocabulary above rather than C++ type names.

## Monolith tooling: Live Coding doesn't persist newly `RegisterAction`'d actions to the on-disk module

- **Area:** Monolith plugin action registration workflow (`Registry.RegisterAction(...)` in any
  `MonolithXxxActions.cpp`).
- **Repro:** Add a brand-new Monolith action via `RegisterAction`, then patch it into the running
  editor via `editor_query live_compile` (Live Coding) instead of a full rebuild.
- **Actual:** Live Coding only patches the running editor process's in-memory module. The action
  keeps reporting "Unknown action" when called — even after a full editor restart/relaunch —
  because the on-disk module DLL was never actually rebuilt with the new registration.
- **Expected:** A newly registered action should become callable after either a successful Live
  Coding patch or an editor restart.
- **Status:** Open (tooling, not game code). Workaround: after adding a new Monolith C++ action,
  do a genuine `Build.bat <Target>Editor Win64 Development -project=...` rebuild (not just Live
  Coding) before expecting the new action to be callable, then restart the editor.

## Meta-Shop UI (`UW_MetaShop`) not yet built — perk unlock/spend flow has no player-facing widget (RESOLVED)

- **Area:** Persistent Save System & Meta-Progression Shop (`docs/PHASE_5_TASKLIST.md` Task 4.3).
- **Repro:** N/A — feature gap, not a runtime repro.
- **Actual:** The underlying perk data model/pipeline is complete (`S_MetaPerkEntry`,
  `DT_MetaPerks` with 4 seeded rows, one dedicated `GE_Perk_*` GameplayEffect per attribute,
  `BP_PerkComponent`'s server-RPC `SubmitUnlockedPerks` with an idempotency guard, an
  `OnASCReady` backstop on `BP_HeroCharacter` that re-fires the submission and re-applies a
  `GE_PerkHealthTopUp` health top-up if pawn possession raced ahead of the RPC, and a
  `Debug_UnlockAllPerks` dev entry point on `BP_GameInstance_NoBrainers`), but there is still no
  in-game hub-kiosk widget (`UW_MetaShop`/similar) that lets a player browse `DT_MetaPerks`,
  spend `MetaCurrency` via `TrySpendMetaCurrency`, and call `UnlockPerk` from UI. Currently the
  only way to unlock a perk is the debug function or direct data manipulation.
- **Expected:** A Meta-Shop widget should let players spend earned meta-currency on perks
  between runs, mirroring the existing `WBP_BuildMenu`/`WBP_KioskCatalog` unlock-gating pattern.
- **Status:** Fixed (2026-09-22). Built per the Option B decision below via `ue-architect`
  planning followed by granular `ue-ui-builder`/`ue-blueprint-builder` dispatches:
  - `/Game/Core/GameModes/BP_GameMode_MainMenu` (parent `GameModeBase`) — its `BeginPlay`
    creates `WBP_MainMenu`, adds it to viewport, sets Input Mode UI Only, shows the mouse
    cursor. (The level's own Level Blueprint could not be used for this — see the tooling
    gotcha note at the end of this entry.)
  - `/Game/Levels/Map_MainMenu` — new level, GameMode Override set to `BP_GameMode_MainMenu`
    so it doesn't inherit the global `GlobalDefaultGameMode` (`BP_GameMode_ZombieStore`).
  - `/Game/UI/WBP_MainMenu` — shows current `MetaCurrency` (via `BP_GameInstance_NoBrainers`),
    `Button_StartRun` opens `/Game/GASDocumentation/Maps/Map_Startup`, `Button_Quit` quits,
    `Button_MetaShop` creates+shows `WBP_MetaShop` (passing itself as `MainMenuRef`) and
    collapses itself.
  - `/Game/UI/WBP_MetaShopEntry` — perk catalog row (icon/name/description/cost/Buy button),
    mirrors `WBP_KioskEntry`'s layout; broadcasts an `OnBuyClicked(PerkID)` dispatcher so a
    shared handler on the parent can identify which dynamically-spawned row fired.
  - `/Game/UI/WBP_MetaShop` — shell widget mirroring `WBP_KioskCatalog`; `RebuildCatalog`
    populates rows from `DT_MetaPerks`, per-row Owned/unaffordable/Buy states driven by
    `BP_GameInstance_NoBrainers::IsPerkUnlocked`/`GetMetaCurrency`; purchase flow guards
    against double-spend on an already-unlocked perk before calling `TrySpendMetaCurrency`
    then `UnlockPerk`; `Button_Back` restores `MainMenuRef` and removes itself.
  - `Config/DefaultEngine.ini`'s `GameDefaultMap`/`EditorStartupMap` repointed from the
    GASDocumentation sample's `Map_Startup` to `/Game/Levels/Map_MainMenu`.
  - **Tooling gotcha found this pass:** a level's `LevelScriptBlueprint` is a lazily-created
    transient subobject that doesn't exist as a browsable asset until a human opens
    "Blueprints → Open Level Blueprint" for that level at least once in the editor UI — Monolith
    has no action that can create/edit one (confirmed via `monolith_discover`), and Python's
    `run_python` can't reach it either (`ULevel::LevelScriptBlueprint` is a protected native
    property with no exposed get-or-create API in this engine build's Python bindings). Worked
    around by moving the BeginPlay widget-spawn logic into the level's GameMode instead, which
    is a normal content-browser Blueprint asset Monolith can edit — sidesteps the gap entirely
    and needs no new Monolith C++ work.
  - **Deferred, not built this pass:** weapon/defense-blueprint meta-shop tabs (would need new
    data-model work — `DT_KioskCatalog`/`DT_DefenseBlueprints` aren't meta-currency-denominated
    and have no `RequiredUnlockID` set), a host/join co-op flow for "Start Run" (none exists
    anywhere in the project), and a "Continue" session-resume button. **Returning to the Main
    Menu after a run ends is now fixed** (needs in-PIE confirmation) — `EndRun` sets a
    `PostRunReturnDelay`-second timer (default 5s) after the per-player payout RPCs fire, then
    calls a new `ReturnToMainMenu` function (`OpenLevel` to `PostRunLevelName`, default
    `Map_MainMenu`) on the server, which server-travels all connected clients. This is a direct
    travel with no run-summary screen (none exists yet; `LastRunSummary` is already replicated
    on GameState so a future `WBP_RunSummary` can be added without re-plumbing — confirmed
    acceptable scope with the user for now).
  - **Still needs in-PIE confirmation** — not yet playtested (see project-wide PIE-testing
    limitation noted throughout this doc).
  **Decision (2026-09-22, user-approved): the Meta-Shop UI's home is Option B — a real
  Main Menu level/flow** (`Map_MainMenu` + `WBP_MainMenu`), not a hub-kiosk actor (Option A)
  or a debug-key-openable widget stopgap (Option C). User's stated intent: "nail down a real
  feature instead of a test fixture."

## Player no longer spawns with a starting pistol

- **Area:** `BP_HeroCharacter::OnASCReady` (`/Game/GASDocumentation/Characters/Hero/BP_HeroCharacter`).
- **Repro:** Play a run in PIE; player pawn spawns/possesses with no starting pistol.
- **Actual:** This session's perk-application work (see the Meta-Shop UI entry above) added a
  new `HasAuthority` branch directly onto `Event OnASCReady`'s exec output pin, which silently
  **replaced** (rather than fanned out from) the pre-existing wire running
  `Event OnASCReady` → `Parent: OnASCReady` → `GrantStartingLoadoutIfEmpty` (on
  `BP_EquipmentComponent`) → cast to `BP_PlayerController_ZombieStore` → `OnPawnEquipmentReady`.
  The `Parent: OnASCReady` node's `execute` input pin had zero incoming connections, so the
  starting-loadout grant (including the pistol) never fired.
- **Expected:** Player should always spawn with a starting pistol from
  `GrantStartingLoadoutIfEmpty`.
- **Status:** Fixed (2026-09-22). Added a `Sequence` node between `Event OnASCReady` and its
  two downstream chains (`then_0` → `Parent: OnASCReady` → loadout grant; `then_1` → the
  `HasAuthority` perk-application branch), so both fire independently instead of one
  overwriting the other's wire. Note for future edits to this event: Monolith's
  `blueprint.connect_pins` **replaces** an existing single connection on an output exec pin
  rather than adding a fan-out wire — always insert an explicit `Sequence` node when a second
  chain needs to run off a pin that already has a connection. Compiled 0 errors/0 warnings,
  saved. Still needs in-PIE verification (spawn a fresh pawn and confirm the pistol appears
  alongside perk application still working).


## Build Menu: clicking a trap does nothing (root-caused, fix in progress)

- **Area:** Build Mode targeting (`BP_BuildModeComponent::UpdateTargetSocket`,
  `docs/PHASE_4_TASKLIST.md` Section 2.1/2.3).
- **Repro:** Press `B` in-game during Day Phase (Build Menu opens), click a trap entry,
  then aim at a build socket and press `F`.
- **Actual:** Diagnostic confirmed clicking a menu entry *does* correctly wire through
  `WBP_BuildEntry::OnClicked` → `BP_PlayerController_ZombieStore::HandleBuildMenuBlueprintSelected`
  → `BP_BuildModeComponent::SetSelectedBlueprint` (menu closes as expected) — that half is
  not the bug. The actual root cause is in `UpdateTargetSocket`: its
  `Branch(NotEqual_ObjectObject(NewTarget, CurrentTargetSocket))` only recomputes
  `bCurrentTargetValid` on the `true` branch (when the traced socket actor itself changes);
  the `else` pin is unconnected, so if the player is already aiming at a socket *before*
  selecting a blueprint (the common case — open menu, pick a trap, camera hasn't moved), the
  cached `bCurrentTargetValid` from before selection never gets recomputed, and `F`
  (`IA_ConfirmPlacement`) silently no-ops via `GetPlacementRequest.bValid == false`. There is
  also no feedback anywhere on this failure path (`BP_PlayerController_ZombieStore`'s
  `IfThenElse_6`/`IfThenElse_7` both have unconnected `else` pins), so a failed placement
  looks identical to total unresponsiveness.
- **Expected:** Selecting a blueprint while already aiming at a valid socket should allow
  immediate placement with `F`; validity should be recomputed against the *current* selection
  every trace tick, not only when the traced actor changes.
- **Secondary/unconfirmed:** `BP_DefenseSocket::UserConstructionScript` has one node
  (`SetCollisionResponseToAllChannels`) flagged with a validator error, but the actual build
  trace uses object-type (`ObjectTypeQuery2`/WorldDynamic) matching, not channel response, so
  this is likely dead code and not chased as part of this fix.
- **Status:** Fixed and verified by automation (`Test_BuildModePlacementRequest`, added to
  `Content/Tests/Automation`, PASSES as of this session's full test-bed run) — still needs a
  real in-PIE manual confirmation (mouse/keyboard `B`→click→aim→`F` flow) since the automation
  test drives the component's functions directly rather than simulating actual input. Landed
  this session:
  `UpdateTargetSocket` now recomputes `bCurrentTargetValid` on every trace tick (the `Branch`'s
  previously-unconnected `else` pin now re-runs the occupied/socket-type validity check).
  While validating that fix, `validate_blueprint` also caught the **exact same disconnected
  Entry→Return exec pin bug independently present in two more functions on this Blueprint**:
  `GetPlacementRequest` (the function that actually gates `F`-press placement — it was
  silently always returning `bValid=false` regardless of any upstream fix, so the
  `UpdateTargetSocket` fix alone would NOT have resolved the reported bug) and
  `GetCurrentTargetSocket`. Both are pure functions but still had live (non-orphaned) exec
  pins on their Return Nodes that needed wiring. All three fixes are landed; `BP_BuildModeComponent`
  now validates with zero disconnected nodes.

## Customers still don't spawn on Day phase (root-caused, fix in progress)

- **Area:** Customer spawning (`BP_CustomerSpawner::GetMaxConcurrent`,
  `docs/PHASE_4_TASKLIST.md` Section 5 / `docs/PHASE_2_TASKLIST.md` Task 4.1). See the
  separate, earlier `BP_CustomerSpawner` entry above in this file, which lists 4 prior fixes
  as landed and compiling clean.
- **Repro:** Play a run to Day phase in PIE. No customer NPCs appear at shelves.
- **Actual:** The 4 previously-landed fixes (cast-retry, timer re-arm, inverted `Select` in
  `GetSpawnTransform`, unwired `CastFailed` in `TrySpawnCustomer`) are all genuine and
  correct, but none of them touch the actual blocker. Root cause, confirmed via
  `validate_blueprint` (`disconnected_nodes: [K2Node_FunctionResult_0 "Return Node" in graph
  GetMaxConcurrent]`): `GetMaxConcurrent`'s `K2Node_FunctionEntry_0.then` exec pin is not
  connected to `K2Node_FunctionResult_0.execute` — only the data-pin chain feeding the return
  value (`BaseMaxConcurrent × EscalationComponent.GetCustomerVolumeMultiplier() +
  EventConcurrentBonus`) is wired. With the exec pin disconnected, the function always returns
  the int default `0`. `TrySpawnCustomer`'s gate `Branch(Length(ActiveCustomers) <
  GetMaxConcurrent)` therefore always evaluates `0 < 0 = false`, permanently taking the
  `else` branch, which just re-arms the spawn timer forever without ever reaching
  `SpawnActor`. This is the exact same bug class as the already-fixed "no zombies spawn on
  entering night phase" regression (an exec-pin disconnection between a function's Entry and
  Return node silently returning a default value) — comparison against the working
  `BP_ZombieSpawnerManager::CalculateHordeCount` (Return Node correctly wired) confirmed the
  zombie path's spawn-point/nav-projection logic was never the differentiator. The NavMesh
  `RuntimeGeneration` theory carried over from the earlier entry is not implicated here:
  `Map_Startup`'s `RuntimeGeneration` is `Dynamic` (not `DynamicModifiersOnly`), and the
  zombie spawner (which works) does no nav projection at all, so nav config was a red herring
  for this particular bug.
- **Expected:** Customer NPCs should reliably spawn every day phase.
- **Secondary/unconfirmed (not spawn blockers, tracked for follow-up):**
  `TrySpawnCustomer`'s `SpawnActor` leaves the expose-on-spawn `ArchetypeRow` pin
  unconnected (set only after spawn via cast), so `BP_Customer::BeginPlay`'s row lookup
  always sees `None` and `MaxWalkSpeed`/archetype data never actually apply; and `BeginPlay`
  never seeds `LastKnownPhase` before its `Switch(CurrentPhase)` (unlike
  `BP_ZombieSpawnerManager::BeginPlay`, which does), a latent bug if the spawner ever begins
  play outside Day phase.
  - Update 2026-09-23: `Server_SpawnCustomerBurst` sets `ArchetypeRow` after spawn but never
    calls `ApplyArchetype`, and `ArchetypeRow` was not replicated, so clients never got the
    right `MaxWalkSpeed`. Fix: `ArchetypeRow` becomes RepNotify (`OnRep_ArchetypeRow` →
    `ApplyArchetype`) with a `None` guard on `BeginPlay`. See "Customers walk to world
    origin (0,0,0) instead of shopping."
- **Status:** Fixed and verified by automation (`Test_CustomerSpawnerMaxConcurrent`, added to
  `Content/Tests/Automation`, PASSES as of this session's full test-bed run — confirms
  `GetMaxConcurrent()==6` and that `TrySpawnCustomer()` actually grows `ActiveCustomers`).
  Still needs a real in-PIE manual confirmation (play to Day phase, confirm customers appear
  at shelves) since the automation test calls functions directly rather than running the full
  phase-timer/spawn-loop over real time.

## No zombies spawn on entering night phase (regression, fixed — PIE-confirmed)

- **Area:** `BP_StoreEscalationComponent`'s four "Escalation State" getter functions
  (`GetNightDifficulty`, `GetCustomerVolumeMultiplier`, `GetZombieHordeSizeMultiplier`,
  `GetZombieStatMultiplier`), consumed by `BP_ZombieSpawnerManager::CalculateHordeCount`.
- **Repro:** Enter night phase in PIE (e.g. via `BP_GameMode_ZombieStore::CloseShopEarly`).
  Phase correctly transitions to Night (`BP_GameState_ZombieStore::CurrentPhase`), and
  `BP_ZombieSpawnerManager`'s self-polling (`PollPhaseChange`→`HandlePhaseChanged`→
  `StartWaveSpawning`) correctly detects the change and runs, but `RemainingToSpawn` ends up
  `0` and `bWaveActive` stays `false` — zero zombies ever spawn.
- **Root cause (confirmed, corrected from an earlier misdiagnosis):** all 4 getter functions'
  graphs had their `K2Node_FunctionEntry`'s `then` exec-output pin left **disconnected** from
  the `K2Node_FunctionResult`'s `execute` exec-input pin — only the data pin
  (`VariableGet`→`ReturnValue`) was wired. A Kismet function in this shape always executes the
  disconnected result node with the return value's type default (i.e. always returns `0.0`),
  regardless of purity or of any variable-accessor binding. This was verified with a controlled
  A/B test: a throwaway pure function returning a hardcoded literal reproduced the same `0`
  symptom when its exec pins were left disconnected, and returned the literal correctly once
  `then`→`execute` was wired — isolating the defect to the disconnected exec pins, independent
  of accessors. Since `CalculateHordeCount` calls `GetZombieHordeSizeMultiplier()` and
  multiplies by its result, the horde-size calculation always yielded `0`, so
  `StartWaveSpawning` set `RemainingToSpawn=0` and no zombies were ever queued to spawn.
  An earlier pass at this bug incorrectly attributed it to Blueprint custom Property
  Getter/Setter self-recursion (the `MD_PropertyGetFunction`/`MD_PropertySetFunction`
  UE5.3+ variable-accessor feature) and "fixed" it by clearing that metadata via a new
  Monolith action, `blueprint.set_variable_accessor`. That looked plausible under CDO-level
  reflection checks, but a real live-PIE test (`pie_call_function` against the getters, and
  the real in-game `CalculateHordeCount`→`GetZombieHordeSizeMultiplier` call) showed the
  getters still returned `0` after that "fix" — proving the self-recursion theory was wrong.
  `blueprint.set_variable_accessor` itself is legitimate and harmless (it is a real, correctly
  implemented unbind action for that metadata) but was not the fix for this bug.
- **Expected:** Entering night phase should spawn a horde per `CalculateHordeCount`, using the
  escalation component's real, non-zero multipliers.
- **Status:** Fixed and PIE-confirmed (2026-09-22). Wired `K2Node_FunctionEntry_0.then` →
  `K2Node_FunctionResult_0.execute` on all 4 getter graphs via `blueprint.connect_pins`,
  recompiled (0 errors/0 warnings), and saved on
  `/Game/Core/Components/BP_StoreEscalationComponent`. Verified with a clean end-to-end PIE
  run (fresh `load_level` → `start_pie` → `CloseShopEarly`): `BP_ZombieSpawnerManager`'s
  `RemainingToSpawn` came back `1` and `bWaveActive` came back `true` (both were `0`/`false`
  before the fix).
  Note for future Blueprint authoring via Monolith: `blueprint.add_function` can produce a
  function graph with `FunctionEntry.then` left unconnected to `FunctionResult.execute` even
  when the data pins are correctly wired — always verify exec-pin connectivity (e.g. via
  `blueprint.get_graph_data`'s `connected_to` arrays) on functions created this way, not just
  that the data pins resolve.
  Note: the Unreal Editor crashed once during the original (misdiagnosed) investigation
  (process fully exited) after back-to-back `pie_call_function` calls — cause unconfirmed,
  but avoid rapid repeated `pie_call_function` calls against the same function as a precaution.

## Checkout counter stand-location bug — customer permanently loops between claim/queue (RESOLVED)

- **Area:** `BP_CheckoutCounter`, `BT_Customer`/`BB_Customer`, `BTT_MoveToCounter`,
  `BTT_JoinCheckoutQueue` (overnight session 2026-09-24, customer checkout-loop hardening).
- **Repro:** Let a customer reach checkout in `Map_Startup`. It claims the counter, then
  never actually completes checkout.
- **Root cause:** `BTT_MoveToCounter`'s "Move To Counter" node was keyed on `AssignedCounter`
  (the counter actor itself), whose origin sits inside its own mesh — not a navigable point —
  so the move-to call always failed, aborting the "Checkout And Leave" branch and falling
  through to "Queue For Checkout." There was also no guard stopping a counter's own occupant
  from rejoining its own queue, so this produced a permanent claim → fail-to-move → re-queue
  loop with no way out.
- **Fix:** Added `GetCustomerStandLocation()` on `BP_CheckoutCounter` (same
  `ProjectPointToNavigation` pattern as the existing `GetQueueSpotLocation`), writing a
  NavMesh-projected stand point to a new `CounterStandLocation` Blackboard vector key at
  every claim point; `BTT_MoveToCounter` now targets that vector key instead of the counter
  actor. Added a guard so a counter's own occupant releases the counter before it can
  re-enter its own queue.
- **Status:** Fixed and verified 2026-09-24. `Test_CustomerCheckout_PaysAndDespawns` and
  `Test_CheckoutCounter_TryClaimReturnsTrue` both PASS in a correctly session-scoped,
  75-second-held PIE automation run, alongside the other 12 sync tests in
  `BP_TestController`'s `RunAllTests` chain (only the pre-existing, unrelated
  `Test_Equipment_ReloadReplenishesMagazine` GAS bug still fails — see its own entry above).
  Vision-keeper gate 2: ALIGNED. Committed (`40c8a41`).

## Monolith/Unreal gotcha: a `BlueprintPure` function with branching logic can silently return zeroed output when called cross-actor (RESOLVED)

- **Area:** `BP_BreachPoint::GetApproachLocation`, called from
  `BTS_ZombieBreachDecision::WriteBreachApproach` (`docs/PHASE_3_TASKLIST.md`, zombie
  breach-point AI).
- **Repro:** `GetApproachLocation` was `BlueprintPure`, built from `GetActorLocation`,
  `GetActorForwardVector`, vector math, two `Vector_Distance` calls, a `Less_DoubleDouble`,
  and a `SelectVector` branch. It compiled clean and returned correct values when inlined
  in the same Blueprint's graph, but returned `(0,0,0)` whenever invoked cross-actor as a
  genuine `ProcessEvent`/UFunction call (e.g. from another Blueprint's graph, or via
  `editor.pie_call_function`).
- **Actual:** `BTS_ZombieBreachDecision`'s breach-approach-location computation silently
  came back zeroed at runtime, undermining the zombie breach/approach behavior despite the
  function compiling with 0 errors and looking correct on inspection.
- **Expected:** A pure function's output should be identical whether it's inlined or called
  cross-actor.
- **Status:** RESOLVED (2026-09-24). There is no Monolith action to flip an existing
  function's pure/impure flag in place (`UBlueprint::FunctionGraphs`/`UbergraphPages` are
  Python-reflection-protected — scripting the flag directly throws "is protected and cannot
  be read"). Fixed by deleting and recreating the function as `BlueprintCallable`
  (`blueprint.add_function(is_pure=false)`) with identical logic, now exec-driven
  (`Entry.then -> ... -> Return.execute`), and rewiring both call sites
  (`BTS_ZombieBreachDecision::WriteBreachApproach` and
  `BP_TestController::Test_BreachPoint_ApproachLocation`) to the new exec pins. Verified via
  a direct cross-actor `editor.pie_call_function` call (correct non-zero result) and two
  independent full test-bed runs, both showing `Test_BreachPoint_ApproachLocation` and
  `Test_BreachPoint_DamageBreaches` PASS.
  **Reusable gotcha for future work:** treat any `BlueprintPure` function with
  branching/`Select` logic as unverified for cross-actor calls until tested that way — a
  clean compile and correct same-Blueprint behavior are not sufficient evidence. Rebuilding
  it exec-driven also needed `KismetMathLibrary::MakeVector`/`BreakVector` CallFunction
  nodes in place of generic `K2Node_MakeStruct`/`K2Node_BreakStruct` for the Vector
  make/break step — generic Vector struct nodes were rejected as "not a BlueprintType" when
  created from scratch in this rebuild (same class of issue as the existing
  `add_node`-with-`MakeStruct` entry above, now confirmed to also affect manually
  reconstructed graphs, not just that action).

## Test-bed log ambiguity: some tests appear to log a result twice within one `RunAllTests` session (RESOLVED)

- **Area:** `BP_TestController` (`EventGraph` and `RunAllTests` function graph), and
  `ue-test-runner`'s session-scoping discipline when reading `[AUTOTEST]` lines.
- **Repro (original):** A full test-bed run that included `Test_CustomerCheckout_PaysAndDespawns`
  unexpectedly FAILed once; a follow-up diagnostic misread multiple prior PIE sessions' logs
  as one session and reported several tests (`CheckoutQueueSpotLocation`,
  `Test_CheckoutQueueOrdering`, etc.) logging twice in "one" run. A later overnight session
  re-observed a much stronger version of the same symptom: a single 120s session appeared to
  show `RunAllTests` firing ~45 times, with `Test_DayEndAutoSellCustomerItems` (~17%) and
  `Test_CustomerCheckout_PaysAndDespawns` (~41%) failing intermittently with bare
  `[AUTOTEST] FAIL:` lines and no error text.
- **Actual (root-caused, two parts):**
  1. The apparent "~45 cycles" was a measurement artifact, not real repeated invocation —
     confirmed only one `BP_TestController` instance exists in the test map, `Event Tick` and
     `Event ActorBeginOverlap` are both disabled, and nothing calls `RunAllTests` more than
     once. The inflated count came from reading accumulated `[AUTOTEST]` lines across many
     separate `run_pie_smoke` sessions run earlier the same day instead of isolating one
     session's exact timestamp range.
  2. `Test_CustomerCheckout_PaysAndDespawns` had a genuine wiring bug: it was chained onto the
     tail of `Test_DayEndAutoSellCustomerItems`'s own async completion event
     (`DaySellTest_Delayed` → 1.5s `Delay` → `Server_AutoSellActiveCustomers` → `LogResult`)
     instead of being called from `RunAllTests`'s own chain, so it only ran when that async
     path happened to complete inside the session window (~60% of runs) and, when it ran, it
     called its own `Server_AutoSellActiveCustomers` + destroyed all customer actors
     concurrently with `Test_DayEndAutoSellCustomerItems`'s in-flight check — corrupting that
     test's cash math and causing both to log a bare FAIL back-to-back. A first fix attempt
     (calling it directly from `RunAllTests`'s synchronous chain) made invocation deterministic
     but made the race worse, since it then ran ~1.5s *before* the day-sell test's async tail
     had finished.
- **Expected:** Each test logs exactly one PASS/FAIL result per session, and
  `Test_CustomerCheckout_PaysAndDespawns` runs only after `Test_DayEndAutoSellCustomerItems`'s
  own async chain has actually resolved, not merely been called.
- **Status:** Fixed. `Test_CustomerCheckout_PaysAndDespawns` is now wired in `EventGraph` off
  the `then` pin of the `LogResult` call that ends `Test_DayEndAutoSellCustomerItems`'s async
  chain, guaranteeing correct ordering and exactly-once invocation. Verified clean in a
  properly single-session-scoped 100s run (`pie_smoke_36_041456`): 21/21 tests PASS, no
  duplicate log lines, `Test_DayEndAutoSellCustomerItems` and `Test_CustomerCheckout_PaysAndDespawns`
  each logged exactly once. Root cause of the original "log ambiguity" symptom was therefore a
  mix of test-runner session-scoping error and a real test-harness ordering bug, not an engine
  or Monolith issue.

## Tooling gotcha: `run_pie_smoke` defaults to a 5-second session, which silently truncates async test runs

- **Area:** Monolith MCP tooling (`editor_query("run_pie_smoke", ...)`), discovered while
  verifying the checkout-counter stand-location fix above.
- **Repro:** Call `run_pie_smoke` without an explicit `duration` against a test bed run that
  includes any async/delayed test (chained via a `Delay` node or a custom event off
  `RunAllTests`).
- **Actual:** `duration` defaults to 5 seconds (clamped 0–120) and PIE tears itself down at
  that point regardless of what happens afterward. `poll_pie_smoke` only takes `session_id`/
  `include_samples` — it cannot wait or extend a session past its original `duration`. This
  produced two false alarms this session: a FAIL for `Test_CustomerCheckout_PaysAndDespawns`
  and a "missing" result for `Test_CheckoutCounter_TryClaimReturnsTrue` (the latter also had
  a separate search-pattern typo — searched for `Test_CheckoutCounterTryClaimReturnsTrue`,
  no underscore after "Checkout"). Both tests were actually passing; the apparent failures
  were log-session-mixing/premature-teardown artifacts.
- **Expected:** Test-runner dispatches should always account for real test duration.
- **Status:** Fixed. `.claude/agents/ue-test-runner.md` now requires an explicit `duration`
  on every `run_pie_smoke` call (≥75s for any run with async/delayed tests, ≥30s for a purely
  synchronous run), and warns that a session ending exactly at the requested `duration` before
  results appear should be re-run with a larger `duration`, not re-polled. `.claude/monolith/SCHEMAS.md`
  was also stale (missing `poll_pie_smoke`, `stop_pie_smoke`, `list_errored_blueprints`,
  `capture_pie_movement_clip`) and has been regenerated.
