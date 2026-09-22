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
    anywhere in the project), a "Continue" session-resume button, and returning to the Main
    Menu after a run ends (`BP_GameMode_ZombieStore::EndRun` currently never travels anywhere).
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


## No zombies spawn on entering night phase (regression, fixed — needs PIE confirmation)

- **Area:** `BP_StoreEscalationComponent`'s four "Escalation State" getter functions
  (`GetNightDifficulty`, `GetCustomerVolumeMultiplier`, `GetZombieHordeSizeMultiplier`,
  `GetZombieStatMultiplier`), consumed by `BP_ZombieSpawnerManager::CalculateHordeCount`.
- **Repro:** Enter night phase in PIE (e.g. via `BP_GameMode_ZombieStore::CloseShopEarly`).
  Phase correctly transitions to Night (`BP_GameState_ZombieStore::CurrentPhase`), and
  `BP_ZombieSpawnerManager`'s self-polling (`PollPhaseChange`→`HandlePhaseChanged`→
  `StartWaveSpawning`) correctly detects the change and runs, but `RemainingToSpawn` ends up
  `0` and `bWaveActive` stays `false` — zero zombies ever spawn.
- **Root cause (confirmed):** `BP_StoreEscalationComponent`'s 4 state variables
  (`NightDifficulty`, `CustomerVolumeMultiplier`, `ZombieHordeSizeMultiplier`,
  `ZombieStatMultiplier`) have a Blueprint custom Property Getter bound to their matching
  `Get<Name>()` pure function (a UE5.3+ Blueprint variable-details feature). Because each
  getter's own graph body reads the variable via a normal `VariableGet` node, and the Kismet
  compiler redirects *all* reads of an accessor-bound property (including from inside the
  accessor's own body) through that same accessor function, every call to `Get<Name>()`
  recurses into itself; UE's reentrancy guard aborts the call and returns the type's
  zero-value instead of the real property value. Confirmed empirically: raw reflection reads
  (`pie_get_object_properties`, Python `get_editor_property`) correctly return the real values
  (e.g. `ZombieHordeSizeMultiplier=1.1`), but calling the function itself — via
  `pie_call_function`, via Python `call_method`, and via the real in-game
  `K2Node_CallFunction` inside `CalculateHordeCount` — always returns `0.0`, for all 4 sibling
  getters, even against the CDO with no PIE running, and even after a forced
  `BlueprintEditorLibrary.compile_blueprint` recompile (rules out stale-bytecode). Since
  `CalculateHordeCount` calls `GetZombieHordeSizeMultiplier()` and multiplies by its result,
  the horde-size calculation always yields `0`, so `StartWaveSpawning` sets `RemainingToSpawn=0`
  and no zombies are ever queued to spawn.
- **Expected:** Entering night phase should spawn a horde per `CalculateHordeCount`, using the
  escalation component's real, non-zero multipliers.
- **Status:** Fixed. The Getter/Setter binding lives in the Blueprint's `NewVariables` array
  (`FBPVariableDescription`) as `BlueprintGetter`/`BlueprintSetter` metadata, which is blocked
  from Python's `get_editor_property` reflection and had no existing Monolith action to unbind
  it — so a new Monolith action, `blueprint.set_variable_accessor`, was written
  (`Plugins/Monolith/Source/MonolithBlueprint/{Public,Private}/MonolithBlueprintVariableActions.{h,cpp}`)
  wrapping `FBlueprintEditorUtils::SetBlueprintVariableMetaData`/`RemoveBlueprintVariableMetaData`
  against `FBlueprintMetadata::MD_PropertyGetFunction`/`MD_PropertySetFunction`, taking
  `asset_path`, `name`, and `clear_getter`/`clear_setter` (or `getter_function`/`setter_function`
  to rebind instead of clear) params. After a full module rebuild (Live Coding does not persist
  newly `RegisterAction`'d actions — see the Monolith tooling gotcha note in this file) and an
  editor restart, the action was called against all 4 variables
  (`NightDifficulty`, `CustomerVolumeMultiplier`, `ZombieHordeSizeMultiplier`,
  `ZombieStatMultiplier` on `/Game/Core/Components/BP_StoreEscalationComponent`) with
  `clear_getter=true, clear_setter=true`. The Blueprint now compiles with 0 errors/0 warnings
  and was saved. **Still needs a PIE confirmation** (`CloseShopEarly` → confirm
  `BP_ZombieSpawnerManager`'s `RemainingToSpawn` goes positive and zombies actually spawn from
  the 8 `TargetPoint`s in `Map_Startup`) — not yet done, since testing here is limited to what
  Monolith/editor tooling can verify without a live PIE session.
  Note: the Unreal Editor crashed once during the original investigation (process fully exited)
  after back-to-back `pie_call_function` calls into this recursive accessor — if repeating this
  class of investigation, prefer CDO-level `call_method` tests over repeated `pie_call_function`
  calls against a self-recursive accessor.
