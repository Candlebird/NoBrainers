Here is the breakdown for Phase 4: Defense \& Building Systems, structured as a technical Markdown document for Phase\_4\_Defense\_and\_Building\_Systems.md.



Phase 4: Defense \& Building Systems

Technical Context

Engine Version: Unreal Engine 5.7.4



Perspective: First-Person



Architecture: Server-authoritative placement validation, replicated trap state management, and localized grid/surface snapping system.



Goal: Allow players to purchase defense blueprints during the day, preview placement in first-person using a snapping ghost mesh, build automated traps/turrets/barricades, and maintain or repair them as zombies attack them.



Task Breakdown

1\. First-Person Placement \& Preview System

\[ ] 1.1 Placement Component (UPlacementComponent)



Attach to ACharacter\_Player.



Track active build mode state (bIsBuilding, TSubclassOf SelectedDefenseClass).



Continuous first-person line-trace along player camera view vector (configurable build range, e.g., 300–500 units).



\[ ] 1.2 Ghost Preview Actor (ABuildPreviewActor)



Spawns on build mode enter. Dynamic translucent material:



Green Material: Valid placement location.



Red Material: Invalid placement location (colliding with walls, out of bounds, or blocking required pathways).



Snap logic: Align to floor grid/normals or wall surfaces depending on defense type (EPlacementSurface::Floor, EPlacementSurface::Wall).



\[ ] 1.3 Networked Build Execution



Server RPC Server\_PlaceDefense(TSubclassOf DefenseClass, FTransform TargetTransform).



Server validation checks:



Player possesses defense blueprint or item in inventory.



Target location is within valid reach distance and surface constraints.



Player or store has required funds/inventory item to consume.



Deduct item/blueprint and spawn ADefenseBase actor across all clients.



2\. Defense Base Class \& Structure Hierarchy

\[ ] 2.1 Core Defense Actor (ADefenseBase)



Create ADefenseBase derived from AActor (IInteractableInterface):



Replicated UHealthComponent (Zombies can target and destroy built defenses).



Replicated state enum: EDefenseState::Active, EDefenseState::Disabled, EDefenseState::Destroyed.



Visual damage feedback (Particle/Decal swap as health drops).



\[ ] 2.2 Navigation Mesh Integration



Add UNavModifierComponent to ADefenseBase actors.



Configure obstacle area types (e.g., barricades act as Nav Obstacles forcing zombie re-pathing, while floor traps allow zombie pathing over them).



3\. Trap \& Automated Defense Classes

\[ ] 3.1 Spike / Damage Traps (ATrap\_Spike)



Floor-mounted defense actor.



Overlap trigger box detects ACharacter\_ZombieBase instances.



Trigger cooldown timer and apply AOE physical damage to overlapping zombies.



Durability system: Deduct 1 durability point per activation until destroyed or depleted.



\[ ] 3.2 Slow / Utility Traps (ATrap\_Slow)



Floor/Wall-mounted defense actor (e.g., Glue pad, Oil slick, Ice strip).



Applies speed reduction status effect (UStatusEffect\_Slow) to zombies within trigger volume.



Replicates status particle effects to clients.



\[ ] 3.3 Automated Turrets (ATurret\_Base)



Wall or floor-mounted automated defense.



Target acquisition component (USphereComponent) searching for nearest ACharacter\_ZombieBase.



Rotating turret head (pitch/yaw smoothly interpolates toward active target).



Firing loop: Line-trace or projectile damage with ammo counter and re-arm mechanic.



4\. Defense Repair \& Deconstruction System

\[ ] 4.1 Repair Mechanism



First-person interaction with damaged ADefenseBase actors during DayPhase.



Deduct store cash or repair materials to restore CurrentHealth / trap durability.



\[ ] 4.2 Deconstruction / Relocation



Allow players to dismantle built traps during DayPhase.



Refund a percentage (e.g., 75%) of original cost to store cash reserves or return defense item to player inventory.



Acceptance Criteria

Players can toggle build preview mode, showing a clear green/red ghost mesh that aligns smoothly with floors or walls.



Placing a defense correctly validates on the server, consumes the item/cash, and spawns the networked defense actor.



Spike traps, slow traps, and automated turrets autonomously trigger on nearby zombies and apply damage or status effects.



Zombies dynamically target and deal damage to player-built defenses if their paths are obstructed or if attacked by turrets.



Players can repair or deconstruct placed defenses during the Day Phase.

