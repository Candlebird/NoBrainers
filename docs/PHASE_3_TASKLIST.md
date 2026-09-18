Phase 3: Night Phase & Zombie Horde

Technical Context

Engine Version: Unreal Engine 5.7.4

Perspective: First-Person

Architecture: Server-authoritative zombie AI spawning, pathfinding, breach point management, raycast-based gunplay with fast visual tracers (no ammo/reload mechanics yet), new melee weapon implementation, equipment/inventory binding, and randomized loot drops.

Goal: Implement the night-time survival gameplay loop by integrating existing base weapons, adding ammo/reload extensions, building the foundational inventory/holster system, introducing melee weapons, setting up zombie AI and breach mechanics, and configuring loot drops.

Task Breakdown

1. Inventory & Equipment System Foundation

[x] 1.1 Player Inventory Component (UInventoryComponent)

Create UInventoryComponent attached to ACharacter_Player:

Replicated inventory arrays and slot structural limits (Primary, Secondary, Melee, Consumables).

Server RPCs for adding, removing, and switching equipped items.

Client delegates for inventory UI updates.

STATUS NOTE (1.1 + 1.2, built together):

- Perspective deviation: this task's wording ("First-Person", "Skel_Mesh_FP") is stale — docs/GDD.md and the live BP_HeroCharacter (CameraBoom+FollowCamera+CharacterMesh0, no FP mesh) both confirm the project is third-person over-the-shoulder. No FP-arms asset was built. Resolved as a documented deviation, not a blocker.
- Naming deviation: built as `/Game/Characters/BP_EquipmentComponent` (new ActorComponent Blueprint on BP_HeroCharacter), kept intentionally separate from the existing `BP_InventoryComponent` (Phase 2 retail-item inventory). Reason: BP_InventoryComponent's `S_ItemSlot`/`S_ItemData`/`DT_Items`/`E_ItemCategory` are the exact serialization unit consumed by the 6.2 save system — widening them for weapon/equipment data would break the save format and force re-saving ~8 dependent Blueprints. Those Phase 2 assets were left completely untouched.
- New data assets: `E_EquipmentSlot` (Primary/Secondary/Melee/Consumable), `S_WeaponData` (DT_Weapons row struct), `S_EquipmentSlot` (replicated per-slot record: SlotType/ItemID/Quantity/CurrentAmmo/ReserveAmmo), `DT_Weapons` (3 placeholder rows: Pistol/Rifle/Bat — all tuning values, meshes, and abilities are unsourced placeholders pending real weapon art/design pass; Bat's WeaponMesh is null pending task 3.1).
- `BP_EquipmentComponent`: 6 replicated slots (Primary/Secondary/Melee/Consumable×3), ActiveSlotIndex, Server_EquipItem/Server_RemoveEquipment/Server_SetActiveSlot/Server_CycleActiveSlot RPCs, GrantActiveWeaponAbility/ClearGrantedWeaponAbility (GAS ability swap tied to active slot, mirrors the existing GunAbilityReference handle pattern). `Server_DropEquipped()` left as a stub — real implementation deferred to a later loot/pickup task. `RestoreEquipment(Slots)` built but deliberately left unwired — whether gear survives player death/respawn is an open design call, not assumed either way.
- Holster visuals: 3 new skeleton sockets on UE4_Mannequin_Skeleton (Socket_Holster_Primary/Secondary/Melee — placeholder transforms, flagged for a human visual pass), 3 new non-replicated SkeletalMeshComponents on BP_HeroCharacter (Holster_Primary/Secondary/Melee) attached to those sockets, and a filled-in `ApplyEquipmentVisuals()` that sets the native `Gun` component's mesh to the active weapon slot's row (never touches Gun's socket attachment, only SetSkeletalMesh/relative transform) and mirrors non-active occupied weapon slots onto their holster components.
- Input: new IA_EquipSlot1/2/3 + IA_CycleWeapon (axis) actions, mapped to keys 1/2/3 and mouse wheel in IMC_Default (existing unrelated pending edits to that asset preserved; task 2.1 hold's IA_Interact/interact binding untouched). Binding logic went into BP_PlayerController_ZombieStore's EventGraph rather than BP_HeroCharacter, since that's where the project's actual EnhancedInputAction convention (IA_PrimaryAction, IA_ToggleInventory) already lives — documented deviation from the literal task wording.
- KNOWN GAP — needs a human in the editor: Monolith cannot create a properly-bound `K2Node_EnhancedInputAction` node referencing an existing InputAction asset (add_node/add_nodes_bulk fall back to an inert generic node with no settable InputAction reference). The 4 new input chains in BP_PlayerController_ZombieStore are fully built and wired except for their first exec pin. Manual step needed: drop in 4 EnhancedInputAction nodes (IA_EquipSlot1/2/3, IA_CycleWeapon) and wire each into its dangling Cast node's execute pin (K2Node_DynamicCast_0/1/2/3 in that graph); for CycleWeapon also wire its ActionValue float into the SignOfFloat call (K2Node_CallFunction_21's "A" pin). Graph compiles fine in the current dangling state (equip/cycle simply won't fire from input until this is done).
- Compile: both touched Blueprints 0 errors/0 warnings each pass. Saved via save_dirty_assets.
- Task 2.1 (Phase 2, interaction raycast) hold respected throughout — BP_InteractionProbe/IA_Interact untouched.
- Manual testing needed once the EnhancedInputAction nodes above are wired in-editor: 2-client listen-server test — equip/switch/drop across slots via keys 1/2/3 and mouse wheel, holster meshes correct on both local and remote pawn, granted GAS ability actually swaps with active slot, hand mesh (Gun component) shows only the active weapon and nothing when a Consumable slot is active.

[x] 1.2 Holster & Equipment Attachment System

Define socket attachments on the first-person character mesh (Skel_Mesh_FP / Third-person mesh) for weapons (e.g., Spine, Thigh, Back sockets).

Update weapon equipping logic so active weapons attach to hands and inactive weapons snap to their corresponding holster sockets.

(See status note under 1.1 above — 1.1 and 1.2 were built and documented together.)

2. Weapon System Expansion (Ammo, Reload & Raycast Tracers)

[ ] 2.1 Ammo & Reload Mechanics

Extend existing first-person weapon classes to include:

Replicated integer variables: CurrentAmmo, MagazineSize, ReserveAmmo.

Server RPC: Server_Reload() to check reserve counts, execute reload animations, and replenish magazines.

[ ] 2.2 Fast-Tracer Raycast Weapon Integration

Standardize all firing logic to use line-trace (raycast) on the server.

Implement visual "fake projectile" fast-tracers (Niagara particle systems or beam emitters) spawned from muzzle to impact point to simulate projectiles visually without ballistic physics overhead.

3. Melee Weapons Implementation

[ ] 3.1 Melee Weapon Base Class (AMeleeWeaponBase)

Create AMeleeWeaponBase derived from AWeaponBase or actors:

Attack animation states (Swing, Recovery).

Hit detection using box/capsule sweeps along the weapon swing arc.

[ ] 3.2 Server-Validated Melee Damage

Implement server-side overlap/sweep validation to prevent client-side hit exploitation.

Apply impulse force to zombie ragdolls or hit targets upon successful melee impact.

4. Zombie AI & Horde Spawning Manager

[ ] 4.1 Zombie Base Character (ACharacter_ZombieBase)

Create ACharacter_ZombieBase derived from ACharacter.

Add UHealthComponent (replicated).

NavMesh Agent setup with custom locomotion speeds (walk/jog/sprint variations).

Attack Component (UZombieAttackComponent) for melee sweeps against players or breach barriers.

[ ] 4.2 Zombie AI Controller & Behavior Tree (BT_Zombie)

Create AAIController_Zombie using Blackboard & Behavior Tree:

Priority 1: Target nearest active player within sight/hearing radius.

Priority 2: If no line of sight, target nearest Breach Point (ABreachPoint) to enter the store.

Priority 3: If inside store and path blocked by player-placed defense, attack defense actor.

[ ] 4.3 Spawner System (AZombieSpawnerManager)

Create AZombieSpawnerManager active during NightPhase:

Calculate total horde count based on BaseRunDifficulty + StoreAdvertisementLevel.

Wave logic: Spawns zombies at exterior spawn points outside store boundaries in controlled bursts within performance caps.

5. Store Entry & Breach Point System

[ ] 5.1 Breach Point Actor (ABreachPoint)

Create ABreachPoint placed at windows, glass doors, and vent hatches around store geometry.

Replicated state variables: float Health, bool bIsBreached.

Visual states: Intact -> Damaged -> Destroyed/Breached (collision disabled).

[ ] 5.2 The Breach Action

Zombies path toward unbreached ABreachPoint actors, attack them, and trigger breach events upon health depletion, allowing entry into the store interior via updated NavMesh links.

6. Zombie Loot Drop System

[ ] 6.1 Loot Table Architecture (FLootTable) & Drop Spawning

Data Table DT_ZombieLoot mapping zombie types to weighted item drop lists.

On ACharacter_ZombieBase::Die() (Server-side): roll against drop tables, spawn physical world pickup items with slight drop impulses, and clear zombie bodies after a set delay.

