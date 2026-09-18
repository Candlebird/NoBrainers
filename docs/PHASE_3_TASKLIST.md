Phase 3: Night Phase & Zombie Horde

Technical Context

Engine Version: Unreal Engine 5.7.4

Perspective: First-Person

Architecture: Server-authoritative zombie AI spawning, pathfinding, breach point management, raycast-based gunplay with fast visual tracers (no ammo/reload mechanics yet), new melee weapon implementation, equipment/inventory binding, and randomized loot drops.

Goal: Implement the night-time survival gameplay loop by integrating existing base weapons, adding ammo/reload extensions, building the foundational inventory/holster system, introducing melee weapons, setting up zombie AI and breach mechanics, and configuring loot drops.

Task Breakdown

1. Inventory & Equipment System Foundation

[ ] 1.1 Player Inventory Component (UInventoryComponent)

Create UInventoryComponent attached to ACharacter_Player:

Replicated inventory arrays and slot structural limits (Primary, Secondary, Melee, Consumables).

Server RPCs for adding, removing, and switching equipped items.

Client delegates for inventory UI updates.

[ ] 1.2 Holster & Equipment Attachment System

Define socket attachments on the first-person character mesh (Skel_Mesh_FP / Third-person mesh) for weapons (e.g., Spine, Thigh, Back sockets).

Update weapon equipping logic so active weapons attach to hands and inactive weapons snap to their corresponding holster sockets.

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

