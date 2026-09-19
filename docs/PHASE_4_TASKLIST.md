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

[x] 2.2 Blueprint Registry & Progression Engine (UBlueprintSubsystem)

Status: Implemented as a replicated `UnlockedBlueprintIDs` array + `IsBlueprintUnlocked`/`Server_UnlockBlueprint` on `BP_GameState_ZombieStore` (Blueprint, not a `UBlueprintSubsystem`), seeded from `/Game/Data/DT_DefenseBlueprints` (6 rows: SpikeTrap, SwingingTrap, Turret, Barricade, SlowStrip, GasTrap — SpikeTrap/SwingingTrap `bUnlockedByDefault=true`). Landed fac8297. Kiosk integration (Turret/Barricade/SlowStrip/GasTrap purchasable via `DT_KioskCatalog` `FulfillmentType=Blueprint`, calling `Server_UnlockBlueprint` from `BP_PlayerController_ZombieStore`) landed alongside commit 8d9d9a4. SwingingTrap has no `BP_DefenseBase` subclass yet (see 3.2).

[x] 2.3 Place-Defense RPC

Status: `Server_PlaceDefenseOnSocket(TargetSocket, DefenseClass)` implemented on `BP_PlayerController_ZombieStore` (Blueprint body behind a C++ `BlueprintImplementableEvent` scaffold from fac8297) — validates DayPhase, unoccupied socket, matching `AllowedSocketType`, looks up `DT_DefenseBlueprints.Cost` by `BlueprintID`, deducts `StoreCash`, spawns/attaches the `BP_DefenseBase` subclass onto the socket, sets `OwningSocket`/`OccupyingDefense`/`bIsOccupied`. Landed commit da31cb4. Not yet callable from gameplay — see 2.1's remaining gap (no confirm-placement input wired up yet).

[x] 3.1 Defense Base Actor (ADefenseBase)

Status: Built as `/Game/Defense/BP_DefenseBase` (Blueprint). Node-attached via `OwningSocket` ref; `AllowedSocketType` (E_DefenseSocketType); replicated `Health`/`MaxHealth` (in place of a separate `UHealthComponent` — inline on the actor per this project's lighter-weight convention); implements `BPI_Breachable::ApplyBreachDamage` so the existing zombie-attack non-ASC damage path works unmodified; `OnDefenseDestroyed()` clears the owning socket and self-destroys. Landed commit 8d9d9a4.

[ ] 3.2 Defense Type Behaviors

Status:
- Floor — Spike Trap: done, `/Game/Defense/BP_Trap_Spike` (commit da31cb4). Applies `GE_TrapDamage` to overlapping zombies via GAS, loses its own Health/durability per activation.
- Floor — Slow Strip: partially done, `/Game/Defense/BP_Trap_SlowStrip` (commit da31cb4) detects zombie overlap server-side only — no slow GameplayEffect exists anywhere in this project yet, so it currently applies no actual slow. Needs a `GE_Slow`-style GameplayEffect (or equivalent) built before this trap does anything.
- Wall — Swinging Blade/Mallet Trap: not started. No `BP_DefenseBase` subclass, no `DT_DefenseBlueprints` `DefenseClass` reference, and the SwingingTrap row itself was never given a kiosk-purchase path (it's a free starter, so that's expected, but the actor class still doesn't exist).
- TurretBase — Automated Turret: not started.
- Other — Barricade, Gas Trap: not started (Barricade/GasTrap kiosk purchase + unlock flow exists per 2.2, but no `BP_DefenseBase` subclass to actually spawn).

4. Node Repair, Upgrade & Selling System

[x] 4.1 In-Build Mode Node Management

Status: `Server_RepairDefense`/`Server_SellDefense` implemented on `BP_PlayerController_ZombieStore` (commit da31cb4) — repair costs `DT_DefenseBlueprints.RepairCostPerHP × missing HP` (flat 25 fallback on row-lookup miss), sell refunds `Cost × SellRefundPercent` (same flat-25 fallback), both gated by `StoreCash` affordability. Not yet wired to any UI/input — there's no in-Build-Mode "look at occupied socket → see Repair/Sell options" interaction built yet; only the server-side RPC logic exists. That UI/interaction wiring is the remaining piece of this task.

Acceptance Criteria

Building restricted pre-defined node locations (Floor, Wall, TurretBase, Other) only activated during Day Phase by pressing B. Met for the toggle/gating; not yet met end-to-end since placement still has no input path from build-menu selection to the socket RPC (see 2.1/2.3 gap).

Players start each run with basic blueprints (Spike Trap, Swinging Trap) unlocked. Partially met: unlock-registry defaults are correct, but Swinging Trap has no placeable actor class yet (see 3.2).

Sockets auto-target/highlight while in Build Mode. Met (1.2).

Next up (not yet started): confirm-placement input (closes 2.1/2.3), Repair/Sell in-Build-Mode UI (closes 4.1), Wall/TurretBase/Other defense subclasses (3.2 remainder), and a slow GameplayEffect for Slow Strip.
