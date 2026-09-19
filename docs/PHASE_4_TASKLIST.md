Phase 4: Defense & Building Systems

Technical Context

Engine Version: Unreal Engine 5.7.4

Perspective: First-Person

Architecture: Node-based socket placement system (pre-defined world anchors), blueprint unlock registry, day-only build mode UI, server-authoritative money transactions placement.

Goal: Implement simplified build system players spend store cash Day Phase place unlocked defense blueprints onto specialized, pre-defined node sockets (Floor, Wall, TurretBase, Other).

Task Breakdown

1. Build Node Socket Architecture

[x] 1.1 Defense Socket Actor (ADefenseSocket)

Status: Built as `/Game/Defense/BP_DefenseSocket` (Blueprint, not native C++, per this project's Blueprint-first convention). Replicated `SocketType` (E_DefenseSocketType), `OccupyingDefense` (Actor ref), `bIsOccupied`. Build-mode-only highlight visibility hook present. Landed in commit fac8297.

[x] 1.2 Socket Trace & Selection Engine

Status: `/Game/Characters/BP_BuildModeComponent` on `BP_HeroCharacter` does the camera-center line trace against `BP_DefenseSocket` actors and dispatches valid/invalid highlight state while `bBuildModeActive` is true. Landed in commit fac8297.

2. Day-Only Build Mode & Blueprint System

[x] 2.1 Build Mode Input & HUD Overlay (IA_ToggleBuildMode)

Status: `IA_ToggleBuildMode` bound to `B` in `IMC_Default`. `BP_PlayerController_ZombieStore` gates the toggle to `CurrentPhase == DayPhase` and force-exits `bBuildModeActive` via a bound `OnPhaseChanged` handler whenever the phase leaves Day. Landed in commit 8d9d9a4. `/Game/UI/WBP_BuildMenu` + `WBP_BuildEntry` (grid, not radial/carousel — deviation from the doc's wording) show unlocked/locked `DT_DefenseBlueprints` rows and expose `SelectedBlueprintID`/`OnBlueprintSelected`. Landed in commit da31cb4. Remaining gap: no "confirm placement" input exists yet to consume the selection and fire `Server_PlaceDefenseOnSocket` — needs its own follow-up step (new input action + wiring selection+traced-socket into the RPC call), plus wiring the widget's visibility to `bBuildModeActive`.

**BLOCKED sub-item:** `BP_PlayerController_ZombieStore.HandleBuildMenuBlueprintSelected(BlueprintID: Name)` was built and compiles clean, but binding it to `WBP_BuildMenu`'s `OnBlueprintSelected` event dispatcher is not achievable via any currently-available Monolith tool. Exhausted: `blueprint_query add_node` with both `CreateDelegate` (self-context and external-target_class variants — the node is created but its internal function reference never actually gets set, so `compile_blueprint` always fails with "missing a function/event name") and `CustomEvent` (no parameter-pin support for matching an arbitrary dispatcher signature); `set_function_params` (only targets true Function graphs, not bare CustomEvent nodes); and a direct Python escape hatch via `editor_query run_python` against the live `K2Node_CreateDelegate` object (none of the candidate internal fields/setters are exposed to Python's UObject reflection wrapper). **Needs a manual editor fix**: open `OpenBuildMenu` (or wherever the widget is created) in the graph editor, drag off `WBP_BuildMenu`'s `OnBlueprintSelected` dispatcher's "Bind Event" pin, and let the editor auto-create a correctly-signatured Custom Event bound to it, then call `HandleBuildMenuBlueprintSelected` from inside it. All exploratory nodes from these attempts were removed and the Blueprint reverted to a clean, saved, 0-error state.

[x] 2.2 Blueprint Registry & Progression Engine (UBlueprintSubsystem)

Status: Implemented as a replicated `UnlockedBlueprintIDs` array + `IsBlueprintUnlocked`/`Server_UnlockBlueprint` on `BP_GameState_ZombieStore` (Blueprint, not a `UBlueprintSubsystem`), seeded from `/Game/Data/DT_DefenseBlueprints` (6 rows: SpikeTrap, SwingingTrap, Turret, Barricade, SlowStrip, GasTrap — SpikeTrap/SwingingTrap `bUnlockedByDefault=true`). Landed fac8297. Kiosk integration (Turret/Barricade/SlowStrip/GasTrap purchasable via `DT_KioskCatalog` `FulfillmentType=Blueprint`, calling `Server_UnlockBlueprint` from `BP_PlayerController_ZombieStore`) landed alongside commit 8d9d9a4. SwingingTrap has no `BP_DefenseBase` subclass yet (see 3.2).

[x] 2.3 Place-Defense RPC

Status: `Server_PlaceDefenseOnSocket(TargetSocket, DefenseClass)` implemented on `BP_PlayerController_ZombieStore` (Blueprint body behind a C++ `BlueprintImplementableEvent` scaffold from fac8297) — validates DayPhase, unoccupied socket, matching `AllowedSocketType`, looks up `DT_DefenseBlueprints.Cost` by `BlueprintID`, deducts `StoreCash`, spawns/attaches the `BP_DefenseBase` subclass onto the socket, sets `OwningSocket`/`OccupyingDefense`/`bIsOccupied`. Landed commit da31cb4. Not yet callable from gameplay — see 2.1's remaining gap (no confirm-placement input wired up yet).

[x] 3.1 Defense Base Actor (ADefenseBase)

Status: Built as `/Game/Defense/BP_DefenseBase` (Blueprint). Node-attached via `OwningSocket` ref; `AllowedSocketType` (E_DefenseSocketType); replicated `Health`/`MaxHealth` (in place of a separate `UHealthComponent` — inline on the actor per this project's lighter-weight convention); implements `BPI_Breachable::ApplyBreachDamage` so the existing zombie-attack non-ASC damage path works unmodified; `OnDefenseDestroyed()` clears the owning socket and self-destroys. Landed commit 8d9d9a4.

[x] 3.2 Defense Type Behaviors

Status:
- Floor — Spike Trap: done, `/Game/Defense/BP_Trap_Spike` (commit da31cb4). Applies `GE_TrapDamage` to overlapping zombies via GAS, loses its own Health/durability per activation.
- Floor — Slow Strip: done. `/Game/GASDocumentation/Characters/Shared/GameplayEffectTemplates/GE_Slow` built (HasDuration 3.0s, Multiply modifier on `GDAttributeSetBase.MoveSpeed` ×0.5, grants `State.Debuff.Slow`, AggregateBySource, StackLimit 1, RefreshOnSuccessfulApplication) and `/Game/Defense/BP_Trap_SlowStrip` wired to apply it on server-side zombie overlap (overlap → HasAuthority → Cast to BP_ZombieBase → GetAbilitySystemComponent → MakeEffectContext → MakeOutgoingSpec(GE_Slow, 1.0) → ApplyGameplayEffectSpecToTarget).
- Wall — Swinging Blade/Mallet Trap: done, `/Game/Defense/BP_Trap_Swinging` (parented to `BP_DefenseBase`, `AllowedSocketType`=Wall). Mirrors `BP_Trap_Spike`'s overlap→GAS-damage→self-durability-loss pattern, reusing `GE_TrapDamage`. `DT_DefenseBlueprints.SwingingTrap.DefenseClass` populated.
- TurretBase — Automated Turret: done, `/Game/Defense/BP_Turret_Automated` (parented to `BP_DefenseBase`, `AllowedSocketType`=TurretBase). Sphere-overlap detection (800 unit radius) + a 1s repeating server timer applies `GE_TrapDamage` to the first detected `BP_ZombieBase` in range; timer cleared on EndPlay/destroy. No self-durability loss (Health only depletes via `ApplyBreachDamage` from zombie attacks, same as base class). `DT_DefenseBlueprints.Turret.DefenseClass` populated.
- Other — Barricade: done, `/Game/Defense/BP_Barricade` (parented to `BP_DefenseBase`, `AllowedSocketType`=Other). Pure static blocker, no attack logic — CDO `MaxHealth`/`Health` set to 250 (~2.5x a trap's baseline). `DT_DefenseBlueprints.Barricade.DefenseClass` populated.
- Other — Gas Trap: done, `/Game/Defense/BP_Trap_Gas` (parented to `BP_DefenseBase`, `AllowedSocketType`=Other). Structural mirror of `BP_Trap_SlowStrip`'s overlap→GAS pattern, applying the same `GE_Slow` effect (no self-durability loss, matching SlowStrip). `DT_DefenseBlueprints.GasTrap.DefenseClass` populated.

All 6 `DT_DefenseBlueprints` rows now have a populated `DefenseClass`. None of the 5 new/updated defense actors have been verified in PIE yet — recommend a playtest pass placing each on its socket type and confirming zombie overlap triggers the expected GAS effect (damage or slow) and, for traps, self-destruction on durability loss.

4. Node Repair, Upgrade & Selling System

[x] 4.1 In-Build Mode Node Management

Status: Done. `Server_RepairDefense`/`Server_SellDefense` implemented on `BP_PlayerController_ZombieStore` (commit da31cb4) — repair costs `DT_DefenseBlueprints.RepairCostPerHP × missing HP` (flat 25 fallback on row-lookup miss), sell refunds `Cost × SellRefundPercent` (same flat-25 fallback), both gated by `StoreCash` affordability. UI/interaction wiring landed this session: `/Game/UI/WBP_BuildMenu` gained a contextual `RepairSellBox` panel (status text + Repair/Sell buttons), bound to `BP_BuildModeComponent.OnTargetSocketChanged` — shows/hides based on whether the traced socket is occupied and displays the occupying defense's `Health`/`MaxHealth`; button clicks call `Server_RepairDefense`/`Server_SellDefense` with the tracked socket. Compiles clean, saved. Untested in PIE.

Acceptance Criteria

Building restricted pre-defined node locations (Floor, Wall, TurretBase, Other) only activated during Day Phase by pressing B. Met for the toggle/gating; not yet met end-to-end since placement still has no input path from build-menu selection to the socket RPC (see 2.1/2.3 gap).

Players start each run with basic blueprints (Spike Trap, Swinging Trap) unlocked. Partially met: unlock-registry defaults are correct, but Swinging Trap has no placeable actor class yet (see 3.2).

Sockets auto-target/highlight while in Build Mode. Met (1.2).

Next up: only confirm-placement input (closes 2.1/2.3) remains, and it's blocked behind the `OnBlueprintSelected` dispatcher-binding issue above (needs a manual editor fix — see 2.1). Everything else in this phase (3.2, the Slow Strip GameplayEffect, and 4.1's Repair/Sell UI) is complete.

5. Playtest Map Population (`/Game/GASDocumentation/Maps/Map_Startup`)

Status: Done, 3 passes, saved to disk. The startup map (both `GameDefaultMap` and `EditorStartupMap`) now has all actors needed to playtest Phases 3/4 end-to-end:
- Pass 1 (core gameplay): 8 `BP_DefenseSocket` instances, 2 per `SocketType` (Floor/Wall/TurretBase/Other), placed around the existing east-wall doorway so all 6 `DT_DefenseBlueprints` defense types have a valid socket to test on; 4 `BP_ShelfActor` + a `Shop_Counter` primitive near the existing `BP_ShopStation_Base`; 3 `BP_CustomerSpawnPoint` markers plus 1 `BP_CustomerSpawner` instance.
- Pass 2 (structure): two `1M_Cube` primitive partition walls (`Partition_Shop_West`/`Partition_Shop_East`) with a doorway gap, visually separating the shop room from the main hall/breach corridor, matching the existing wall mesh/scale convention.
- Pass 3 (decor): primitive crates, barrels flanking the main doorway, and the shop counter for visual detail.
- Pre-existing content (untouched, not built this pass): perimeter walls/doorway, 2 `PlayerStart`s, `BP_ShopStation_Base`, 2 `BP_ItemPickup`s, 8 zombie `TargetPoint`s already wired into `BP_ZombieSpawnerManager.SpawnPoints`, and 2 `BP_BreachPoint`s.
- Known minor issue: one decorative barrel actor landed with an auto-generated name/no outliner folder (cosmetic only, no gameplay impact).
- Untested in PIE — recommended playtest pass: walk through the doorway and confirm zombies spawn/path via the TargetPoints and attack through the breach points; enter Build Mode at each of the 8 new sockets and confirm the correct defense type is placeable per socket type (still blocked overall on the 2.1 dispatcher-binding gap above); confirm shelves/shop station/item pickups are interactable; confirm the customer spawner produces customers that path toward the shop; rebuild the navmesh (`RecastNavMesh-Default`) and confirm the new interior partition doesn't block navigation, since it was added after the last bake.
