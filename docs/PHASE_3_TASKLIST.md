Here is the breakdown for Phase 3: Night Phase \& Zombie Horde, structured as a technical Markdown document for Phase\_3\_Night\_Phase\_and\_Zombie\_Horde.md.



Phase 3: Night Phase \& Zombie Horde

Technical Context

Engine Version: Unreal Engine 5.7.4



Perspective: First-Person



Architecture: Server-authoritative zombie AI spawning, pathfinding, breach point management, weapon hit-detection, and randomized loot distribution.



Goal: Implement the night-time survival gameplay loop, including horde spawning scaled by store advertisements, breachable entry points, first-person gunplay/melee combat, and zombie loot drops.



Task Breakdown

1\. Zombie AI \& Horde Spawning Manager

\[ ] 1.1 Zombie Base Character (ACharacter\_ZombieBase)



Create ACharacter\_ZombieBase derived from ACharacter.



Add UHealthComponent (replicated).



NavMesh Agent setup with custom locomotion speeds (walk/jog/sprint variations).



Attack Component (UZombieAttackComponent): Melee sweep line-trace dealing damage to players or breach barriers.



\[ ] 1.2 Zombie AI Controller \& Behavior Tree (BT\_Zombie)



Create AAIController\_Zombie using Blackboard \& Behavior Tree:



Priority 1: Target nearest active player within sight/hearing radius.



Priority 2: If no line of sight, target nearest Breach Point (ABreachPoint) to enter the store.



Priority 3: If inside store and path blocked by defense (turret/barricade), attack defense actor.



\[ ] 1.3 Spawner System (AZombieSpawnerManager)



Create AZombieSpawnerManager active during NightPhase:



Calculate total horde count based on BaseRunDifficulty + StoreAdvertisementLevel.



Wave logic: Spawns zombies at exterior spawn points outside store boundaries in controlled bursts.



Tracks active count to keep within performance caps (e.g., max 30-50 active zombies on screen simultaneously).



2\. Store Entry \& Breach Point System

\[ ] 2.1 Breach Point Actor (ABreachPoint)



Create ABreachPoint placed at windows, glass doors, and vent hatches around the store geometry.



Replicated state variables: float Health, bool bIsBreached.



Visual states: Intact (Mesh 1) -> Damaged (Mesh 2) -> Destroyed/Breached (Mesh 3 + collision disabled).



\[ ] 2.2 Zombie Breach Interaction



Zombies path toward unbreached ABreachPoint actors blocking their way into the store.



Attack animation loop damages the ABreachPoint.



On breach complete: Broadcast breach event (audio cue for players), disable barrier collision, and update NavMesh to allow zombies into the store interior.



\[ ] 2.3 Player Barrier Repair (Optional/Day Prep)



Allow players to interact with breached ABreachPoint actors using resources or cash to repair window boards/glass before or during night.



3\. First-Person Combat \& Weapons System

\[ ] 3.1 Networked Weapon Base Class (AWeaponBase)



Create AWeaponBase actor class (Attachable to ACharacter\_Player first-person mesh):



Replicated variables: int32 CurrentAmmo, int32 ReserveAmmo, float FireRate, float BaseDamage.



Server RPC: Server\_FireWeapon(FVector MuzzleLocation, FVector TargetImpact).



Multicast RPC: Multicast\_PlayFireFX() (Muzzle flash, recoil animation, shot audio).



\[ ] 3.2 Hit-Scan \& Projectile Implementation



Hit-Scan Weapons (Pistol, Shotgun, SMG):



Line-trace from camera center with weapon spread modifier.



Validate impact on server and apply damage via UGameplayStatics::ApplyDamage().



Melee Weapons (Baseball Bat, Crowbar):



Capsule/Box trace along weapon arc during attack animation state.



\[ ] 3.3 Weapon Inventory \& Switching



Equip/Holster system for ACharacter\_Player supporting Primary, Secondary, and Melee slots.



Bind input actions IA\_PrimaryAction (Fire), IA\_SecondaryAction (Aim Down Sights), and IA\_Reload.



4\. Zombie Loot Drop System

\[ ] 4.1 Loot Table Architecture (FLootTable)



Data Table DT\_ZombieLoot mapping zombie types to weighted item drop lists.



Items dropped match store retail items defined in DT\_Items (Phase 2).



\[ ] 4.2 Loot Spawning on Death



On ACharacter\_ZombieBase::Die() (Server-side):



Roll against DT\_ZombieLoot drop probability.



Spawn AItemPickup actor (from Phase 2) at zombie death transform with physics impulse (slight drop toss effect).



Auto-destroy zombie ragdoll/body after configurable delay (e.g., 5 seconds) to maintain performance.



Acceptance Criteria

When NightPhase begins, the spawner manager scales and spawns zombie waves dynamically based on run progress and advertisement level.



Zombies correctly path to store windows/doors, breach the barriers, and enter the store space.



Players can fire weapons (hit-scan/melee), dealing validated damage to zombies with synced audio/visual effects across all clients.



Defeated zombies play death ragdolls/animations and drop physical AItemPickup actors that players can store for the next Day phase.

