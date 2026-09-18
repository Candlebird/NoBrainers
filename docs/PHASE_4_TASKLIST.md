Phase 4: Defense & Building Systems

Technical Context

Engine Version: Unreal Engine 5.7.4

Perspective: First-Person

Architecture: Node-based socket placement system (pre-defined world anchors), blueprint unlock registry, day-only build mode UI, and server-authoritative money transactions for placement.

Goal: Implement a simplified build system where players spend store cash during the Day Phase to place unlocked defense blueprints onto specialized, pre-defined node sockets (Floor, Wall, TurretBase, Other).

Task Breakdown

1. Build Node Socket Architecture

[ ] 1.1 Defense Socket Actor (ADefenseSocket)

Create ADefenseSocket actor placed fixedly throughout the store map.

Replicated properties:

EDefenseSocketType SocketType (Floor, Wall, TurretBase, Other).

ADefenseBase* OccupyingDefense (Pointer to active placed defense, null if empty).

bool bIsOccupied.

Visual feedback: Node marker highlight visible only while the local player is in Build Mode.

[ ] 1.2 Socket Trace & Selection Engine

Line-trace from camera center while in Build Mode targeting ADefenseSocket actors.

Highlight valid target sockets matching the category of the selected defense blueprint.

2. Day-Only Build Mode & Blueprint System

[ ] 2.1 Build Mode Input & HUD Overlay (IA_ToggleBuildMode)

Bind key (B) to toggle Build Mode:

Restriction: Allowed only during EGamePhase::DayPhase. Force exit Build Mode when transitioning to NightPhase.

Open Radial / Carousel Build Menu (UW_BuildMenu) showing unlocked blueprints.

[ ] 2.2 Blueprint Registry & Progression Engine (UBlueprintSubsystem)

Track unlocked defense classes per run:

Default Starters (Unlocked automatically): Simple Spike Traps (Floor), Simple Swinging Traps (Wall).

Shop Unlockables: Turrets (TurretBase), Barricades, Slow Strips, Gas Traps (Other).

Integrate blueprint purchases into the Day Phase Employee Discount Store catalog.

[ ] 2.3 Networked Node Build Transaction

Server RPC Server_PlaceDefenseOnSocket(ADefenseSocket* TargetSocket, TSubclassOf<ADefenseBase> DefenseClass).

Server validation checks:

Phase is currently DayPhase.

TargetSocket is valid, unoccupied, and matches DefenseClass required SocketType.

Player has unlocked the blueprint.

Store cash reserves (AGameState_ZombieStore::StoreCash) are sufficient.

Deduct store cash, mark socket as occupied, and spawn/attach ADefenseBase actor to node transform across all clients.

3. Defense Base Class & Socket Trap Hierarchy

[ ] 3.1 Core Defense Actor (ADefenseBase)

Base class for node-attached defenses:

Associated socket type enum: EDefenseSocketType.

Replicated UHealthComponent (Targetable and destructible by zombies).

Durability / Health visual states.

[ ] 3.2 Socket Trap Variants

Floor Traps (SocketType::Floor):

Spike Trap: Overlap trigger dealing instant physical damage; loses durability per activation.

Oil Slick / Ice Strip: Applies speed reduction status effect (UStatusEffect_Slow) to crossing zombies.

Wall Traps (SocketType::Wall):

Swinging Blade / Mallet Trap: Swings outward on proximity trigger, applying knockback and physical damage.

Turrets (SocketType::TurretBase):

Automated Turret: Mounts on designated turret bases; 360-degree target acquisition, firing line-traces at passing zombies.

Other Defenses (SocketType::Other):

Spotlights, barricades, gas dispensers, or utility generators.

4. Node Repair, Upgrade & Selling System

[ ] 4.1 In-Build Mode Node Management

While looking at an occupied ADefenseSocket during Build Mode:

Repair Option: Spend store cash to restore OccupyingDefense health/durability.

Sell / Dismantle Option: Remove OccupyingDefense, refunding a portion of store cash (e.g., 75%) and freeing the socket for new construction.

Acceptance Criteria

Building is restricted to pre-defined node locations (Floor, Wall, TurretBase, Other) and can only be activated during the Day Phase by pressing B.

Players start each run with basic blueprints (Spike and Swinging Traps) unlocked by default and can buy advanced blueprints (Turrets, Gas Dispensers) at the store.

Placing a defense on a node validates cash, socket type matching, and blueprint ownership on the server before spawning.

Traps deal damage, apply status effects, or auto-target zombies based on their socket type during the Night Phase.

Players can repair or sell placed defenses directly from occupied node sockets while in Build Mode.

