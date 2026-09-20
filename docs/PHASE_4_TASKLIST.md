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

Status: Done. `IA_ToggleBuildMode` bound to `B` in `IMC_Default`. `BP_PlayerController_ZombieStore` gates the toggle to `CurrentPhase == DayPhase` and force-exits `bBuildModeActive` via a bound `OnPhaseChanged` handler whenever the phase leaves Day. Landed in commit 8d9d9a4. `/Game/UI/WBP_BuildMenu` + `WBP_BuildEntry` (grid, not radial/carousel — deviation from the doc's wording) show unlocked/locked `DT_DefenseBlueprints` rows and expose `SelectedBlueprintID`/`OnBlueprintSelected`. Landed in commit da31cb4. Widget open/close lifecycle (`AddToViewport`/`RemoveFromParent` on Build Mode enter/exit, including the phase-change force-exit path) already landed in commit 539e21e — verified still correct.

**Dispatcher-binding blocker resolved:** `BP_PlayerController_ZombieStore.HandleBuildMenuBlueprintSelected(BlueprintID: Name)` is now bound to `WBP_BuildMenu`'s `OnBlueprintSelected` event dispatcher via a `K2Node_CreateDelegate`/`K2Node_AddDelegate` pair in `OpenBuildMenu`, wired to an intermediate `OnBuildMenuBlueprintSelected_Handler` Custom Event. Root cause was a Monolith engine-interaction bug, not a hand-editing limitation: `UK2Node_CreateDelegate::HandleAnyChangeWithoutNotifying()` runs automatically the moment the node's `self` pin gets connected, and at that point (before the delegate output pin is wired) it silently wipes `SelectedFunctionName` back to `NAME_None`, permanently breaking the binding. Fixed by adding a new Monolith action, `blueprint.finalize_create_delegate`, which re-applies `SetFunction()` immediately before calling the engine's own resolution logic, run only after both the `self` and delegate pins are fully wired. Verified `is_valid: true`, `selected_function_name` match, `compile_blueprint` 0 errors, saved.

**Confirm-placement input landed:** new `IA_ConfirmPlacement` InputAction (Boolean), mapped to `F` in `IMC_Default` (LMB/RMB/E were already taken by `IA_PrimaryAction`/`IA_SecondaryAction`/`IA_Interact`). Bound in `BP_PlayerController_ZombieStore` (Started event) alongside `IA_ToggleBuildMode`: branches on `bBuildModeActive`, casts the controlled pawn to `BP_HeroCharacter`, reads `BuildModeComponent.GetPlacementRequest()` (`TargetSocket`/`DefenseClass`/`bValid`), and on a valid request with a non-null `DefenseClass` calls `Server_PlaceDefenseOnSocket(TargetSocket, DefenseClass)`. Compiled 0 errors, all touched assets saved. Untested in PIE — needs a playtest pass pressing `F` in Build Mode with a blueprint selected and a valid unoccupied socket targeted (expect spawn + cash deduction), and confirming it no-ops with Build Mode off, no selection, or an invalid/occupied socket.

[x] 2.2 Blueprint Registry & Progression Engine (UBlueprintSubsystem)

Status: Implemented as a replicated `UnlockedBlueprintIDs` array + `IsBlueprintUnlocked`/`Server_UnlockBlueprint` on `BP_GameState_ZombieStore` (Blueprint, not a `UBlueprintSubsystem`), seeded from `/Game/Data/DT_DefenseBlueprints` (6 rows: SpikeTrap, SwingingTrap, Turret, Barricade, SlowStrip, GasTrap — SpikeTrap/SwingingTrap `bUnlockedByDefault=true`). Landed fac8297. Kiosk integration (Turret/Barricade/SlowStrip/GasTrap purchasable via `DT_KioskCatalog` `FulfillmentType=Blueprint`, calling `Server_UnlockBlueprint` from `BP_PlayerController_ZombieStore`) landed alongside commit 8d9d9a4. SwingingTrap has no `BP_DefenseBase` subclass yet (see 3.2).

[x] 2.3 Place-Defense RPC

Status: `Server_PlaceDefenseOnSocket(TargetSocket, DefenseClass)` implemented on `BP_PlayerController_ZombieStore` (Blueprint body behind a C++ `BlueprintImplementableEvent` scaffold from fac8297) — validates DayPhase, unoccupied socket, matching `AllowedSocketType`, looks up `DT_DefenseBlueprints.Cost` by `BlueprintID`, deducts `StoreCash`, spawns/attaches the `BP_DefenseBase` subclass onto the socket, sets `OwningSocket`/`OccupyingDefense`/`bIsOccupied`. Landed commit da31cb4. Now callable from gameplay via the `IA_ConfirmPlacement` (`F`) input added under 2.1 — end-to-end path from build-menu selection to placement is complete, untested in PIE.

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

Building restricted pre-defined node locations (Floor, Wall, TurretBase, Other) only activated during Day Phase by pressing B. Met end-to-end: toggle/gating, dispatcher-bound selection, and confirm-placement (`F`) → `Server_PlaceDefenseOnSocket` are all wired and compile clean. Untested in PIE.

Players start each run with basic blueprints (Spike Trap, Swinging Trap) unlocked. Partially met: unlock-registry defaults are correct, but Swinging Trap has no placeable actor class yet (see 3.2).

Sockets auto-target/highlight while in Build Mode. Met (1.2).

Next up: all Phase 4 build items (1.1–4.1) are implemented and compile clean. Nothing remains but the PIE playtest pass described under section 5 below — no further build work is blocking this phase.

4.2 Project HUD (`WBP_HUD`) — unplanned, not in the original task breakdown

Status: Done, compiles clean, committed 3545fa8. `/Game/UI/WBP_HUD` subclasses `UGDHUDWidget` (the GAS sample HUD) and adds a live ammo readout (`Ammo_Current`/`Ammo_Reserve`, hidden for non-gun slots) alongside the existing health/stamina bars and ability confirm/cancel text. Fed by `BP_EquipmentComponent.OnEquipmentUpdated`/`OnActiveSlotChanged` (broadcast from every mutating path, including OnReps, so remote clients update too). `BP_HeroCharacter` grants the starting loadout then broadcasts a new `OnPawnEquipmentReady` dispatcher on `BP_PlayerController_ZombieStore` so the HUD can bind even if it constructs before the pawn's equipment is ready — `WBP_HUD` falls back to that dispatcher on Construct if the equipment component isn't valid yet. Both `BP_PlayerController_ZombieStore` and the sample `BP_PlayerController` now point `UIHUDWidgetClass` at `WBP_HUD` (the sample PC isn't on the live path — `BP_GameMode_ZombieStore` is — so that change is harmless but not load-bearing). No cash/day-phase/build-mode HUD elements yet — out of scope for this pass. Untested in PIE.

5. Playtest Map Population (`/Game/GASDocumentation/Maps/Map_Startup`)

Status: Done, 3 passes, saved to disk. The startup map (both `GameDefaultMap` and `EditorStartupMap`) now has all actors needed to playtest Phases 3/4 end-to-end:
- Pass 1 (core gameplay): 8 `BP_DefenseSocket` instances, 2 per `SocketType` (Floor/Wall/TurretBase/Other), placed around the existing east-wall doorway so all 6 `DT_DefenseBlueprints` defense types have a valid socket to test on; 4 `BP_ShelfActor` + a `Shop_Counter` primitive near the existing `BP_ShopStation_Base`; 3 `BP_CustomerSpawnPoint` markers plus 1 `BP_CustomerSpawner` instance.
- Pass 2 (structure): two `1M_Cube` primitive partition walls (`Partition_Shop_West`/`Partition_Shop_East`) with a doorway gap, visually separating the shop room from the main hall/breach corridor, matching the existing wall mesh/scale convention.
- Pass 3 (decor): primitive crates, barrels flanking the main doorway, and the shop counter for visual detail.
- Pre-existing content (untouched, not built this pass): perimeter walls/doorway, 2 `PlayerStart`s, `BP_ShopStation_Base`, 2 `BP_ItemPickup`s, 8 zombie `TargetPoint`s already wired into `BP_ZombieSpawnerManager.SpawnPoints`, and 2 `BP_BreachPoint`s.
- Known minor issue: one decorative barrel actor landed with an auto-generated name/no outliner folder (cosmetic only, no gameplay impact).
- Untested in PIE — recommended playtest pass: walk through the doorway and confirm zombies spawn/path via the TargetPoints and attack through the breach points; enter Build Mode at each of the 8 new sockets and confirm the correct defense type is placeable per socket type (still blocked overall on the 2.1 dispatcher-binding gap above); confirm shelves/shop station/item pickups are interactable; confirm the customer spawner produces customers that path toward the shop; rebuild the navmesh (`RecastNavMesh-Default`) and confirm the new interior partition doesn't block navigation, since it was added after the last bake.

6. Post-Playtest Fix Pass (4 issues reported after the first Phase 4 playtest)

Status: all 4 done, unverified in PIE (overnight/unattended session — user was asleep, per standing unattended-run rules).

- Shop terminal not interactable → fixed. Root cause was the same class of bug as the shelf fix below: `GA_Interact`'s `Has Authority`-gated `OnInteract` body silently no-op'd on non-host clients. Kiosk now opens a purchasable items/weapons list plus purchasable blueprints that unlock buildings for the whole run (`BP_DiscountKiosk` + `DT_KioskCatalog`). Committed `9deb32c`.
- Shelves not interactable → fixed, **with one deviation from the literal request**: the ask was drag-and-drop from inventory into shelf slots; this was blocked by a confirmed Monolith MCP tooling gap — `blueprint.add_node` has no support for `ConstructObjectFromClass`/any object-construction node type, which a custom `DragDropOperation` subclass requires (see `monolith-editor-crash-triggers` memory, item 5). Substituted click-to-transfer (click an inventory item to select it, click a shelf slot to stock/take) — functionally equivalent but not literally "drag." Shelf UI (`WBP_ShelfPanel`/`WBP_ShelfSlot`) shows per-slot item/qty and the alike-items matching-bonus multiplier, plus a category-match bonus. Committed `65d1114`. An inert orphaned asset, `BP_ItemDragOperation` (abandoned drag subclass, undeletable via Monolith, zero references), remains in `Content/UI/` from the aborted attempt.
- Upgradable shelves → fixed. 5-tier system (Tier0 4 slots → Tier4 16 slots, costs $100/$150/$250/$400/free-topped-out) driven by new `S_ShelfTier`/`DT_ShelfTiers`. `BP_ShelfActor` gained a replicated `ShelfTier` resizing `StockedItems` and toggling 16 slot-mesh components; `Server_UpgradeShelf` RPC on `BP_PlayerController_ZombieStore` validates affordability via `GameState.CanAfford`/`Server_DeductCash`; `WBP_ShelfPanel` gained an Upgrade button + cost/next-tier readout, disabled at top tier. Retired the old unimplemented `ShelfExpansion` kiosk row as part of this (confirmed dead code first). Committed `37add2e`.
- Night phase ending on a fixed timer → fixed. Night phase now ends only when the zombie count hits zero rather than after a fixed duration. Committed `c9e30e8`.

Needs a manual PIE playtest pass covering, as a non-host client where noted:
- Shop terminal purchase flow as a non-host client.
- Shelf click-to-transfer stocking/taking as a non-host client — and confirm whether true drag-and-drop feel is wanted badly enough to revisit later (would need a C++ static factory function to construct the `DragDropOperation`, since Monolith can't author that node).
- Shelf tier upgrade flow: cost readout, slot count changing live (4→6→8→12→16), and the "Max Tier" disabled state at Tier4.
- Night-phase zombie-count-based end condition, including the failsafe-timer and defense-kill edge cases.
