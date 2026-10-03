# Freeform Building: architect plan (feature/freeform-building)

## 1. Goal
Replace socket-based defense placement with free placement. Players put floor items inside `BP_BuildArea` volumes and wall items on interior static walls, within about 6 m. The ghost preview turns green or red and the HUD shows the reason. Floor items rotate in 90° steps. Turret and Barricade block pathing, and zombies attack them only while they block a path. A destroyed buildable leaves a ghost that can be rebuilt or removed. Traps can be moved. Saves store buildables by transform. All of this follows `docs/FREEFORM_BUILDING_DECISIONS.md`.

## 2. Existing infrastructure to reuse (paths verified)

**Defense actors (/Game/Defense/)**
- `BP_DefenseBase` (implements `/Game/Interactable/BPI_Breachable`).
- `BP_BuildGhost` (GhostMesh/GhostMeshB; SetGhostShape, SetGhostValid, SetGhostDefense).
- `BP_Turret_Automated`, `BP_Barricade`, `BP_Trap_Spike`, `BP_Trap_Swinging`, `BP_Trap_SlowStrip`, `BP_Trap_Gas`.
- `Materials/M_BuildGhost`.
- `BP_DefenseSocket` is retired in the last task.

**Build mode and player controller**
- `/Game/Characters/BP_BuildModeComponent`. It sits on the PC as variable `BuildModeComponent` and is used by the PC and WBP_BuildMenu.
- `/Game/Core/PlayerControllers/BP_PlayerController_ZombieStore`, with C++ parent GDPlayerController. Its `Server_SellDefense(AActor*)` and BIE `OnServerSellDefense` are kept. `Server_PlaceDefenseOnSocket` stays declared but goes dead.
- The PC already has these, all verified:
  - `GetInteractKeyText() -> KeyText:Text` (pure, uses QueryKeysMappedToAction).
  - `IsUICloseKey`.
  - GetAimedPlacedDefense, GetAimedDamagedDefense, GetAimedInteractPromptText, GetHoldBarProgress.
  - ShowOwnerStatusMessage, CloseTrapPanelUI.
  - A door/breach hold-E pattern.
- `/Game/Core/Components/BP_TutorialComponent.GetKeyTextForAction(Action:InputAction) -> KeyText` (pure). This is what fills `{Key}` in tutorial text.

**Game state and data**
- `/Game/Core/GameStates/BP_GameState_ZombieStore`:
  - Defense and save: GatherPlacedDefenses, RestorePlacedDefenses, IsBlueprintUnlocked.
  - Cash: CanAfford, Server_DeductCash, Server_AddCash.
  - Other: RecordCustomerLost.
  - Phase: CurrentPhase, where E_GamePhase is 0 Day, 1 Night, 2 RunOver, 3 Morning, 4 Dusk. Build is allowed when the phase is neither 1 nor 2.
- `/Game/Data/DT_DefenseBlueprints` with row struct `/Game/Data/S_DefenseBlueprintEntry` (SocketType, DefenseClass, Cost, SellRefundPercent, ...).
- `/Game/Data/E_DefenseSocketType` (0 Floor, 1 Wall, 2 TurretBase, 3 Other).
- `/Game/Data/Save/S_SavedDefense`.

**AI**
- `/Game/Characters/AI/`: BB_Zombie, BT_Zombie, BTS_ZombieBreachDecision (pattern source), BTT_ZombieMeleeAttack, AIC_Zombie, BP_StoreInteriorVolume.
- `/Game/AI/Customer/AIC_Customer`.
- `/Game/Characters/BP_ZombieAttackComponent`.
- `/Game/Characters/BP_Customer` (HandlePatienceTimeout → bHandled, ExitLocation; BeginLeaveStore).
- `DefaultNavigationFilterClass` is None on both AIC_Zombie and AIC_Customer (verified).

**Input, UI, tutorial**
- `/Game/Characters/Input/IMC_Default` and `IA_ToggleBuildMode`.
- `/Game/UI/WBP_HUD`, `WBP_BuildMenu`, `WBP_TrapPanel`.
- `/Game/Data/Tutorial/DT_TutorialGoals`, `DT_CodexEntries`.

**Other**
- `/Game/Interactable/BP_BreachPoint`. Doors are breach points; there is no separate door BP.
- Tests: `/Game/Tests/Automation/Blueprints/BP_TestController`, `/Game/Tests/Automation/Data/DT_AutomationTests`, `/Game/Tests/Automation/Maps/L_AutomationTestBed`, `Tools/TestSuites/make_suite_maps.py`.

## 3. New classes and assets

**C++ (one task, `Source/GASDocumentation/`)**
- `UGDBuildPlacementLibrary` (BlueprintFunctionLibrary). It holds the placement geometry: tracing, slope, area containment, tag-overlap and physical-overlap checks. Both the client preview and the server validation call the same function. In Blueprint this would be a 60+ node graph with nested loops, which would be fragile to build through Monolith.
- `UGDNavArea_DefenseBlocker` (UNavArea) and `UGDNavFilter_AvoidDefenseBlockers` (UNavigationQueryFilter). These are config-only classes. C++ avoids editing an array-of-struct CDO through Monolith and rides on the same compile.
- `Build.cs` gets the private dependency `NavigationSystem`.

**Blueprint**
- `/Game/Defense/BP_BuildArea` (new).
- `/Game/Defense/BP_DefenseGhost` (new, child of BP_BuildGhost).
- `/Game/Characters/Input/IA_RotateBuildable` (new).
- `/Game/Characters/AI/BTS_ZombieBlockerDecision` (new).
- Everything else is an edit to an existing asset.

## 4. Replication and ownership (listen server, server-authoritative)

| State | Owner | Replication |
|---|---|---|
| Placed buildables (spawn, move, destroy) | Server | Actor replicates (already). `bReplicateMovement=true` is new, so Move shows on clients. |
| `BP_DefenseGhost` and its Ghost* vars | Server spawns | `bReplicates=true`. GhostBlueprintID is RepNotify → visual. Tier, TotalSpent and Class replicate. |
| `bBlocksPath`, `PlacementExtent`, `PreviewRadius` | CDO constants | Not replicated. They are class defaults. |
| `LastPathBlockTime` | Server only (the BT service writes it) | Not replicated. Only the damage gate reads it, and that runs on the server. |
| Placement preview, PlacementYawDegrees, MovingDefense, PlacementFailReason, radius ring | Owning client | Local only. The server re-validates the transform with 75 cm range slack. |
| Ghost-hold vars (GhostHoldTarget, GhostHoldStartTime, timer) | Owning client | Local. Completion sends a reliable Server RPC. |
| `BP_BuildArea` | Level | Not replicated. It exists in the map on every machine, and both sides query it. |
| Customer route-give-up vars | Server | Not replicated. AI runs only on the server. |
| New RPCs on the PC | Client→Server reliable: Server_PlaceDefenseAt, Server_MoveDefense, Server_RebuildGhost, Server_RemoveGhost. Server→Owning Client reliable: Client_BuildRejected(Reason). | |

## 5. Risk flags

1. **Transient compile breaks between tasks.**
   - Task 18 changes the BuildModeComponent API. The PC (20), WBP_BuildMenu (25) and BP_TestController (39) won't compile until their own tasks land.
   - Builders after 18 must expect errors in *other* assets and must not fix them.
   - Checkpoints C3 and C6 must be green before commit.
2. **Nav.** Turret and Barricade nav marking needs dynamic runtime generation (BUGS.md L556). Task 33 only reports RecastNavMesh RuntimeGeneration and does not edit it, because the map has hand edits. If it is not Dynamic, the orchestrator logs it as a BUG for the user. The final manual test checks `show Navigation`.
3. **Perf.** BTS_ZombieBlockerDecision runs 2 sync path queries per zombie every 0.5 s, but only while at least one bBlocksPath defense exists. Worth checking during a horde in the manual test.
4. **Monolith gotchas** (from memory):
   - Pure functions need an entry→return exec wire.
   - The SpawnActor Class pin can be left unset. Check that ReturnValue is the concrete type.
   - IMC edits can stay unsaved. Byte-check the .uasset.
   - Never wire a ForEach back-edge.
   - Custom widget ForegroundColor can come out transparent.
   - BT BB decorators need OperationType set (Set=0).
5. **Hand-edited Map_Store_Outdoors.** Task 33 may only add BP_BuildArea actors and delete BP_DefenseSocket actors.
6. **Mesh orientation.**
   - Swinging trap: the wall-mount math assumes the mesh extends along actor +X out of the wall.
   - Floor items assume the pivot is at their base.
   - CDO tasks report these and don't fix them. Verified in the manual test.
7. **Pawns inside a new blocker.** The spec allows overlapping players and zombies. A Turret or Barricade placed on top of a pawn can trap it. This is accepted and logged.
8. **Floor items on raised fixtures.** A floor item can sit on top of a counter if the counter is inside a build area and the footprint fits under the area's top. This is accepted for v1 and logged.
9. **GDD.md L104 tension.** It plans "defense-targeting" zombies. This plan makes defenses attackable only while they block a path, so that future zombie type would need its own exception later. Flagged, not resolved here.
10. **Bloater/Spitter damage path.** I assume all zombie damage to defenses goes through `BPI_Breachable.ApplyBreachDamage`. Task 11 searches for other callers and reports them.
11. **Automation tests touched:**
    - Test_BuildModePlacementRequest
    - Test_BuildMode_ServerPlaceAllowedInDusk / _BlockedAtNight
    - Test_Audio_K3DefenseSoundsAssigned
    - Test_Defense_K4ReplicationEnabled
    - Test_Defense_K4SocketHighlight (deleted)
    - TU_*/SV_* socket helpers in BP_TestController
    - Tasks 39–41 handle all of these.

## 6. Task breakdown

The run is serial overnight, one builder at a time. "Parallel with" is informational.

---
### CHECKPOINT A: Foundation

### Task 1: Placement library, nav area, nav filter (C++)
- Agent: ue-cpp-builder
- Depends on: none   Parallel with: 4, 5, 6, 8
- Asset(s):
  - `Source/GASDocumentation/Public/GDBuildPlacementLibrary.h` + `Private/GDBuildPlacementLibrary.cpp` (new)
  - `Public/GDNavArea_DefenseBlocker.h` + `Private/GDNavArea_DefenseBlocker.cpp` (new)
  - `Public/GDNavFilter_AvoidDefenseBlockers.h` + `Private/GDNavFilter_AvoidDefenseBlockers.cpp` (new)
  - `Source/GASDocumentation/GASDocumentation.Build.cs` (edit)
- Read first: `GASDocumentation.Build.cs`. The private deps currently include AIModule and EnhancedInput, but not NavigationSystem. Use the API macro `GASDOCUMENTATION_API`.
- Do:
  - **Build.cs:** add `"NavigationSystem"` to PrivateDependencyModuleNames.
  - **`UGDNavArea_DefenseBlocker : UNavArea`.** Constructor sets `DefaultCost = 1.f` and `DrawColor = FColor(220,40,40)`. It must stay traversable for the default filter. Do not use the Null area.
  - **`UGDNavFilter_AvoidDefenseBlockers : UNavigationQueryFilter`.** Constructor calls `AddExcludedArea(UGDNavArea_DefenseBlocker::StaticClass())`.
  - **`UGDBuildPlacementLibrary : UBlueprintFunctionLibrary`**, all `UFUNCTION(BlueprintCallable/BlueprintPure, Category="NoBrainers|Build")`. Names are file-local constants.
    - **Constants:** RangeCm=600; MaxSlopeDeg=15; WallMaxAbsNormalZ=0.25; Shrink=2; DoorReserveXY=120; FloorProbeUp=20, FloorProbeDown=30, FloorProbeTolerance=10.
    - **`static float GetMaxBuildRange()`** (BlueprintPure). Returns 600.
    - **`static bool TraceBuildSurface(const UObject* WorldContextObject, FVector Start, FVector End, const TArray<AActor*>& IgnoreActors, FHitResult& OutHit)`** (BlueprintCallable, meta WorldContext).
      1. Runs `LineTraceMultiByObjectType` for ECC_WorldStatic + ECC_WorldDynamic, with IgnoreActors added to the query params.
      2. Iterates hits in order and returns the first one where:
         - the actor is not an APawn;
         - the actor is not in IgnoreActors;
         - the component is not simulating physics;
         - `Component->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block`.
      3. Sets `OutHit.bBlockingHit=true` and returns true. If no hit qualifies it returns false.
    - **`static bool ComputePlacementTransform(const FHitResult& AimHit, bool bIsWallItem, float YawDegrees, FTransform& OutTransform, FText& OutFailReason)`** (BlueprintPure).
      - Let N be `AimHit.ImpactNormal`.
      - If `!AimHit.bBlockingHit`: OutTransform = identity at TraceEnd, reason "Nothing to aim at", return false.
      - Floor items:
        - Rotation = `FRotationMatrix::MakeFromZX(N, FVector(cos(yaw), sin(yaw), 0))`.
        - If `N.Z < cos(15°)`, reason "Too steep" and return false.
      - Wall items:
        - H = N with Z zeroed, then normalized. If H is near zero, use (1,0,0).
        - Rotation = `MakeFromXZ(H, FVector::UpVector)`.
        - Fail with "Needs a wall" if `|N.Z| > 0.25` or the hit component's `GetCollisionObjectType()!=ECC_WorldStatic`.
      - Location = ImpactPoint.
      - Always write a best-effort OutTransform. On success, the reason is empty.
    - **`static bool ValidatePlacement(const UObject* WorldContextObject, const FTransform& PlacementTransform, bool bIsWallItem, FVector PlacementExtent, FVector ViewerLocation, float RangeSlack, const TArray<AActor*>& IgnoreActors, FText& OutFailReason)`** (BlueprintCallable).
      - **Setup:**
        - E = PlacementExtent.
        - Local footprint center C = (0,0,E.Z) for floor items, (E.X,0,0) for wall items.
        - Footprint = oriented box (PlacementTransform, C, E).
      - Checks run in this order and the first failure returns false:
        1. **Range.** `Dist(ViewerLocation, Location) > 600 + RangeSlack` → "Too far".
        2. **Surface.**
           - Floor: Up = Transform.GetUnitAxis(Z). If `Up.Z < cos(15°) - 0.001` → "Too steep". Then TraceBuildSurface from Loc+Up*20 to Loc-Up*30 (same IgnoreActors). It must hit with `|hit.Location - Loc| <= 10`, otherwise "Needs a floor".
           - Wall: Fwd = Transform X axis. If `|Fwd.Z| > 0.25` → "Needs a wall". TraceBuildSurface from Loc+Fwd*10 to Loc-Fwd*20 must hit a component whose object type is WorldStatic, otherwise "Needs a wall".
        3. **Area.**
           - Gather every `UBoxComponent` on actors that have tag `BuildArea`.
           - Test 9 points: the 8 corners of the footprint shrunk by 2 cm per axis, plus the center.
           - A point is inside a box when, with P' = `Box->GetComponentTransform().InverseTransformPosition(P)`, |P'| ≤ `Box->GetUnscaledBoxExtent()` on every axis.
           - Every point must be inside at least one box. The boxes can differ per point, which is how overlapping volumes union. Otherwise → "Outside store".
        4. **Tag pass.**
           - Footprint world AABB = AABB of its 8 corners, shrunk 2 cm.
           - Single `TActorIterator<AActor>` pass. Skip IgnoreActors. Per actor, take the union of `Bounds.GetBox()` for every `UMeshComponent` that `IsVisible()`, shrunk 2 cm.
           - Tag `Buildable` intersecting → "Overlaps a buildable".
           - Tag `BuildGhost` intersecting → "Overlaps a ghost".
           - Tag `BuildReserve`: expand its box by 120 in X and Y first, then if it intersects → "Blocks a door".
           - Use strict intersection, so boxes that only touch don't count. Shared faces fail strict overlap after the shrink.
        5. **Physical pass.**
           - `OverlapMultiByObjectType` with an FCollisionShape box of extent E−1 at the footprint center, offset +2 cm along the surface normal (Up for floor items, Fwd for wall items), using the footprint rotation.
           - Object types: WorldStatic, WorldDynamic, PhysicsBody, Destructible.
           - Skip:
             - APawn owners;
             - actors tagged Buildable, BuildGhost, BuildReserve, BuildArea or BuildIgnore;
             - IgnoreActors;
             - components simulating physics;
             - components whose Pawn response isn't Block.
           - The first remaining hit decides the reason: an `AStaticMeshActor` owner → "Overlaps a wall", anything else → "Overlaps an object".
      - If every check passes, empty the reason and return true.
    - **`static bool IsPointInBuildArea(const UObject* WorldContextObject, FVector Point)`** (BlueprintPure). Uses the same containment test as check 3.
    - **`static bool GetBuildableDefaults(TSubclassOf<AActor> DefenseClass, FVector& OutPlacementExtent, float& OutPreviewRadius, bool& bOutBlocksPath)`** (BlueprintPure).
      - Defaults are (50,50,40), 0 and false.
      - If the class is null, return false.
      - From the CDO, read by name via FindFProperty:
        - `PlacementExtent` (FStructProperty FVector).
        - `PreviewRadius`. It can be an FDoubleProperty, since Blueprint floats are doubles, or an FFloatProperty.
        - `bBlocksPath` (FBoolProperty).
      - Return true if the CDO was valid.
- Don't touch: GDPlayerController and other existing C++. Don't remove any socket RPCs.
- Report: in NOTES, state that the nav area and filter are C++ for convenience (they ride the same compile), not necessity; they could be Blueprint classes.
- Done when: the editor build compiles with 0 errors, and `cppreflect_query list_ufunctions` on GDBuildPlacementLibrary shows all 6 functions.
- Needs user test: no

### Task 2: AIC_Zombie default nav filter
- Agent: ue-blueprint-builder
- Depends on: 1   Parallel with: 3
- Asset(s): `/Game/Characters/AI/AIC_Zombie` (edit)
- Read first: `DefaultNavigationFilterClass` is currently None (verified).
- Do: set CDO `DefaultNavigationFilterClass` = `/Script/GASDocumentation.GDNavFilter_AvoidDefenseBlockers`.
- Don't touch: BT reference, graphs.
- Done when: get_cdo_properties shows the new value; compiled and saved.
- Needs user test: no

### Task 3: AIC_Customer default nav filter
- Agent: ue-blueprint-builder
- Depends on: 1   Parallel with: 2
- Asset(s): `/Game/AI/Customer/AIC_Customer` (edit)
- Read first: the current value is None (verified).
- Do: set CDO `DefaultNavigationFilterClass` = `/Script/GASDocumentation.GDNavFilter_AvoidDefenseBlockers`.
- Don't touch: anything else.
- Done when: the CDO shows the value; saved.
- Needs user test: no

### Task 4: BP_BreachPoint build reserve tag
- Agent: ue-blueprint-builder
- Depends on: none   Parallel with: 1, 5, 6, 8
- Asset(s): `/Game/Interactable/BP_BreachPoint` (edit)
- Do:
  - CDO `Tags` add `BuildReserve` if it is missing.
  - In BeginPlay, before the existing logic, add `Tags.AddUnique("BuildReserve")`. Placed instances with overridden Tags then still get it. This runs on server and client.
- Don't touch: breach, nav-area or door logic.
- Done when: compiles; CDO Tags contains BuildReserve; the BeginPlay AddUnique node is present. Vesper on EventGraph.
- Needs user test: no

### Task 5: BP_BuildArea (new)
- Agent: ue-blueprint-builder
- Depends on: none   Parallel with: 1, 4, 6, 8
- Asset(s): `/Game/Defense/BP_BuildArea` (new, parent Actor)
- Do:
  - Root BoxComponent `AreaBox`:
    - BoxExtent (500,500,200).
    - Collision NoCollision, CanEverAffectNavigation false, bHiddenInGame true.
    - Visible in the editor; LineThickness 4; ShapeColor (80,200,120).
  - CDO:
    - `Tags` = [`BuildArea`]
    - `bReplicates` false
    - `bCanBeDamaged` false
    - `bIsEditorOnlyActor` false (it must exist at runtime)
  - No graph logic.
- Don't touch: anything else.
- Done when: compiled and saved; the components list shows AreaBox as root with the extent above.
- Needs user test: no

### Task 6: IA_RotateBuildable (new)
- Agent: ue-blueprint-builder
- Depends on: none   Parallel with: 1, 4, 5, 8
- Asset(s): `/Game/Characters/Input/IA_RotateBuildable` (new InputAction)
- Read first: `/Game/Characters/Input/IA_ToggleBuildMode` settings. Mirror them.
- Do:
  - ValueType Digital (bool).
  - PlayerMappableKeySettings: Name `RotateBuildable`, DisplayName "Rotate Buildable", DisplayCategory the same as IA_ToggleBuildMode.
- Don't touch: IMC (that's Task 7).
- Done when: the asset exists and is saved.
- Needs user test: no

### Task 7: IMC_Default rotate mappings
- Agent: ue-blueprint-builder
- Depends on: 6   Parallel with: none
- Asset(s): `/Game/Characters/Input/IMC_Default` (edit)
- Do: add mappings `IA_RotateBuildable` → `T` and `IA_RotateBuildable` → `Gamepad_RightShoulder`, with no modifiers or triggers.
- Don't touch: existing mappings.
- Also: before adding, list existing IMC_Default mappings on `T` and `Gamepad_RightShoulder` and report any conflict in NOTES (add the mappings anyway).
- Done when: the mappings are listed. Byte-check the saved `.uasset` contains the string `IA_RotateBuildable` (memory: IMC edits can stay unsaved). Report the check.
- Needs user test: no

### Task 8: DT_DefenseBlueprints socket types
- Agent: ue-blueprint-builder
- Depends on: none   Parallel with: 1, 4, 5, 6
- Asset(s): `/Game/Data/DT_DefenseBlueprints` (edit)
- Do:
  - For the rows whose DefenseClass is BP_Turret_Automated, BP_Barricade or BP_Trap_Gas, set `SocketType` = Floor (0).
  - Swinging stays Wall (1). Spike and SlowStrip stay Floor.
  - Report the final per-row SocketType.
- Don't touch: other fields.
- Done when: read_data_table shows only the Swinging row as Wall; saved.
- Needs user test: no

### C1: ue-git-manager
Commit "Freeform building: placement library, nav filter, build area, rotate input" and push `feature/freeform-building`. No PR.

---
### CHECKPOINT B: Defense actors and ghost

### Task 9: BP_BuildGhost radius ring and tint
- Agent: ue-blueprint-builder
- Depends on: none   Parallel with: none
- Asset(s): `/Game/Defense/BP_BuildGhost` (edit)
- Read first: the existing SetGhostValid. Copy how it makes and uses MIDs and the material parameter name. The M_BuildGhost color param is `GhostColor`; confirm it from SetGhostValid.
- Do:
  - Add StaticMeshComponent `RadiusRing`, child of GhostMesh:
    - Mesh `/Engine/BasicShapes/Cylinder`, material `/Game/Defense/Materials/M_BuildGhost`.
    - Collision NoCollision, CanEverAffectNavigation false, CastShadow false.
    - Visible false.
    - AbsoluteRotation true. The ring stays flat while the ghost tilts.
  - Function `SetPreviewRadius(Radius: float)` (impure):
    - If Radius ≤ 0, set RadiusRing hidden.
    - Otherwise:
      - SetWorldScale3D (Radius/50, Radius/50, 0.02).
      - Create or reuse a MID on RadiusRing and set GhostColor (0.2, 0.6, 1.0, 0.35).
      - Set it visible.
  - Function `SetGhostTint(Color: LinearColor)` (impure): for GhostMesh and GhostMeshB, create or reuse a MID per material slot and set vector param GhostColor = Color.
  - SetGhostValid must not override the RadiusRing color. If SetGhostValid loops over all components, restrict it to GhostMesh and GhostMeshB.
- Don't touch: SetGhostShape, SetGhostDefense.
- Done when: compiles; get_functions lists SetPreviewRadius(Radius) and SetGhostTint(Color). Vesper on the edited graphs.
- Needs user test: no

### Task 10: BP_DefenseGhost (new)
- Agent: ue-blueprint-builder
- Depends on: 9   Parallel with: none
- Asset(s): `/Game/Defense/BP_DefenseGhost` (new, parent `/Game/Defense/BP_BuildGhost`)
- Read first: BP_BuildGhost after Task 9: SetGhostDefense(DefenseClass: class Actor), SetGhostTint, SetPreviewRadius. E_LootTier is the enum used by BP_DefenseBase.Tier.
- Do:
  - **CDO:** bReplicates true; bReplicateMovement false; Tags [`BuildGhost`]; bCanBeDamaged false.
  - **Variables** (all Replicated, Instance Editable, Expose on Spawn):
    - `GhostBlueprintID` Name, RepNotify → `OnRep_GhostData`
    - `GhostDefenseClass` Class of Actor
    - `GhostTier` E_LootTier
    - `GhostTotalSpent` int
  - Non-replicated `RebuildCostPercent` float 0.25.
  - **`ApplyGhostVisual()`** (impure):
    1. If GhostDefenseClass is valid, call SetGhostDefense(GhostDefenseClass).
    2. SetGhostTint((0.35, 0.4, 0.5, 0.45)).
    3. SetPreviewRadius(0).
    4. For GhostMesh and GhostMeshB:
       - SetCollisionEnabled QueryOnly; SetCollisionObjectType PhysicsBody.
       - SetCollisionResponseToAllChannels Ignore, then SetCollisionResponseToChannel Visibility Block.
       - SetCanEverAffectNavigation false.
  - `OnRep_GhostData` → ApplyGhostVisual.
  - BeginPlay → Parent BeginPlay (if present) → ApplyGhostVisual.
  - **`GetRebuildCost() -> Cost: int`** (pure, with an entry→return exec wire) = Round(GhostTotalSpent × RebuildCostPercent).
- Don't touch: BP_BuildGhost.
- Done when: compiles; the replicated flags are visible in get_variables; GetRebuildCost is pure with the exec wire. Vesper.
- Needs user test: no

### Task 11: BP_DefenseBase freeform core
- Agent: ue-blueprint-builder
- Depends on: 1, 10   Parallel with: none
- Asset(s): `/Game/Defense/BP_DefenseBase` (edit)
- Read first:
  - Existing functions OnDefenseDestroyed, ApplyTrapHit, the BPI_Breachable `ApplyBreachDamage` event/impl, RestoreTierState(InTier, InTotalSpent, InHealth), RestoreFullHealth, PlayPlacementPop(Sound), RefreshDefenseVisual.
  - `/Game/Defense/BP_DefenseSocket` CDO: find its placement sound property (used when it spawned defenses) to copy the asset reference.
- Do:
  - **New variables:**
    - `bBlocksPath` bool false (Instance Editable)
    - `LastPathBlockTime` float −1000
    - `PathBlockGraceSeconds` float 2.0
    - `PlacementExtent` Vector (50,50,40) (Instance Editable)
    - `PreviewRadius` float 0 (Instance Editable)
    - `PlaceSound` SoundBase (default = the socket's placement sound asset)
    - `bSkipPlacePop` bool false (Expose on Spawn)
  - **CDO:** bReplicateMovement true; Tags add `Buildable`.
  - **`MarkBlockingPath()`** (impure): LastPathBlockTime = GetGameTimeInSeconds.
  - **`IsBlockingPathNow() -> bBlocking: bool`** (pure, exec wire) = bBlocksPath AND (GetGameTimeInSeconds − LastPathBlockTime ≤ PathBlockGraceSeconds).
  - **`ApplyHealthLoss(Amount: float)`** (impure):
    1. If not HasAuthority, or Health ≤ 0, return.
    2. Health = max(0, Health − Amount).
    3. RefreshDefenseVisual.
    4. If Health ≤ 0, OnDefenseDestroyed.
  - **ApplyBreachDamage (BPI impl):** first `if not IsBlockingPathNow → return` (no damage). Otherwise route its health subtraction through ApplyHealthLoss with the same amount. Keep other side effects such as sounds.
  - **ApplyTrapHit:** replace its inline wear subtraction or destroy with ApplyHealthLoss(TrapWearPerHit). Damage to the zombie stays unchanged.
  - **OnDefenseDestroyed:**
    1. Remove all OwningSocket and BP_DefenseSocket logic.
    2. Keep the existing FX and sound.
    3. Then, if HasAuthority: SpawnActor `BP_DefenseGhost` (Class pin explicitly set; collision AlwaysSpawn) at GetActorTransform with GhostBlueprintID=BlueprintID, GhostDefenseClass=GetClass, GhostTier=Tier, GhostTotalSpent=TotalSpent.
    4. DestroyActor.
  - **BeginPlay:** add `if not bSkipPlacePop AND GetGameTimeInSeconds > 3.0 → PlayPlacementPop(PlaceSound)`.
  - Leave the OwningSocket and AllowedSocketType variables in place but unused.
  - **`ApplyGatedDamage(Amount: float)`** (impure, gate-1 fix): if not IsBlockingPathNow → return; else ApplyHealthLoss(Amount). Make ApplyBreachDamage call this instead of duplicating the gate.
  - Run project_query search for `ApplyBreachDamage`, and also for any other place zombie attacks or area damage reduce defense health: Bloater explode, Spitter acid projectile/pool, `ApplyDamage`/`AnyDamage` on BP_DefenseBase, and direct Health sets on defenses. In NOTES, list each caller with its asset path and whether it already goes through ApplyBreachDamage. The orchestrator then dispatches Task 11b for any caller that bypasses the gate.
- **Task 11b (conditional, one call per caller asset):** ue-blueprint-builder. In the caller's asset, replace the damage call or health write on a BP_DefenseBase target with a call to `ApplyGatedDamage(Amount)`, keeping the amount the same. Don't touch the zombie/player damage paths. Vesper and compile.
- Don't touch: tier and upgrade functions, child BPs.
- Done when: compiles 0 errors; the new functions are listed; OnDefenseDestroyed has no socket references; the SpawnActor ReturnValue is BP_DefenseGhost_C. Vesper on every edited graph.
- Needs user test: no

### Task 12: BP_Turret_Automated blocker setup
- Agent: ue-blueprint-builder
- Depends on: 11   Parallel with: 13–17
- Asset(s): `/Game/Defense/BP_Turret_Automated` (edit)
- Do:
  - Measure the combined local bounds of the visible meshes. PlacementExtent = half-size rounded up to 5 cm.
  - Add BoxComponent `NavBlockerBox` under the root:
    - BoxExtent = PlacementExtent; RelativeLocation (0,0,PlacementExtent.Z).
    - Collision QueryOnly, ObjectType Vehicle, all channels Ignore except Vehicle Block.
    - CanEverAffectNavigation true, bDynamicObstacle true.
    - AreaClassOverride `/Script/GASDocumentation.GDNavArea_DefenseBlocker`.
    - HiddenInGame true.
  - All mesh components: collision preset BlockAll (object type WorldDynamic), CanEverAffectNavigation false.
  - DetectionSphere: CanEverAffectNavigation false.
  - CDO:
    - bBlocksPath true
    - AllowedSocketType Floor
    - PreviewRadius = DetectionSphere SphereRadius × its relative scale
    - Tags still include Buildable (add it if the child overrides Tags)
    - bReplicateMovement true
  - Report the PlacementExtent and whether the mesh bottom sits at local Z≈0 (±2 cm). Don't move meshes.
- Don't touch: firing logic.
- Done when: compiles; components and CDO values are reported. Vesper n/a unless graphs are edited.
- Needs user test: no

### Task 13: BP_Barricade blocker setup
- Agent: ue-blueprint-builder
- Depends on: 11   Parallel with: 12, 14–17
- Asset(s): `/Game/Defense/BP_Barricade` (edit)
- Do: the same as Task 12 (NavBlockerBox, mesh collision, PlacementExtent from bounds, bBlocksPath true, AllowedSocketType Floor, Buildable tag, bReplicateMovement) with PreviewRadius 0. Report the extent and the pivot-at-base check.
- Don't touch: graphs.
- Done when: as Task 12.
- Needs user test: no

### Task 14: BP_Trap_Spike non-blocker CDO
- Agent: ue-blueprint-builder
- Depends on: 11   Parallel with: 12, 13, 15–17
- Asset(s): `/Game/Defense/BP_Trap_Spike` (edit)
- Do:
  - All mesh components: CanEverAffectNavigation false, Pawn response Overlap, Visibility stays Block.
  - PlacementExtent from bounds, rounded up to 5 cm. PreviewRadius 0. bBlocksPath false.
  - Ensure Tags include Buildable and bReplicateMovement is true.
  - Report the extent and the pivot check.
- Don't touch: trap pulse logic.
- Done when: CDO and component values are reported; compiled and saved.
- Needs user test: no

### Task 15: BP_Trap_Swinging non-blocker CDO (wall)
- Agent: ue-blueprint-builder
- Depends on: 11   Parallel with: 12–14, 16, 17
- Asset(s): `/Game/Defense/BP_Trap_Swinging` (edit)
- Do:
  - The same as Task 14, with PreviewRadius 0 and AllowedSocketType Wall.
  - PlacementExtent is the mount footprint only: the bounds of the mounting/base mesh, not the blade sweep.
  - Report the local axis along which the mesh extends away from the wall mount. The expected answer is +X. If it isn't +X, say so clearly in NOTES and don't rotate anything.
- Don't touch: swing logic.
- Done when: values and the axis are reported; saved.
- Needs user test: no

### Task 16: BP_Trap_SlowStrip non-blocker CDO
- Agent: ue-blueprint-builder
- Depends on: 11   Parallel with: 12–15, 17
- Asset(s): `/Game/Defense/BP_Trap_SlowStrip` (edit)
- Do: as Task 14, with PreviewRadius = the CDO TrapRadius value.
- Done when: reported; saved.
- Needs user test: no

### Task 17: BP_Trap_Gas non-blocker CDO
- Agent: ue-blueprint-builder
- Depends on: 11   Parallel with: 12–16
- Asset(s): `/Game/Defense/BP_Trap_Gas` (edit)
- Do: as Task 14, with PreviewRadius = TrapRadius and AllowedSocketType Floor.
- Done when: reported; saved.
- Needs user test: no

### C2: ue-git-manager
Commit "Freeform building: defense ghost, blocker nav, defense base damage gate" and push. No PR.

---
### CHECKPOINT C: Build mode, PC, UI

### Task 18: BuildModeComponent part 1 (freeform preview)
- Agent: ue-blueprint-builder
- Depends on: 1, 9, 11   Parallel with: none
- Asset(s): `/Game/Characters/BP_BuildModeComponent` (edit)
- Read first:
  - Current vars and functions (verified): bBuildModeActive, BuildTraceDistance 1200, SelectedBlueprint (S_DefenseBlueprintEntry), CurrentTargetSocket, OnTargetSocketChanged, bCurrentTargetValid, bHasSelection, SnapRadius, LastAimPoint, CachedSockets, BuildGhost (BP_BuildGhost_C); UpdateTargetSocket, SetBuildModeActive, SetSelectedBlueprint, GetCurrentTargetSocket, GetPlacementRequest, ClearSelection, CanAffordSelected, FindSnapSocket.
  - The Tick graph.
  - The PC, BuildMenu and TestController will break after this task. Expected; don't fix them.
- Do:
  - **Remove:** CurrentTargetSocket, OnTargetSocketChanged, SnapRadius, CachedSockets, FindSnapSocket, UpdateTargetSocket, GetCurrentTargetSocket, and any socket show/hide calls in SetBuildModeActive.
  - **Add variables:**
    - `PlacementYawDegrees` float 0
    - `PlacementTransform` Transform
    - `PlacementFailReason` Text empty
    - `MovingDefense` BP_DefenseBase_C ref
    - `SelectedPlacementExtent` Vector (50,50,40)
    - `bSelectedIsWallItem` bool false
    - `SelectedPreviewRadius` float 0
  - **`UpdatePlacementPreview()`** (impure), called from Tick when bBuildModeActive AND bHasSelection AND the owner PC IsLocalController:
    1. Camera = PC PlayerCameraManager location and forward. End = Start + Fwd × BuildTraceDistance.
    2. Ignore = [controlled pawn, BuildGhost, MovingDefense (if valid)].
    3. `TraceBuildSurface` → Hit.
    4. `ComputePlacementTransform(Hit, bSelectedIsWallItem, PlacementYawDegrees)` → T, ok1, reason1.
    5. If ok1: `ValidatePlacement(T, bSelectedIsWallItem, SelectedPlacementExtent, PawnLocation, 0, Ignore)` → ok2, reason2.
    6. Set PlacementTransform = T; bCurrentTargetValid = ok1 AND ok2; PlacementFailReason = the first failing reason, or empty if valid.
    7. LastAimPoint = T location.
    8. BuildGhost: SetActorTransform(T), SetGhostValid(bCurrentTargetValid), visible.
  - When there is no selection, hide BuildGhost and clear PlacementFailReason.
  - **Replace GetPlacementRequest** with `GetPlacementRequest() -> (BlueprintID: Name, OutTransform: Transform, OutMovingDefense: BP_DefenseBase_C, bValid: bool)` (pure, exec wire). Returns SelectedBlueprint.BlueprintID, PlacementTransform, MovingDefense, and bHasSelection AND bCurrentTargetValid.
  - **`GetBuildReasonText() -> Reason: Text`** (pure, exec wire). Returns PlacementFailReason if bBuildModeActive AND bHasSelection AND NOT bCurrentTargetValid, otherwise empty text.
- Don't touch: CanAffordSelected, SetBuildTagApplied, ClearSelection (Task 19).
- Done when:
  - this asset compiles with 0 errors (other assets may break);
  - no function references BP_DefenseSocket;
  - the GetPlacementRequest outputs match exactly.
  - Vesper on the edited graphs.
- Needs user test: no

### Task 19: BuildModeComponent part 2 (rotate, move, selection)
- Agent: ue-blueprint-builder
- Depends on: 18, 8   Parallel with: none
- Asset(s): `/Game/Characters/BP_BuildModeComponent` (edit)
- Read first: the Task 18 report. DT row struct S_DefenseBlueprintEntry has SocketType (E_DefenseSocketType: 0 Floor, 1 Wall) and DefenseClass.
- Do:
  - **SetSelectedBlueprint(NewEntry)**, at its start:
    1. MovingDefense = None.
    2. After its existing logic: `GetBuildableDefaults(NewEntry.DefenseClass)` → SelectedPlacementExtent, SelectedPreviewRadius.
    3. bSelectedIsWallItem = (NewEntry.SocketType == Wall).
    4. BuildGhost.SetPreviewRadius(SelectedPreviewRadius).
    5. If bSelectedIsWallItem, PlacementYawDegrees = 0.
  - **ClearSelection:** also MovingDefense = None and BuildGhost.SetPreviewRadius(0).
  - **SetBuildModeActive(false) branch:** also MovingDefense = None.
  - **`RotateSelection()`** (impure): if bHasSelection AND NOT bSelectedIsWallItem, PlacementYawDegrees = (PlacementYawDegrees + 90) mod 360.
  - **`BeginMove(Defense: BP_DefenseBase_C)`** (impure):
    1. If not valid, return.
    2. GetDataTableRow(DT_DefenseBlueprints, Defense.BlueprintID). If not found, return.
    3. If not bBuildModeActive, SetBuildModeActive(true).
    4. SetSelectedBlueprint(row).
    5. MovingDefense = Defense. This must come after step 4, which clears it.
    6. PlacementYawDegrees = round(Defense yaw / 90) × 90, normalized to 0..359.
- Don't touch: Task 18 functions except where stated.
- Done when: compiles; get_functions shows RotateSelection() and BeginMove(Defense). Vesper.
- Needs user test: no

### Task 20: PC part A (place, rotate, sell, key text)
- Agent: ue-blueprint-builder
- Depends on: 19, 7, 1   Parallel with: none
- Asset(s): `/Game/Core/PlayerControllers/BP_PlayerController_ZombieStore` (edit)
- Read first:
  - `OnServerPlaceDefenseOnSocket`. Copy its phase check, unlocked check, free-first-Spike logic, cash deduction, TotalSpent setup and `Client_TutorialGoalCompleted("Def_PlaceTrap")` call before emptying it.
  - `OnServerSellDefense`, `TryPlaceSelectedDefense`, `GetInteractKeyText` (pure; QueryKeysMappedToAction pattern), `ShowOwnerStatusMessage`.
  - BuildModeComponent's new GetPlacementRequest outputs (BlueprintID, OutTransform, OutMovingDefense, bValid), RotateSelection, ClearSelection, GetBuildReasonText.
- Do:
  - **`IsBuildPhase() -> bAllowed: bool`** (pure, exec wire): GameState CurrentPhase is not NightPhase(1) and not RunOver(2).
  - **`TryServerPlaceDefense(BlueprintID: Name, InTransform: Transform) -> (bSuccess: bool, FailReason: Text)`** (impure, server logic):
    1. Not HasAuthority → false.
    2. Not IsBuildPhase → "Can't build at night".
    3. DT row missing → "Unknown buildable".
    4. GameState.IsBlueprintUnlocked false → "Not unlocked".
    5. GetBuildableDefaults(row.DefenseClass) → Extent.
    6. ValidatePlacement(InTransform, row.SocketType==Wall, Extent, controlled pawn location, 75, empty) false → its reason.
    7. Cost: copied free-spike logic, otherwise CanAfford(Cost) and Server_DeductCash. Failure → "Not enough cash".
    8. SpawnActor (Class pin = row.DefenseClass, AlwaysSpawn) at InTransform.
    9. Cast to BP_DefenseBase and set BlueprintID and TotalSpent (the cost actually paid, matching existing behavior).
    10. Client_TutorialGoalCompleted("Def_PlaceTrap").
    11. Return true.
  - **`Server_PlaceDefenseAt(BlueprintID: Name, InTransform: Transform)`** custom event, Run on Server, Reliable → TryServerPlaceDefense. If not bSuccess → Client_BuildRejected(FailReason).
  - **`Client_BuildRejected(Reason: Text)`** custom event, Run on Owning Client, Reliable → ShowOwnerStatusMessage(Reason).
  - **TryPlaceSelectedDefense** rewrite:
    1. Get the placement request.
    2. Not bValid → ShowOwnerStatusMessage(BuildModeComponent.GetBuildReasonText, or "Can't place here" if empty) and return.
    3. OutMovingDefense valid → Server_MoveDefense(OutMovingDefense, OutTransform), then ClearSelection. Server_MoveDefense is created in Task 21; add a stub custom event now with the same signature (Run on Server, Reliable, inputs Defense: BP_DefenseBase_C, InTransform: Transform), body empty.
    4. Otherwise Server_PlaceDefenseAt(BlueprintID, OutTransform).
  - **Input:** EnhancedInputAction `IA_RotateBuildable` Started → if BuildModeComponent.bBuildModeActive → BuildModeComponent.RotateSelection.
  - **OnServerSellDefense:**
    - Cast the param directly to BP_DefenseBase and remove any socket lookup.
    - Keep the refund math. The defense must be removed with **DestroyActor**, never OnDefenseDestroyed, because selling must not leave a ghost.
  - **OnServerPlaceDefenseOnSocket:** empty the body. Leave the event node in place.
  - **`GetRotateKeyText() -> KeyText: Text`** (pure, exec wire). Copy GetInteractKeyText using IA_RotateBuildable; fallback "T".
- Don't touch: interact/hold logic (Task 22), the door hold, weapon input.
- Done when: the PC compiles with 0 errors; get_functions shows the signatures above; no SpawnActor has an unset class pin. Vesper on EventGraph and edited functions.
- Needs user test: no

### Task 21: PC part B (move, rebuild, remove)
- Agent: ue-blueprint-builder
- Depends on: 20, 10   Parallel with: none
- Asset(s): `/Game/Core/PlayerControllers/BP_PlayerController_ZombieStore` (edit)
- Read first: the Task 20 report. BP_DefenseGhost exposes GhostBlueprintID, GhostDefenseClass, GhostTier, GhostTotalSpent and `GetRebuildCost()->Cost`. BP_DefenseBase has `RestoreTierState(InTier, InTotalSpent, InHealth)`, `RestoreFullHealth`, `bSkipPlacePop` (ExposeOnSpawn) and `BlueprintID`. BuildModeComponent has `BeginMove(Defense)`.
- Do:
  - **`TryServerMoveDefense(Defense: BP_DefenseBase_C, InTransform: Transform) -> (bSuccess, FailReason: Text)`**:
    1. Authority; Defense valid; IsBuildPhase, else "Can't move at night".
    2. Row by Defense.BlueprintID.
    3. GetBuildableDefaults(Defense.GetClass) → Extent.
    4. ValidatePlacement(InTransform, row.SocketType==Wall, Extent, pawn location, 75, [Defense]), else its reason.
    5. Defense.SetActorTransform(InTransform). No cost.
  - Fill in the **`Server_MoveDefense`** body → TryServerMoveDefense; on failure Client_BuildRejected.
  - **`TryServerRebuildGhost(Ghost: BP_DefenseGhost_C) -> (bSuccess, FailReason)`**:
    1. Authority; ghost valid; IsBuildPhase, else "Can't rebuild at night".
    2. Cost = Ghost.GetRebuildCost.
    3. Row by GhostBlueprintID.
    4. ValidatePlacement(Ghost transform, row.SocketType==Wall, Extent from GhostDefenseClass, pawn location, 75, [Ghost]), else its reason.
    5. If not CanAfford(Cost) → "Not enough cash"; otherwise Server_DeductCash(Cost).
    6. SpawnActor GhostDefenseClass at the ghost transform (AlwaysSpawn).
    7. Cast to BP_DefenseBase; BlueprintID = GhostBlueprintID; RestoreTierState(GhostTier, GhostTotalSpent, 1.0); RestoreFullHealth.
    8. Ghost DestroyActor.
    9. TotalSpent stays GhostTotalSpent. The rebuild cost is not added.
  - **`TryServerRemoveGhost(Ghost) -> bSuccess`**: authority, valid → DestroyActor. Any phase, no refund.
  - **RPCs** (Run on Server, Reliable): `Server_RebuildGhost(Ghost: BP_DefenseGhost_C)` and `Server_RemoveGhost(Ghost: BP_DefenseGhost_C)`. Each sends Client_BuildRejected on failure.
  - **`BeginMoveDefense(Defense: BP_DefenseBase_C)`** (client-side, impure):
    1. If not IsBuildPhase → ShowOwnerStatusMessage("Can't move at night") and return.
    2. CloseTrapPanelUI.
    3. BuildModeComponent.BeginMove(Defense).
- Don't touch: Task 20 logic.
- Done when: compiles 0 errors; all signatures listed. Vesper.
- Needs user test: no

### Task 22: PC part C (interact, ghost hold, socket cleanup)
- Agent: ue-blueprint-builder
- Depends on: 21   Parallel with: none
- Asset(s): `/Game/Core/PlayerControllers/BP_PlayerController_ZombieStore` (edit)
- Read first:
  - GetAimedPlacedDefense: a Visibility LineTraceSingle from the camera, then Cast BP_DefenseBase, falling back to Cast BP_DefenseSocket→OccupyingDefense.
  - GetAimedDamagedDefense.
  - The IA_Interact Started/Completed/Canceled handlers, including the defense repair-hold branch and the door/breach hold (keep that one).
  - GetAimedInteractPromptText, GetHoldBarProgress, GetInteractKeyText, OpenTrapPanel (or whatever opens WBP_TrapPanel for a defense).
- Do:
  - **Socket cleanup:**
    - Delete the BP_DefenseSocket fallback in GetAimedPlacedDefense and GetAimedDamagedDefense.
    - Delete the defense repair-hold branch from the IA_Interact handlers. Repair stays in the panel; this closes BUGS.md "hold-E repair conflict".
  - **`GetAimedGhost() -> Ghost: BP_DefenseGhost_C`** (pure, exec wire). Same trace as GetAimedPlacedDefense, then Cast BP_DefenseGhost.
  - **New variables** (local, not replicated):
    - `GhostHoldTarget` BP_DefenseGhost_C
    - `bGhostHoldActive` bool
    - `GhostHoldStartTime` float
    - `GhostHoldSeconds` float 1.5
    - `GhostHoldTimer` TimerHandle
  - **IA_Interact Started**, outside build mode, after the placed-defense check fails and before door handling: if GetAimedGhost is valid:
    1. GhostHoldTarget = it; bGhostHoldActive = true; GhostHoldStartTime = GetGameTimeInSeconds.
    2. SetTimerByFunctionName "CompleteGhostHold", GhostHoldSeconds, no loop → GhostHoldTimer.
    3. Consume (skip the remaining branches).
  - **`CompleteGhostHold()`**: if bGhostHoldActive and GhostHoldTarget valid → Server_RebuildGhost(GhostHoldTarget); bGhostHoldActive = false.
  - **`ReleaseGhostHold()`**, called from IA_Interact Completed and Canceled:
    1. If not bGhostHoldActive, return.
    2. Clear GhostHoldTimer.
    3. If (now − GhostHoldStartTime) < GhostHoldSeconds AND GhostHoldTarget valid → OpenTrapPanelForGhost(GhostHoldTarget).
    4. bGhostHoldActive = false.
  - **`OpenTrapPanelForGhost(Ghost: BP_DefenseGhost_C)`**: open WBP_TrapPanel the same way as for a defense, then call `SetTargetGhost(Ghost)` on it. SetTargetGhost is made in Task 23. If it isn't there yet, leave a TODO-free stub call by adding the call after Task 23. Simplest: create the panel and store it; Task 23's builder wires the call.
  - **GetAimedInteractPromptText:** when GetAimedGhost is valid, return Format("Hold {0} to rebuild (${1}) · Tap for options", GetInteractKeyText, Ghost.GetRebuildCost).
  - **GetHoldBarProgress:** if bGhostHoldActive, return clamp((now − GhostHoldStartTime)/GhostHoldSeconds, 0, 1). Otherwise keep the existing logic.
- Don't touch: the door/breach hold, weapon fire.
- Done when: compiles 0 errors; no node references BP_DefenseSocket (search_nodes "DefenseSocket" returns 0); no ForEach back-edges. Vesper on every edited graph.
- Needs user test: no

### Task 23: WBP_TrapPanel move, remove, destroyed state
- Agent: ue-ui-builder
- Depends on: 22   Parallel with: 24, 25
- Asset(s): `/Game/UI/WBP_TrapPanel` (edit)
- Read first:
  - The existing Upgrade, Repair and Sell buttons and their text style.
  - TargetDefense var, FindOwningSocket, the close-key handling (IsUICloseKey; Tab/Esc/E). Keep the close keys.
  - PC functions: BeginMoveDefense(Defense), Server_RemoveGhost(Ghost), Server_SellDefense(AActor*), IsBuildPhase, OpenTrapPanelForGhost (Task 22).
- Do:
  - **Widgets:**
    - `Button_Move` / `Text_Move` ("Move"), and `Button_Remove` / `Text_Remove` ("Remove (no refund)"), placed in the same container as Sell and styled like Sell.
    - `Text_DestroyedStatus` TextBlock above the buttons, Collapsed by default.
    - Copy ForegroundColor and font from the Sell text (memory: foreground can come out transparent).
  - **Variable** `TargetGhost` (BP_DefenseGhost_C).
  - **`SetTargetGhost(Ghost: BP_DefenseGhost_C)`**:
    1. TargetGhost = Ghost; TargetDefense = None.
    2. Collapse Upgrade, Repair, Sell and Move. Show Remove.
    3. Text_DestroyedStatus visible: Format("Destroyed. Hold {0} on it to rebuild for ${1}.", PC.GetInteractKeyText, Ghost.GetRebuildCost).
    4. Set any title text to the ghost's DT DisplayName.
  - **Normal defense refresh:** show Upgrade, Repair, Sell and Move; collapse Remove and DestroyedStatus. Button_Move is enabled only when PC.IsBuildPhase.
  - **Clicks:**
    - Move → PC.BeginMoveDefense(TargetDefense). The PC closes the panel.
    - Remove → PC.Server_RemoveGhost(TargetGhost), then close the panel.
    - Sell → PC.Server_SellDefense(TargetDefense). Pass the defense directly, with no socket lookup.
  - Delete FindOwningSocket and every BP_DefenseSocket reference.
  - In the PC's OpenTrapPanelForGhost, make sure the SetTargetGhost call is wired. This is the one allowed PC edit; it is a single node.
- Don't touch: upgrade and repair logic, close keys.
- Done when: the widget and the PC compile; search_nodes "DefenseSocket" = 0 in the panel. Vesper on the edited graphs.
- Needs user test: no

### Task 24: WBP_HUD build reason text
- Agent: ue-ui-builder
- Depends on: 18   Parallel with: 23, 25
- Asset(s): `/Game/UI/WBP_HUD` (edit)
- Do:
  - Add TextBlock `Txt_BuildReason` under the crosshair: centered anchor, offset Y +40.
    - Color (1, 0.35, 0.3, 1); font size 16; justification center; Visibility HitTestInvisible.
    - Copy the font family from an existing HUD text.
  - Bind Text to a new function `GetBuildReason() -> Text` (pure): GetOwningPlayer → Cast BP_PlayerController_ZombieStore → BuildModeComponent → GetBuildReasonText. Empty if the cast fails.
- Don't touch: other HUD elements.
- Done when: compiles; the binding is present. Vesper.
- Needs user test: no

### Task 25: WBP_BuildMenu socket removal and placement hint
- Agent: ue-ui-builder
- Depends on: 20   Parallel with: 23, 24
- Asset(s): `/Game/UI/WBP_BuildMenu` (edit)
- Read first: TrackedSocket var, HandleTargetSocketChanged and its OnTargetSocketChanged bind, RefreshSocketFit and the text widget it writes. BuildModeComponent vars bHasSelection and bSelectedIsWallItem. PC.GetRotateKeyText.
- Do:
  - Delete TrackedSocket, HandleTargetSocketChanged and the bind node.
  - Rename RefreshSocketFit → `RefreshPlacementHint()`. It writes the same text widget:
    - no selection → "Pick a buildable"
    - wall item → "Wall item · aim at an inside wall"
    - otherwise → Format("Floor item · Rotate: {0}", PC.GetRotateKeyText)
  - Call it wherever RefreshSocketFit was called, and after a selection is made.
- Don't touch: list and buy logic.
- Done when: compiles 0 errors; no socket references. Vesper.
- Needs user test: no

### C3: ue-git-manager
First confirm that the PC, WBP_BuildMenu, WBP_TrapPanel, WBP_HUD and BP_BuildModeComponent compile clean. BP_TestController may still be broken; note that in the commit message. Commit "Freeform building: build mode, PC placement/move/ghost, UI" and push.

---
### CHECKPOINT D: AI and customers

### Task 26: BB_Zombie blocker keys
- Agent: ue-blueprint-builder
- Depends on: none   Parallel with: 29, 30
- Asset(s): `/Game/Characters/AI/BB_Zombie` (edit)
- Do: add `BlockerTarget` (Object, BaseClass Actor) and `BlockerApproachLocation` (Vector).
- Done when: the keys are listed; saved.
- Needs user test: no

### Task 27: BTS_ZombieBlockerDecision (new)
- Agent: ue-blueprint-builder
- Depends on: 26, 1, 11   Parallel with: 29, 30
- Asset(s): `/Game/Characters/AI/BTS_ZombieBlockerDecision` (new, parent BTService_BlueprintBase)
- Read first: `/Game/Characters/AI/BTS_ZombieBreachDecision`. Mirror its key selectors (TargetActorKey "TargetActor", BreachTargetKey "BreachTarget"), its FindPathToActorSynchronously usage and its ReceiveTickAI structure.
- Do:
  - **CDO:** Interval 0.5, RandomDeviation 0.1.
  - **Variables:**
    - Instance Editable BlackboardKeySelector: `TargetActorKey`="TargetActor", `BreachTargetKey`="BreachTarget", `BlockerTargetKey`="BlockerTarget", `BlockerApproachLocationKey`="BlockerApproachLocation".
    - `DetourRatioLimit` float 2.0
  - **`ClearBlockerKeys(Owner: AIController)`**: ClearValue on BlockerTarget and BlockerApproachLocation.
  - **`FindBlockerOnPath(PathPoints: Array<Vector>, PawnLocation: Vector) -> Blocker: BP_DefenseBase_C`** (impure):
    1. GetAllActorsOfClass BP_DefenseBase.
    2. Keep those with bBlocksPath AND Health > 0.
    3. For each candidate, take the minimum over path segments (i, i+1) of the distance from the actor location to FindClosestPointOnSegment.
    4. A candidate qualifies when that distance ≤ max(PlacementExtent.X, PlacementExtent.Y) + 80.
    5. Return the qualifying one nearest PawnLocation, or None.
    - Use plain ForEach/ForLoop with no back-edges.
  - **ReceiveTickAI(OwnerController, ControlledPawn):**
    1. Gather blocker candidates (GetAllActorsOfClass, filter bBlocksPath). Clear the keys and return if there are none, or BreachTarget is set, or TargetActor is not set.
    2. Direct = FindPathToActorSynchronously(World, PawnLoc, TargetActor, 100, PathfindingContext=None, FilterClass=None). If invalid or IsPartial → clear and return.
    3. Detour = FindPathToActorSynchronously(..., FilterClass=`GDNavFilter_AvoidDefenseBlockers`). If valid AND not partial AND Detour.GetPathLength ≤ DetourRatioLimit × Direct.GetPathLength → clear and return.
    4. B = FindBlockerOnPath(Direct.PathPoints, PawnLoc). None → clear and return.
    5. Approach = B.Location + Normalize2D(PawnLoc − B.Location) × (max(B.PlacementExtent.X, B.PlacementExtent.Y) + 70). Then ProjectPointToNavigation(Approach, QueryExtent (100,100,200)). Use the projected point if it succeeds, otherwise the raw point.
    6. Set BlockerTarget = B and BlockerApproachLocation = Approach. Call B.MarkBlockingPath.
- Don't touch: BTS_ZombieBreachDecision.
- Done when: compiles; ReceiveTickAI is implemented; the FilterClass pin on the second path call is set. Vesper on all graphs.
- Needs user test: no

### Task 28: BT_Zombie attack-blocker branch
- Agent: ue-blueprint-builder
- Depends on: 27   Parallel with: 29, 30
- Asset(s): `/Game/Characters/AI/BT_Zombie` (edit)
- Read first: export_bt_spec. Find the BreachTarget branch (MoveTo BreachApproachLocation → RotateToFaceBBEntry → BTT_ZombieMeleeAttack) and where BTS_ZombieBreachDecision is attached.
- Do:
  - Add a Sequence `Sequence_AttackBlocker` to the same parent selector, immediately after the breach branch and before the chase branch.
  - Blackboard decorator: key BlockerTarget, IsSet, FlowAbortMode Both. Set BasicOperation Set **and** OperationType 0 (memory gotcha).
  - Children, mirroring the breach branch's node settings:
    1. MoveTo BlockerApproachLocation, AcceptableRadius 50, AllowPartialPath true.
    2. RotateToFaceBBEntry BlockerTarget.
    3. BTT_ZombieMeleeAttack.
  - Attach service BTS_ZombieBlockerDecision on the same composite that hosts BTS_ZombieBreachDecision.
- Don't touch: existing branches.
- Done when: export_bt_spec shows the new sequence in that position with the decorator OperationType 0, and the service is attached. Saved.
- Needs user test: no

### Task 29: Melee hit dedupe
- Agent: ue-blueprint-builder
- Depends on: none   Parallel with: 26–28, 30
- Asset(s): `/Game/Characters/BP_ZombieAttackComponent` (edit)
- Read first: PerformMeleeAttack. It uses BoxTraceMultiForObjects (WorldStatic, WorldDynamic, Pawn) with no per-actor dedupe; see BUGS.md "melee multi-hit", around L2216.
- Do:
  - Add a local variable `HitActors` (Array Actor) in PerformMeleeAttack.
  - In the per-hit loop body, before applying damage: if HitActors Contains HitActor → skip to the end of the body, which ends that iteration naturally. **Do not** wire anything back into the ForEach Exec input.
  - Otherwise AddUnique and continue as before.
- Don't touch: damage values, trace shape.
- Done when: compiles; no exec wire into the ForEach Exec input except from the function entry path. Vesper.
- Needs user test: no

### Task 30: Customer gives up on a blocked route
- Agent: ue-blueprint-builder
- Depends on: 3   Parallel with: 26–29
- Asset(s): `/Game/Characters/BP_Customer` (edit)
- Read first: HandlePatienceTimeout (→ bHandled, ExitLocation), BeginLeaveStore(ExitLocation), bPatienceActive, BeginPlay.
- Do:
  - **Variables:**
    - `RouteBlockedSeconds` float 0
    - `RouteBlockedGiveUpSeconds` float 3.0
    - `RouteCheckTimer` TimerHandle
    - `bGaveUpOnRoute` bool false
  - **BeginPlay:** if HasAuthority, SetTimerByFunctionName "CheckRouteBlocked", 1.0, looping → RouteCheckTimer.
  - **`CheckRouteBlocked()`:**
    1. If GetLifeSpan > 0 or bGaveUpOnRoute → return.
    2. AIC = GetController cast AIController. If invalid → return.
    3. If AIC.GetMoveStatus == Moving AND AIC.HasPartialPath → RouteBlockedSeconds += 1; otherwise RouteBlockedSeconds = 0.
    4. If RouteBlockedSeconds ≥ RouteBlockedGiveUpSeconds:
       - bGaveUpOnRoute = true; bPatienceActive = true.
       - HandlePatienceTimeout. If bHandled → BeginLeaveStore(ExitLocation).
       - Clear RouteCheckTimer.
    - HandlePatienceTimeout already records the lost sale through its existing path. Don't add another RecordCustomerLost.
- Don't touch: patience timer logic, checkout.
- Done when: compiles; the timer is set in BeginPlay behind authority. Vesper.
- Needs user test: no

### C4: ue-git-manager
Commit "Freeform building: zombie blocker attack, melee dedupe, customer route give-up" and push.

---
### CHECKPOINT E: Save, maps, text, docs

### Task 31: S_SavedDefense fields
- Agent: ue-blueprint-builder
- Depends on: none   Parallel with: 33–37
- Asset(s): `/Game/Data/Save/S_SavedDefense` (edit)
- Do: add fields `Transform` (Transform, default identity) and `bIsGhost` (bool, false). Keep SocketName, BlueprintID, Tier, TotalSpent and Health.
- Done when: the struct shows 7 fields; saved.
- Needs user test: no

### Task 32: GameState save and restore by transform
- Agent: ue-blueprint-builder
- Depends on: 31, 10, 11   Parallel with: 33–37
- Asset(s): `/Game/Core/GameStates/BP_GameState_ZombieStore` (edit)
- Read first: GatherPlacedDefenses → Defenses (Array S_SavedDefense) and RestorePlacedDefenses(Defenses). Both currently go through BP_DefenseSocket.
- Do:
  - **GatherPlacedDefenses:**
    - For every BP_DefenseBase with Health > 0, add {SocketName "", BlueprintID, Tier, TotalSpent, Health, Transform = actor transform, bIsGhost false}.
    - For every BP_DefenseGhost, add {SocketName "", BlueprintID=GhostBlueprintID, Tier=GhostTier, TotalSpent=GhostTotalSpent, Health 0, Transform, bIsGhost true}.
    - No socket iteration.
  - **RestorePlacedDefenses**, authority only:
    1. Destroy all existing BP_DefenseBase and BP_DefenseGhost actors.
    2. For each entry: skip it if SocketName is not empty (legacy socket save, dropped), or if the DT_DefenseBlueprints row for BlueprintID is missing.
    3. If bIsGhost: spawn BP_DefenseGhost at Transform with GhostBlueprintID, GhostDefenseClass = row.DefenseClass, GhostTier and GhostTotalSpent.
    4. Otherwise: SpawnActor row.DefenseClass at Transform, AlwaysSpawn, bSkipPlacePop = true when exposed. Cast BP_DefenseBase → BlueprintID = entry.BlueprintID → RestoreTierState(Tier, TotalSpent, Health).
- Don't touch: other save fields.
- Done when: compiles; search_nodes "DefenseSocket" = 0 in this asset; SpawnActor class pins are set. Vesper.
- Needs user test: no

### Task 33: Map_Store_Outdoors build areas and socket removal
- Agent: ue-content-builder
- Depends on: 5   Parallel with: 31, 32, 34–37
- Asset(s): `/Game/Levels/Map_Store_Outdoors` (edit). It has hand edits, so **only** the two operations below.
- Do:
  - Delete every actor of class BP_DefenseSocket. Report the count.
  - For each BP_StoreInteriorVolume actor, spawn a `/Game/Defense/BP_BuildArea`:
    - Same location XY and same yaw.
    - Actor scale = ((VolExtentX+25)/500, (VolExtentY+25)/500, (VolExtentZ+10)/200), where VolExtent = world half-size.
    - Location Z positioned so the area bottom is 20 cm below the volume bottom.
    - Label `BuildArea_<n>`.
  - Report RecastNavMesh RuntimeGeneration. Don't change it.
  - Save the map.
- Don't touch: any other actor or setting.
- Done when: the socket count is 0; the BuildArea count equals the interior volume count; saved.
- Needs user test: no

### Task 34: Map_Startup socket removal
- Agent: ue-content-builder
- Depends on: none   Parallel with: 31–33, 35–37
- Asset(s): `/Game/GASDocumentation/Maps/Map_Startup` (edit)
- Do: delete all BP_DefenseSocket actors and report the count (0 is fine). Add no build areas. Save.
- Done when: the socket count is 0.
- Needs user test: no

### Task 35: Test_Level_Zero socket removal
- Agent: ue-content-builder
- Depends on: none   Parallel with: 31–34, 36, 37
- Asset(s): `/Game/Levels/Test_Level_Zero` (edit)
- Do: as Task 34.
- Done when: the socket count is 0.
- Needs user test: no

### Task 36: DT_TutorialGoals text
- Agent: ue-blueprint-builder
- Depends on: none   Parallel with: 31–35, 37
- Asset(s): `/Game/Data/Tutorial/DT_TutorialGoals` (edit)
- Do:
  - Row `Def_PlaceTrap` text: "Press {Key} to open Build Mode, pick the Spike Trap and place it on the store floor. Green means it fits. Your first Spike Trap each run is free."
  - Row `Def_ManageTrap` text: "Look at one of your traps and press {Key} to upgrade, repair, move or sell it."
  - Leave the key/action fields unchanged (IA_ToggleBuildMode and IA_Interact).
- Done when: read_data_table shows the new text; saved.
- Needs user test: no

### Task 37: DT_CodexEntries text
- Agent: ue-blueprint-builder
- Depends on: none   Parallel with: 31–36
- Asset(s): `/Game/Data/Tutorial/DT_CodexEntries` (edit)
- Do:
  - Row `Def_02` (title "Placing traps") body: "Open Build Mode with the Build Mode key, pick a trap and aim at the store floor (or an inside wall for the Swinging Trap) within about 6 m. The preview turns green when the trap fits and red when it doesn't, with the reason on screen. Press the Rotate key to turn floor traps 90°; wall traps face out on their own. Left click to place, right click exits Build Mode. You cannot fire or aim weapons in Build Mode. Traps can be placed in Morning, Day and Dusk. Turrets and barricades are solid: zombies walk around them if they can, and smash them if they block the way. Each player's first Spike Trap in a run is free."
  - Row `Def_03` (title "Managing traps") body: "Outside Build Mode, look at a placed trap and press the Interact key to open its panel. Upgrade raises its tier. Repair restores health and works in any phase. Move picks the trap up so you can place it again for free, keeping its tier and health. Sell refunds 50% of everything spent on the trap. Upgrade, Move and Sell are closed at Night. A destroyed trap leaves a ghost: hold the Interact key on it to rebuild it at its old tier for 25% of what it cost, or tap it and choose Remove to clear it (no refund). Rebuilding works in Morning, Day and Dusk."
- Done when: the rows read back correctly; saved.
- Needs user test: no

### Task 38: Docs reconciliation (markdown only)
- Agent: orchestrator (main session); no builder needed
- Depends on: 36, 37   Parallel with: none
- Asset(s): `docs/PHASE_13_TASKLIST.md`, `docs/GDD.md`, `docs/FREEFORM_BUILDING_DECISIONS.md`, `docs/BUGS.md`, `docs/PHASE_4_TASKLIST.md`, `docs/ParentTaskList.md` (edit)
- Do:
  - **Gate-1 fix:** add a Status Note to the active phase file, PHASE_4_TASKLIST.md (socket sections) and ParentTaskList.md (its 2 socket mentions) saying freeform placement (`feature/freeform-building`, see FREEFORM_BUILDING_DECISIONS.md) supersedes socket placement.
  - **Gate-1 fix:** in FREEFORM_BUILDING_DECISIONS.md, mark calls 13, 15, 16 and 21 "decided by architect, user may overrule" and quote the spec text each one stretches.
  - **PHASE_13_TASKLIST.md:** update L34/L35 (goal text) and L69/L70 (codex text) to the strings in Tasks 36 and 37.
  - **GDD.md:**
    - L97: the panel lists Upgrade/Repair/Move/Sell, and destroyed traps leave ghosts (hold Interact to rebuild for 25%, tap for Remove).
    - L98: controls add the Rotate key (T / RB, rebindable). Turret and Barricade block pathing and are only attackable while blocking.
  - **FREEFORM_BUILDING_DECISIONS.md:** replace "(none yet)" with the Section 8 list below.
  - **BUGS.md:**
    - Mark resolved by freeform building: L1050, L1377, L1411, L1628, L1775, L1985, L1993, L2085, L2033, L2041 and L2216 (melee dedupe, Task 29).
    - Update L599 to drop its socket collision-box mention.
    - Add new entries (Status: Known limitation) for Risks 6, 7 and 8, plus a RuntimeGeneration entry if Task 33 reported it as non-Dynamic.
- Done when: the four files are edited; no other docs are touched.
- Needs user test: no

### C5: ue-git-manager
Commit "Freeform building: transform saves, build areas in store map, tutorial/codex/docs" and push.

---
### CHECKPOINT F: Tests and cleanup

All tests spawn their own `BP_BuildArea` at the PC pawn location + forward×200, traced down to the floor, with extent large enough (scale 2,2,1). They destroy it at teardown and verify there is floor below first (memory: test level floor check). Suite column = same suite as the existing Build/Defense rows. Rerun `Tools/TestSuites/make_suite_maps.py` after editing rows.

### Task 39: Test migration (TW1)
- Agent: ue-test-writer
- Depends on: 32, 25, 23   Parallel with: none
- Asset(s): `/Game/Tests/Automation/Blueprints/BP_TestController`, `/Game/Tests/Automation/Data/DT_AutomationTests`, `/Game/Tests/Automation/Maps/L_AutomationTestBed` (edit)
- Read first: BP_TestController compile errors after Task 18. These are socket fixtures, the BeginPlay socket cast, and the TU_*/SV_* helpers that reference BP_DefenseSocket or the old GetPlacementRequest/GetCurrentTargetSocket. New APIs:
  - PC.TryServerPlaceDefense(BlueprintID, InTransform) → (bSuccess, FailReason).
  - BuildModeComponent.GetPlacementRequest → (BlueprintID, OutTransform, OutMovingDefense, bValid).
- Do:
  - Remove the socket fixtures from L_AutomationTestBed and BP_TestController, including the BeginPlay cast.
  - Rewrite these tests:
    - `Test_BuildModePlacementRequest`: select the Spike, aim at the floor inside the spawned area, assert bValid and BlueprintID.
    - `Test_BuildMode_ServerPlaceAllowedInDusk`: phase Dusk, TryServerPlaceDefense succeeds.
    - `Test_BuildMode_ServerPlaceBlockedAtNight`: phase Night, it fails.
    - `Test_Audio_K3DefenseSoundsAssigned`: assert BP_DefenseBase CDO PlaceSound is valid, instead of the socket sound.
    - `Test_Defense_K4ReplicationEnabled`: BP_DefenseBase bReplicates and bReplicateMovement; BP_DefenseGhost bReplicates.
  - Delete `Test_Defense_K4SocketHighlight` and its DT row.
  - Fix or remove the socket-based TU_* and SV_* helpers.
- Done when: BP_TestController compiles 0 errors; search_nodes "DefenseSocket" = 0; suite maps regenerated. Vesper on the edited graphs.
- Needs user test: no

### Task 40: Placement and ghost tests (TW2)
- Agent: ue-test-writer
- Depends on: 39   Parallel with: none
- Asset(s): the same three test assets (edit)
- Do: add these tests and DT rows, all using UGDBuildPlacementLibrary or the PC server functions:
  - `Test_Build_ValidateRejectsTooFar`: viewer 700 cm away; reason "Too far".
  - `Test_Build_ValidateRejectsOutsideArea`: a point outside the spawned area; "Outside store".
  - `Test_Build_ValidateRejectsOverlapBuildable`: spawn a Spike at P; validate a Spike at P; "Overlaps a buildable".
  - `Test_Build_ValidateAllowsEdgeTouch`: Spike at P; validate a Spike at P + (2×Spike PlacementExtent.X, 0, 0); passes.
  - `Test_Build_ComputeRejectsSteepSlope`: a synthetic FHitResult with a 30° normal fails with "Too steep"; 10° passes.
  - `Test_Build_ValidateRejectsGhostOverlap`: spawn BP_DefenseGhost (Spike class) at P; "Overlaps a ghost".
  - `Test_Defense_GhostSpawnsOnDestroy`: place a Barricade; ApplyHealthLoss(MaxHealth); a ghost exists at its location with matching GhostBlueprintID.
  - `Test_Defense_BreachDamageOnlyWhenBlocking`: a Barricade without MarkBlockingPath takes no ApplyBreachDamage loss; after MarkBlockingPath it does.
  - `Test_Defense_NonBlockerIgnoresBreachDamage`: a Spike after MarkBlockingPath still takes no breach damage.
  - `Test_Defense_AreaDamageOnlyWhenBlocking`: a Turret without MarkBlockingPath takes no ApplyGatedDamage loss; after MarkBlockingPath it does (covers Bloater and Spitter area damage).
- Done when: compiles; rows added; suite maps regenerated. Vesper.
- Needs user test: no

### Task 41: Ghost, move and save tests (TW3)
- Agent: ue-test-writer
- Depends on: 40   Parallel with: none
- Asset(s): the same three test assets (edit)
- Do:
  - `Test_Defense_NoGhostOnSell`: place, then Server_SellDefense (or the OnServerSellDefense path); no BP_DefenseGhost exists.
  - `Test_Defense_GhostRebuildCostAndTier`: ghost with GhostTier Rare and GhostTotalSpent 400; GetRebuildCost == 100. TryServerRebuildGhost with enough cash → a defense exists at tier Rare, Health == MaxHealth, the ghost is gone, and cash dropped by 100.
  - `Test_Defense_MoveKeepsTierAndHealth`: defense at Rare, TotalSpent 400, Health 37; TryServerMoveDefense to a valid spot → same actor, tier Rare, Health 37, new location.
  - `Test_Save_DefensesRoundTripByTransform`: one defense and one ghost → GatherPlacedDefenses → RestorePlacedDefenses → transforms match within 1 cm, and ghost/defense counts match.
  - `Test_Save_DropsLegacySocketEntries`: an entry with SocketName "Sock_Test" → after restore, no actor was spawned for it.
- Done when: compiles; rows added; maps regenerated. Vesper.
- Needs user test: no

### Task 42: Run the tests
- Agent: ue-test-runner
- Depends on: 41
- Do: run the Build/Defense/Save/Audio suites containing every TestName from Tasks 39–41, and report PASS/FAIL per name. A failure goes back through the normal retry and escalation path for the owning build task, not the test.

### Task 43: Retire BP_DefenseSocket asset
- Agent: ue-content-builder
- Depends on: 42 all PASS   Parallel with: none
- Asset(s): `/Game/Defense/BP_DefenseSocket` (delete)
- Do:
  - Run project_query find_references on it.
  - Delete it only if the result is empty. Otherwise list the referencers in NOTES and leave the asset.
  - Leave E_DefenseSocketType and the C++ socket RPCs.
- Done when: the asset is deleted or the referencers are reported.
- Needs user test: no

### Task 44: Final manual test (user, morning)
- Agent: none; the orchestrator relays this to the user
- Depends on: 43
- Needs user test: yes
  1. **Single player, Map_Store_Outdoors, Day.** Open Build Mode and pick the Spike.
     - The ghost turns green on the floor and red on walls, shelves, outside, doors and other traps, with a HUD reason.
     - T rotates it 90°. It tilts on gentle slopes.
     - The first Spike is free.
  2. **Swinging trap.** It mounts on an inside wall facing outward (check the blade side, Risk 6). It is red on outside walls.
  3. **Turret and Gas.** A blue radius ring shows during preview.
  4. **Nav.** With `show Navigation` on, a placed Turret or Barricade shows the red area. Zombies path around a partial wall and smash a Barricade that fully seals the door. A Turret that isn't blocking takes no damage. A Bloater exploding near a non-blocking turret does nothing.
  5. **Ghost.** Let a Barricade be destroyed: a ghost stays. Hold E for about 1.5 s with the hold bar: it rebuilds at the old tier for 25%. Tap E: the panel shows the destroyed state; Remove clears it. Rebuild is refused at Night.
  6. **Move.** Panel → Move: the trap is picked up into Build Mode, can be placed for free, and keeps tier and health. Move is refused at Night.
  7. **Customers.** Seal the customer route with Barricades: customers leave after about 3 s and the sale is lost.
  8. **Save.** Quit and load: traps and ghosts are back in place, and an old save with socket traps loads without them.
  9. **Two-player listen server.** The client places, moves and rebuilds. The host sees the changes, and the client sees no host preview.
  10. **Horde perf.** Run a night with 3+ barricades and check the frame time.

### C6: ue-git-manager
Commit "Freeform building: tests migrated and added; retire socket actor" and push `feature/freeform-building`. No PR.

## 7. Spec coverage check
- **Core rules 1–6:** T1 (overlap, wall and world checks), T8, T15 (Floor/Wall), T12, T13 (pathing), T11 (attack gate), T11 (ghost on destroy).
- **Categories and socket removal:** T8, T33–35, T43.
- **Build area and overlap rules:** T1 tag and physical passes; doors via T4.
- **Range, slope, no cap:** T1 (600 cm, 15°). There is no count logic.
- **Placement controls:**
  - Free placement: T18.
  - Rotate: T6, T7, T19, T20.
  - Wall items auto-face: T1.
  - Reason HUD: T24.
  - Radius preview: T9, T19.
  - Local preview: T18 IsLocalController.
  - Phases: T20, T21.
- **Pathing:**
  - Blocking: T1–3, T12, T13.
  - Detour within 2x vs attack: T27, T28.
  - No attacker cap: all zombies run the service.
  - Customers: T30.
  - Turret not attackable unless blocking: T11.
  - Area damage gate: T11.
  - Trap self-wear and its ghost: T11 ApplyTrapHit → ApplyHealthLoss.
- **Ghosts:**
  - Spawn on destroy, not on sell: T10, T11, T20.
  - Hold to rebuild for 25%: T21, T22.
  - Tap to Remove: T22, T23.
  - Phase rule: T21.
  - Lifetime: they are never auto-destroyed.
  - Space reservation without collision: T1 BuildGhost tag; T10 PhysicsBody Visibility-only collision.
- **Move:** T19, T21, T23.
- **Save:** T31, T32.
- **Text:** T24, T25, T36–38.
- **Process:** C1–C6.
- **Decisions log:** T38.

## 8. Design calls to log under "Decisions made during the build"
1. **Rotate key.** The rotate action is IA_RotateBuildable on T / Gamepad Right Shoulder, rebindable. Yaw is absolute world yaw in 90° steps, and Move snaps the existing yaw to the nearest 90°.
2. **Wall surfaces.** A wall surface is a hit normal with |Z| ≤ 0.25 on a WorldStatic component. Floor surfaces must block Pawn and sit within 15°.
3. **Range slack.** The server re-validates with 75 cm of range slack over the client's 600 cm, to absorb movement lag.
4. **Overlap test.** Buildable, ghost and door overlap uses mesh-bounds AABBs shrunk 2 cm, so edge-to-edge touching passes.
5. **Door reserve.** Doors and breach points reserve 120 cm in XY around their bounds through a `BuildReserve` tag added in BP_BreachPoint BeginPlay. This covers the swing area.
6. **World objects.** Any non-pawn component that blocks Pawn is a world object, and blocks placement. Physics-simulating components such as pickups are ignored. A StaticMeshActor gives the reason "Overlaps a wall"; anything else gives "Overlaps an object".
7. **Ghost collision.** Ghosts use PhysicsBody query-only collision that responds to Visibility only, so interact traces hit them and fire traces, pawns and nav ignore them.
8. **Build area containment.** All 8 footprint corners plus the center must be inside some BP_BuildArea. Volumes union per point.
9. **Store map areas.** Store build areas equal each BP_StoreInteriorVolume plus 25 cm in XY, with the bottom 20 cm lower. Map_Startup and Test_Level_Zero get no build areas.
10. **Damage gate.** A defense counts as "blocking" for 2 s after any zombie's blocker service flags it. All zombie damage to defenses goes through this gate: melee, Bloater and Spitter acid (via ApplyGatedDamage, gate-1 fix).
11. **Blocker approach.** Zombies attack a blocker when the detour is more than 2.0x the direct path, or when there is no detour. A blocker counts as "on the path" within its max XY half-extent + 80 cm of the direct path.
12. **Customer give-up.** Customers give up after 3 s of partial-path movement, going through the existing patience-timeout path, so it counts as a lost customer.
13. **Rebuild.** Rebuild cost is round(25% × TotalSpent). Rebuilding doesn't add to TotalSpent, so later sells and rebuilds use the original spend.
14. **Remove.** Remove is allowed in any phase. Rebuild and Move are Morning/Day/Dusk only.
15. **Move flow.** During Move the item stays in place until the new spot is confirmed. Cancelling leaves it where it was.
16. **Hold timing.** On a ghost, a tap is a release before 1.5 s, and that opens the panel. Holding E on placed traps no longer repairs; repair is panel-only. This resolves the earlier hold-E conflict.
17. **Visuals.**
    - Ghost tint is a grey-blue (0.35, 0.4, 0.5).
    - The radius ring is a flat blue cylinder.
    - The placement pop now plays from BeginPlay when the world is more than 3 s old, and is suppressed on save restore.
18. **Legacy code.** The C++ socket RPC is kept, but dead. OwningSocket, AllowedSocketType and the TurretBase/Other enum entries are kept unused.
19. **Removed test.** Test_Defense_K4SocketHighlight is deleted. There are no sockets left to highlight.
20. **Melee dedupe.** Each zombie swing hits an actor at most once (fixes the melee multi-hit bug).
21. **Raised floor items.** Floor items may sit on a raised Pawn-blocking surface (for example a counter top) if it is inside a build area. Accepted for v1.
22. **Codex keys.** Codex text names keys generically ("the Rotate key"), because codex entries take one `{Key}` at most.

## 9. Vision self-check
- **Pillar** (rubric L32; GDD.md L24): defending the store you run. Freeform placement inside the store's build areas keeps traps tied to the store space. Rebuild costs make defense spending a retail-economy decision. ALIGNED.
- **Session structure** (rubric L33; GDD.md L31–34, L43): building stays in Morning/Day/Dusk and Night is for fighting. Ghosts turn night losses into next-day rebuild decisions, which strengthens the day/night loop. ALIGNED.
- **Reuse** (rubric):
  - Existing tier, upgrade, sell and repair systems, BP_BuildGhost, BuildModeComponent, the phase checks, the PC interact and hold patterns, and the BT breach branch are all extended rather than replaced.
  - New assets are limited to the placement library, BuildArea, DefenseGhost, one input action and one BT service.
  - ALIGNED.
- **Scope** (rubric): everything traces back to `docs/FREEFORM_BUILDING_DECISIONS.md` sections 1–7. There is no grid, no count cap and no no-build volumes, as specified. One tension needs a decision: GDD.md L104 plans "defense-targeting" zombies, but this plan makes defenses attackable only while blocking (FREEFORM "Pathing and attacks"). That future type needs an explicit exception. **UNSURE: the vision keeper should rule.**
- **Multiplayer** (rubric L40; memory: listen server): the server validates and spawns everything; the preview is local; the reliable RPCs are listed in Section 4; ghosts and movement replicate. The two-player check is item 9 of Task 44. ALIGNED.
- **Docs to reconcile:** GDD.md L97–98 (panel and controls) and PHASE_13 L34/35/69/70. Task 38 covers them. The GDD has no socket mentions, so nothing there contradicts this plan.

**Relevant files:**
- C:\Users\brest\source\GameDesignRepos\NoBrainers\NoBrainers\docs\FREEFORM_BUILDING_DECISIONS.md
- C:\Users\brest\source\GameDesignRepos\NoBrainers\NoBrainers\docs\PHASE_13_TASKLIST.md
- C:\Users\brest\source\GameDesignRepos\NoBrainers\NoBrainers\docs\GDD.md
- C:\Users\brest\source\GameDesignRepos\NoBrainers\NoBrainers\docs\BUGS.md
- C:\Users\brest\source\GameDesignRepos\NoBrainers\NoBrainers\Source\GASDocumentation\GASDocumentation.Build.cs