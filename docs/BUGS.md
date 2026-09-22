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
- **Status:** Fixed. Added a Branch at the top of the sweep's loop body (before the
  existing ASC-validity Branch) that tests `NOT ClassIsChildOf(GetObjectClass(HitActor),
  BP_ZombieBase_C)` (pure `GameplayStatics::GetObjectClass` + `KismetMathLibrary::
  ClassIsChildOf` + `Not_PreBool`, no exec-pin cast-fail branching). False path (hit actor
  is a zombie) skips straight to the next loop iteration; true path falls through into the
  existing ASC-validity chain unchanged. Player-vs-zombie and zombie-vs-defense-node damage
  paths are untouched. Blueprint compiles with 0 errors/0 warnings. Needs in-PIE
  verification (see note below).

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
- **Status:** Fixed. In `HandleZombieDied`'s existing `HasAuthority`-gated branch, before
  the existing loot/despawn logic (`Get Actor Of Class(BP_ZombieSpawnerManager)` →
  `Server_RollAndSpawnLoot` → `BeginBodyDespawn`), added: `Get Controller` → `Cast To
  AIC_Zombie` (CastFailed skips straight to the existing loot/despawn chain) → on success:
  `Stop Movement`, `Clear Focus` (Gameplay priority), `Get BrainComponent` → `Stop Logic`
  (reason "Died"), `Set bUseControllerRotationYaw = false` on self, `Get CharacterMovement`
  → `Disable Movement` — then continues into the unchanged loot/despawn chain. No
  `UnPossess` added; the controller stays possessing the corpse, only its AI/movement/
  rotation is stopped. Compiled 0 errors/0 warnings, saved. Still needs in-PIE verification:
  kill a zombie and confirm it stops moving/rotating/attacking immediately rather than
  continuing to track and hit the player during the despawn delay.

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
- **Status:** Open. Fix would add `OnRep_ActiveEventRow`/`OnRep_PendingEventRow` functions and
  move the `OnEventChanged` broadcast into them (so it fires on every machine when the
  replicated value changes), rather than broadcasting only inside the `HasAuthority` branch.
  Not fixed yet — deferred pending confirmation this is the desired fix, consistent with the
  project's existing host-local meta-currency limitation above.
