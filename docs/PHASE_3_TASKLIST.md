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

[x] 2.1 Ammo & Reload Mechanics

Extend existing first-person weapon classes to include:

Replicated integer variables: CurrentAmmo, MagazineSize, ReserveAmmo.

Server RPC: Server_Reload() to check reserve counts, execute reload animations, and replenish magazines.

STATUS NOTE:

- Deviation: no separate weapon class exists (confirmed in 1.1's planning pass — only the native `Gun` mesh component + GAS abilities). Ammo lives on the already-existing `S_EquipmentSlot` struct's `CurrentAmmo`/`ReserveAmmo` fields (per-slot, in `BP_EquipmentComponent::EquipmentSlots`), not as standalone weapon-class variables — avoids duplicating state that `Server_EquipItem` was already seeding from `DT_Weapons`' `MagazineSize`/`DefaultReserveAmmo`.
- `BP_EquipmentComponent` additions: `bIsReloading` (replicated+RepNotify), `ReloadTimerHandle`, `DefaultReloadDuration=2.0`, `ReloadingSlotIndex`/`ReloadingItemID` (server bookkeeping); pure helpers `GetActiveAmmo()`/`CanReload()`; `RefreshAmmoTags()`/`CancelReload()`; RPCs `Server_Reload()`→`FinishReload()` (mid-reload slot-switch safe — aborts and grants no ammo if the active slot changed) and `Server_ConsumeAmmo(Count)` (intentionally caller-less — no code path decrements ammo on fire yet; that lands with task 2.2's raycast-firing rework). Cleanup (`CancelReload`+`RefreshAmmoTags`) hooked into `Server_SetActiveSlot`/`Server_CycleActiveSlot`/`Server_RemoveEquipment`/`Server_EquipItem`/`RestoreEquipment` so switching weapons mid-reload can't misdeliver ammo.
- Gate, not decrement: new gameplay tags `State.Weapon.NoAmmo`/`State.Weapon.Reloading` added to `GA_FireGun`/`GA_FireRifle`'s `ActivationBlockedTags` (now 5 tags total, verified via CDO read-back) — firing is blocked while reloading or empty, but nothing yet sets ammo to 0 since `Server_ConsumeAmmo` has no caller. This is expected, not a bug, until 2.2.
- Deviation: no reload animation/montage — `S_WeaponData` has no Montage/duration field and no reload Montage assets exist in the project (only bare AnimSequences); real per-weapon reload timing and animation is deferred to a later content pass. Reload duration is a single component-level `DefaultReloadDuration` (2.0s) for now.
- Replication note: known limitation, see `docs/BUGS.md` — "Ammo replication is unconditioned (bandwidth concern)."
- `AmmoItemID` is unset on every `DT_Weapons` row — reserve-ammo replenishment from inventory pickups is not implemented; reserve only comes from `DefaultReserveAmmo` at equip time. Flagged for whoever builds loot drops (task 6.x).
- Input: new `IA_Reload` mapped to `R` in IMC_Default; controller-side chain built in `BP_PlayerController_ZombieStore` with a dangling Cast exec pin — this is the 5th entry on the known Monolith manual-editor punch list (alongside IA_EquipSlot1/2/3, IA_CycleWeapon from 1.1/1.2): a human needs to drop in an `EnhancedInputAction IA_Reload` node and wire its Started pin to Cast node `K2Node_DynamicCast_4` in that graph.
- Compile: both touched Blueprints 0 errors/0 warnings. Saved.
- Manual testing needed (once the punch-list wiring above is done): 2-client listen-server — press R with a full mag (no-op), empty a mag via console `Server_ConsumeAmmo`, confirm firing blocks (NoAmmo tag), reload and confirm reserve→magazine transfer after the 2s delay and firing resumes, then start a reload and switch weapon slots mid-reload to confirm ammo isn't misdelivered to the wrong slot.

[x] 2.2 Fast-Tracer Raycast Weapon Integration

Standardize all firing logic to use line-trace (raycast) on the server.

Implement visual "fake projectile" fast-tracers (Niagara particle systems or beam emitters) spawned from muzzle to impact point to simulate projectiles visually without ballistic physics overhead.

STATUS NOTE (2.2, resumed from a stopped prior session — see former docs/TASK_2.2_HANDOFF.md, now deleted): closed all 8 punch-list gaps left by that session.
- `GA_BP_FireWeapon` EventGraph wired: `Server_ConsumeAmmo(Count=1)` now fires once per trigger-pull immediately after the ammo-gate passes (server branch), decrementing on every shot regardless of hit/miss. `Multicast_FireTracer` now fires on both outcomes — hit path uses the `LineTraceForObjects` `BreakHitResult` ImpactPoint as BeamEnd, miss path uses the computed trace-end vector. All 4 previously-dangling Branch else-paths (out-of-ammo, `HasAuthority`-else, trace-miss, ASC-invalid) plus the post-`ApplyGameplayEffectSpecToTarget` continuation now fan into the existing `EndAbility` node (reused, not duplicated) so the server-side `LocalPredicted` execution always terminates.
- `GA_BP_FirePistol` / `GA_BP_FireRifle` created as plain subclasses of `GA_BP_FireWeapon` — no per-weapon graph overrides, since `S_WeaponData` has no fields (TraceRange/FireMontage/TracerFX/MuzzleSocketName all stay at parent defaults) that would drive ability-level tuning differences. Intentional, not a placeholder.
- `BP_EquipmentComponent::GrantActiveWeaponAbility`'s `K2_GiveAbility` `InputID` pin fixed from `-1` to `3` (legacy input convention), matching the other input-bound abilities.
- `BP_HeroCharacter::OnASCReady`'s legacy hard-coded `Give Ability GA_FireGun` (InputID 3) + `Set GunAbilityReference` double-grant path removed (4 nodes deleted); only the parent-class `OnASCReady` forwarding call remains.
- `DT_Weapons` `Pistol`/`Rifle` rows' `GrantedAbility` repointed from legacy `GA_FireGun_C`/`GA_FireRifle_C` to `GA_BP_FirePistol_C`/`GA_BP_FireRifle_C`; verified via read-back. `Bat` row left untouched (melee, out of scope — task 3.1).
- Checked `BP_PlayerController_ZombieStore` per the prior handoff's flagged Monolith EnhancedInputAction limitation: all input chains relevant to this task (IA_EquipSlot1/2/3, IA_CycleWeapon, IA_Reload) are already fully bound and wired with no dangling exec pins — resolved manually in-editor since the handoff was written. No `TEMP_` placeholder nodes were needed; this Blueprint was not modified.
- Compile: `GA_BP_FireWeapon`, `GA_BP_FirePistol`, `GA_BP_FireRifle`, `BP_EquipmentComponent`, `BP_HeroCharacter` all 0 errors/0 warnings. `DT_Weapons` updated and verified. All saved via `save_packages`.
- Manual testing needed: 2-client listen-server — equip pistol/rifle via DataTable-driven grant only (confirm no double-grant / no duplicate ability warnings now that the legacy `BP_HeroCharacter` grant is removed), fire and confirm ammo decrements every shot (hit and miss), confirm tracer VFX renders on both hit and miss, confirm damage applies only on hit, empty a mag and confirm firing blocks on `NoAmmo`, and confirm the ability's server execution actually ends each activation (no lingering "ability still active" state after repeated fires).

STATUS NOTE (2.2 follow-up, 2026-09-25 — fire rate + hold-to-fire):
- Attack rate is per weapon row: new `S_WeaponData.AttackInterval` (float, seconds between attacks), set on all 13 `DT_Weapons` rows.
- Enforcement: `/Game/Characters/Abilities/GE_WeaponCooldown` (HasDuration, grants `Cooldown.Weapon.Attack`) is applied to the owner on every shot, with duration overridden per shot via `SetDuration` from the row's `AttackInterval`. This is data-driven rather than `CooldownGameplayEffectClass`, so rows that share an ability class (LeverAction → FireRifle, SawedOff → FireShotgun) still get their own rates. `Cooldown.Weapon.Attack` is in `ActivationBlockedTags` on `GA_BP_FireWeapon` and all 6 `GA_BP_Fire*` subclass CDOs. Those subclasses were also missing `State.BuildMode`, which has now been added.
- Hold-to-repeat: ActivateAbility sets `bFireHeld` and starts `WaitInputRelease`, then calls the custom event `FireShot`. `FireShot` applies the cooldown, fires, then `WaitDelay(interval)` and re-calls itself while the button is held and the player is not in build mode.
- An empty magazine or a reload ends the loop; the player must press fire again after reloading.

3. Melee Weapons Implementation

[x] 3.1 Melee Weapon Base Class (AMeleeWeaponBase)

Create AMeleeWeaponBase derived from AWeaponBase or actors:

Attack animation states (Swing, Recovery).

Hit detection using box/capsule sweeps along the weapon swing arc.

[x] 3.2 Server-Validated Melee Damage

Implement server-side overlap/sweep validation to prevent client-side hit exploitation.

Apply impulse force to zombie ragdolls or hit targets upon successful melee impact.


STATUS NOTE (3.1 + 3.2, built together):

- Ability-vs-Actor deviation: no standalone `AMeleeWeaponBase` actor was created. Following the same architecture already established for guns (1.1/2.2 — no separate weapon-class hierarchy, all firing/swing logic lives in a `GDGameplayAbility`), melee swing/hit-detection/damage all live in a new ability Blueprint, `/Game/Characters/Abilities/GA_BP_MeleeAttack`. This keeps melee consistent with `GA_BP_FireWeapon`'s pattern (GAS ability granted per-slot via `BP_EquipmentComponent`) instead of introducing a second, parallel weapon-actor architecture.
- Architecture note: ability logic was originally built as a `K2_ActivateAbility` function-graph override so `PlayMontageAndWait` (via `gas_query add_ability_task_node`) could be wired against it, but that tool hardwires its latent task node into `EventGraph` regardless of which graph the rest of the ability lives in. Resolved by migrating the full function-graph (40 nodes, all internal wiring intact) into `EventGraph` via `blueprint_query copy_nodes`, wiring the final montage-branch connections there, then removing the now-redundant function override via `remove_function`. Net effect is identical to the intended design — ability activates via `Event ActivateAbility` in `EventGraph` — just reached by a different path than originally planned.
- Swing/Recovery: implemented via `PlayMontageAndWait` on `SwingMontage`/`SwingSectionName` (variables on the ability, section-driven so a single montage can support multiple weapon swings later); `OnCompleted`/`OnBlendOut`/`OnInterrupted`/`OnCancelled` all funnel into `K2_EndAbility`.
- Hit detection: server-authoritative box sweep along the melee weapon's swing arc, anchored to `GetAvatarActorFromActorInfo` (the character) for `GetActorForwardVector`/`GetActorLocation`/`GetActorRotation` — not the camera, per this project's standing camera-anchoring gotcha. Multi-hit: sweep results are iterated and damage/impulse applied per unique hit actor; no per-hit `GetEffectContext`/`EffectContextAddHitResult` enrichment was added for the multi-target case (kept consistent with `GA_BP_FireWeapon`'s existing single-context pattern; can be revisited if per-hit contextual data is needed later).
- Server validation: sweep and all damage/impulse logic execute only on the `HasAuthority` branch, matching `GA_BP_FireWeapon`'s pattern — no client-side hit-exploit path exists.
- Damage: `GE_MeleeDamage` uses the same SetByCaller (`Data.Damage`) pattern as `GE_GunDamage` (`MakeOutgoingGameplayEffectSpec` → `AssignTagSetByCallerMagnitude` → `BP_ApplyGameplayEffectSpecToTarget`). Bug found and fixed: `GE_MeleeDamage` was missing its damage execution calculation entirely (`executions: []`, an incomplete carry-over from its original duplication off `GE_GunDamage`) — the whole SetByCaller chain would have silently applied zero damage. Fixed by adding `GDDamageExecCalculation` via `gas_query add_execution`; verified against `GE_GunDamage` for parity.
- Impulse: `AddImpulseAtLocation` applied to hit actors gated on `IsSimulatingPhysics` — generic, not zombie-specific, since `ACharacter_ZombieBase`/ragdoll setup doesn't exist yet (task 4.1). Any physics-simulating actor in the sweep will react correctly once hit; zombie ragdoll behavior itself is deferred to 4.1.
- Tag: ability tagged `Ability.Skill.Ability2` (this project's existing tag convention for the second equip-slot-driven ability, mirroring `GA_BP_FireWeapon`'s `Ability.Skill.Ability1`-style tagging). `ActivationBlockedTags` deliberately omits the ammo-related tags (`State.Weapon.NoAmmo`/`State.Weapon.Reloading`) that gate `GA_FireGun`/`GA_FireRifle` — melee has no ammo concept.
- `DT_Weapons` Bat row `GrantedAbility` repointed from `None` to `GA_BP_MeleeAttack_C`; verified via read-back. Bat's `WeaponMesh` remains `None` (unsourced placeholder art, out of scope here, same caveat already flagged under 1.1).

STATUS NOTE (3.2 follow-up, 2026-09-25 — swing rate + hold-to-attack):
- `GA_BP_MeleeAttack` uses the same per-row `S_WeaponData.AttackInterval` and `GE_WeaponCooldown` / `Cooldown.Weapon.Attack` enforcement as guns; see the 2.2 follow-up note. `Cooldown.Weapon.Attack` is in its `ActivationBlockedTags`.
- Hold-to-repeat: ActivateAbility sets `bAttackHeld` and starts `WaitInputRelease`, then calls the custom event `SwingOnce`. `SwingOnce` applies the cooldown and plays the montage (its delegates are unwired, so they no longer end the ability). On the server it runs the unchanged box-sweep/damage/impulse chain, then `WaitDelay(interval)`, and re-calls itself while the button is held and the player is not in build mode.
- Input: no new input action was added. Melee reuses the existing equip-slot-driven ability-grant pattern (`BP_EquipmentComponent::GrantActiveWeaponAbility`, InputID 3, same as guns) — equipping the Melee slot grants `GA_BP_MeleeAttack` on the same legacy fire-input binding already wired for guns. No `TEMP_` placeholder needed; this task did not touch `IA_Interact`/`BP_InteractionProbe` (2.1 hold) or task 5.3 work.
- Tooling gotcha discovered and worked around: see `docs/BUGS.md` — "Monolith tooling: `auto_layout(formatter="vesper")` can silently duplicate/corrupt nodes." Repaired by removing the 3 duplicate nodes and restoring the 3 affected connections to their original targets; final graph compiles clean. Did not re-run `auto_layout` afterward to avoid re-triggering the bug — current node layout is functional but not vesper-formatted.
- Compile: `GA_BP_MeleeAttack` and `GE_MeleeDamage` both 0 errors/0 warnings. `DT_Weapons` write verified via read-back. All three saved via `editor_query save_packages`.
- Manual testing needed: equip the Melee (Bat) slot, confirm `GA_BP_MeleeAttack` is granted and fires on the existing melee input trigger; swing near a physics-simulating actor (e.g. a loose prop) and confirm the box sweep registers a hit, `GE_MeleeDamage` applies damage (check via `GetActiveEffects`/health if available), and `AddImpulseAtLocation` visibly shoves the hit actor; confirm nothing fires client-side without server authority (test with a listen-server + remote client). Ragdoll-specific impulse behavior can't be meaningfully tested until `ACharacter_ZombieBase` (task 4.1) exists.
STATUS NOTE (3.2 follow-up, 2026-09-25 — melee swing animation + hit on notify):
- New Blender-keyed swing: `Tools/Characters/blender_melee_anim.py` (tunable KEYS block; source `PlaceholderAssets/Blender/A_MeleeSwing.blend`) → `PlaceholderAssets/FBX/A_MeleeSwing.fbx` → `Tools/Characters/ue_import_melee_anim.py` → `/Game/Characters/Hero/Animations/A_MeleeSwing` (30 fps, 22 frames, 0.7 s). Reference skeleton FBX comes from `Tools/Characters/ue_export_mannequin.py`.
- `AM_MeleeSwing`: slot `UpperBody`, section "Swing", blend 0.05/0.15. `AnimNotify_GenericEventByTag` at 0.3333 s (frame 10, the weapon's half arc) sends `Event.Montage.MeleeHit` (new tag in `DefaultGameplayTags.ini`).
- `GA_BP_MeleeAttack.SwingOnce`: ends any stale `ActiveHitWait` task, plays `SwingMontage`=`AM_MeleeSwing` at rate clamp(length / CurrentAttackInterval, 0.5, 2), then a Sequence runs `WaitGameplayEvent(Event.Montage.MeleeHit)` → the hit-resolution chain, in parallel with the `WaitDelay(interval)` → repeat check. The hit now lands on the notify, not after a fixed delay.
- The notify is on the default track "1", not "Hit". See docs/BUGS.md — "Monolith animation.add_notify can't create a new notify track."
- Automation: 45/45 PASS (no regressions). Nothing tests the notify-driven hit itself yet. Server-side firing still needs checking with a manual listen-server + client PIE test. User PIE check 2026-09-25: "the melee seems to work well".
4. Zombie AI & Horde Spawning Manager

[x] 4.1 Zombie Base Character (ACharacter_ZombieBase)

Create ACharacter_ZombieBase derived from ACharacter.

Add UHealthComponent (replicated).

NavMesh Agent setup with custom locomotion speeds (walk/jog/sprint variations).

Attack Component (UZombieAttackComponent) for melee sweeps against players or breach barriers.

STATUS NOTE (4.1, partial — locomotion state + attack component built, health/navmesh/AI still open):

- `BP_ZombieBase` (Blueprint, parented to the existing `BP_Zombie_Base` in `GASDocumentation/Characters/Minions/Zombie`, not a new native `ACharacter_ZombieBase` — this project builds Blueprint-first per standing preference): added `WalkSpeed`/`JogSpeed`/`SprintSpeed` (float, category Locomotion) and replicated `CurrentMovementState` (`E_ZombieMovementState` enum). `Server_SetMovementState` function wires `NewState` into `CurrentMovementState` then switches on it to drive `MaxWalkSpeed`. No custom NavMesh agent setup was added in this pass — locomotion speed variation exists, but the AI-driven walk/jog/sprint selection itself is deferred to 4.2's behavior tree work.
- `BP_ZombieAttackComponent` (plain `ActorComponent`, not `UZombieAttackComponent`/native) built as the melee-sweep attack component: `SwingRange`/`SwingHalfSize`/`ImpulseStrength`/`MeleeDamageEffect` variables (category MeleeAttack, instance-editable) + `PerformMeleeAttack` function mirroring `GA_BP_MeleeAttack`'s box-sweep → `MakeOutgoingSpec` → `BP_ApplyGameplayEffectSpecToTarget` → `AddImpulseAtLocation` pattern, anchored to actor transform (`GetOwner`), not camera. Object-type filter (`ObjectTypeQuery1/2/3`) and impulse/damage wiring mirror `GA_BP_MeleeAttack`'s `EventGraph` exactly.
- Deviation: because this is a plain `ActorComponent` (not a `GameplayAbility`), it can't use ability-only nodes (`GetAvatarActorFromActorInfo`, `MakeOutgoingGameplayEffectSpec`, `AssignTagSetByCallerMagnitude`). Substituted `GetOwner` for actor context and `AbilitySystemComponent::MakeOutgoingSpec`/`MakeEffectContext` (called directly on the source actor's ASC) in place of the ability-context equivalents. Functionally equivalent GAS spec-creation path, just not ability-scoped.
- Deviation: `MeleeDamageEffect` defaults to the existing `/Game/Characters/Abilities/GE_MeleeDamage` (the player melee GE built in 3.1/3.2) as a placeholder — no zombie-specific damage GE exists yet. Variable is instance-editable so it can be swapped per-zombie-type later without a graph change.
- Deliberately skipped (out of scope for this pass, matching the task wording's narrower ask): `HasAuthority` server-gating branch and montage-play logic that `GA_BP_MeleeAttack` has (this component has no ability context to gate off of the same way; server authority should be enforced by whatever AI/BT logic calls `PerformMeleeAttack` in 4.2, not inside the component itself — flagging so it isn't forgotten).
- Not done in this pass: `UHealthComponent` (replicated), NavMesh agent setup, and wiring `PerformMeleeAttack` into any actual call site (no BT/AI exists yet to invoke it). Task 4.1 is not fully closed — remaining work is health component + navmesh + hookup, most of which naturally overlaps 4.2's AI controller work.
- Compile: `BP_ZombieBase` and `BP_ZombieAttackComponent` both 0 errors/0 warnings. All three assets (`BP_ZombieBase`, `BP_ZombieAttackComponent`, `E_ZombieMovementState`) saved via `editor_query save_packages`.
- Manual testing needed: none yet — `PerformMeleeAttack` has no call site wired in, so there's nothing to trigger in-game until 4.2's AI controller calls it. Once wired, retest the same box-sweep/damage/impulse behavior verified for `GA_BP_MeleeAttack` in 3.1/3.2, but from a zombie actor.

STATUS NOTE (4.1 update, closing out — NavMesh agent setup complete, task now fully satisfied):

- Health-component requirement satisfied without new work: `BP_ZombieBase` already applies `GE_ZombieAttributes` (via `DefaultAttributes` on the inherited `GDCharacterBase`), which grants MaxHealth/Armor/MoveSpeed etc. through the shared `GDAttributeSetBase` — the same replicated Health/death pipeline `BP_HeroCharacter` uses. No parallel `UHealthComponent` was added, per the project's standing rule that `AGIS_CombatManager`/GAS attributes are the single shared health system.
- NavMesh agent setup added on `CharMoveComp` (`GDCharacterMovementComponent`, native): read `CollisionCylinder` capsule first (CapsuleRadius=34, CapsuleHalfHeight=90) and matched `NavAgentProps` to it: `AgentRadius=34`, `AgentHeight=180` (2x half-height), `AgentStepHeight=45` (matches existing `MaxStepHeight`). Movement flags set ground-only per design ask: `bCanJump=False`, `bCanSwim=False`, `bCanCrouch=False` (was already False), `bCanFly=False` (was already False), `bCanWalk=True` (unchanged). RVO avoidance enabled: `bUseRVOAvoidance=True` (was False), `AvoidanceWeight=0.5` (was 0.0 — engine default is non-functional at 0), `AvoidanceConsiderationRadius=300` (down from an oversized 500 default, more appropriate for a ~34-radius zombie capsule).
- `WalkSpeed`/`JogSpeed`/`SprintSpeed` verified already sane from the prior pass: 150/300/450 — within the suggested Walk 150-200 / Jog 300-350 / Sprint 450-550 ranges and consistent with `GE_ZombieAttributes`' MoveSpeed=300 baseline (Jog). No changes made.
- Compile: `BP_ZombieBase` 0 errors/0 warnings. Saved via `blueprint.save_asset`.
- Did not touch `BP_ZombieAttackComponent` (no changes needed) or `E_ZombieMovementState`. Did not touch Phase 2 task 2.1 (`BP_InteractionProbe`/`IA_Interact`) or task 5.3 holds.
- Task 4.1 is now fully closed: health (pre-existing GE), attack component (prior pass), NavMesh agent (this pass) all satisfied.

[x] 4.2 Zombie AI Controller & Behavior Tree (BT_Zombie)

Create AAIController_Zombie using Blackboard & Behavior Tree:

Priority 1: Target nearest active player within sight/hearing radius.

Priority 2: If no line of sight, target nearest Breach Point (ABreachPoint) to enter the store.

Priority 3: If inside store and path blocked by player-placed defense, attack defense actor.

STATUS NOTE (4.2, Priority 1 fully implemented; Priorities 2-3 deliberately stubbed pending 5.1/Phase 4):

- Built under `/Game/Characters/AI/`: `BB_Zombie` (Blackboard: `TargetActor` Object, `TargetLocation` Vector, `bHasLineOfSight` Bool, plus auto `SelfActor`), `BT_Zombie` (Behavior Tree), `AIC_Zombie` (AAIController Blueprint). `BP_ZombieBase.AIControllerClass` updated from the inherited `AIC_Minion` default to `AIC_Zombie`; `AutoPossessAI` left unchanged at `PlacedInWorldOrSpawned` (confirmed matches sibling `BP_Minion`-style convention).
- `AIC_Zombie`: `OnPossess` -> `RunBehaviorTree(BT_Zombie)`, no explicit `UseBlackboard` call needed (RunBehaviorTree handles it from the BT asset's own blackboard reference).
- `BT_Zombie` root is a Selector with 3 children in priority order:
  - Priority 1 (Sequence): decorators `BTD_WithinSenseRadius` (custom, SenseRadius=1500uu instance-editable) and `BTD_HasLineOfSight` (custom, channel-based `LineTraceSingle` occlusion check against Visibility channel, also writes `bHasLineOfSight` to the blackboard for debug visibility) gate the branch; services `BTS_FindClosestPlayer_C` (native, reused from the `BT_Minion` precedent rather than building custom target-acquisition — populates `TargetActor`) and `BTS_ZombieMovementState` (custom, drives `Server_SetMovementState` each tick: distance<500uu -> Sprint, else Jog, gated on `HasAuthority` + valid target) both tick on the Sequence. Children: `BTTask_MoveTo` (BlackboardKey=TargetActor, AcceptableRadius=150uu = melee range) -> `BTT_ZombieMeleeAttack` (custom task, casts to `BP_ZombieBase`, `HasAuthority`-gated, calls `PerformMeleeAttack` on `ZombieAttackComponent`) -> `BTTask_Wait` (1.5s attack-cooldown placeholder).
  - Priority 2 (Sequence, STUB at the time this note was written — since rewired and activated by task 5.2, see that STATUS NOTE below): decorator `BTDecorator_Blackboard` (Set check on `TargetLocation`) gated a single `BTTask_MoveTo` (BlackboardKey=TargetLocation, AcceptableRadius=150uu). Nothing wrote `TargetLocation` at this point — no `ABreachPoint` actor existed yet (task 5.1 not built), so this branch was dead code.
  - Priority 3 (STUB, deferred to Phase 4 per task scope): single `BTTask_Wait` (2.0s) placeholder in place of real Wander/Idle or defense-actor-attack behavior, since no defense-actor system exists yet. Documented as a real gap, not a false-complete.
- Numeric thresholds finalized: SenseRadius=1500uu, Jog/Sprint distance threshold=500uu, MoveTo AcceptableRadius/melee range=150uu, attack-cooldown Wait=1.5s, Priority-3 idle Wait=2.0s (all instance-editable/adjustable in the BT graph, not hardcoded in C++).
- `ai_query validate_behavior_tree` on `BT_Zombie`: 0 issues, 4 blackboard keys confirmed resolved (a `set_bt_blackboard` fix was needed mid-build — `create_behavior_tree`'s `blackboard_path` param did not take effect on first creation and the tree initially pointed at `BB_Minion`; corrected before validation passed).
- Compile: `BTT_ZombieMeleeAttack`, `BTS_ZombieMovementState`, `BTD_WithinSenseRadius`, `BTD_HasLineOfSight`, `AIC_Zombie`, `BP_ZombieBase` all 0 errors/0 warnings. Saved: `BB_Zombie`, `BT_Zombie`, `AIC_Zombie`, and all 4 custom BT node Blueprints, plus `BP_ZombieBase`.
- Did not touch Phase 2 task 2.1 (`BP_InteractionProbe`/`IA_Interact`) or task 5.3 work. `BP_HeroCharacter`/`BP_PlayerController_ZombieStore` were not touched at all this pass (not even read-only inspection was needed).
- Manual testing needed: place a `BP_ZombieBase` instance and a player pawn in a test level with a navmesh; confirm the zombie stays idle until the player enters ~1500uu AND has unobstructed line of sight, then chases (visually confirm Jog at range, Sprint under 500uu), performs a melee attack animation/damage tick when it reaches ~150uu, and waits ~1.5s before re-engaging. Priority 2 and 3 branches have no in-game trigger path yet and cannot be manually tested until 5.1 (breach points) and the Phase 4 defense-actor system exist respectively.

[x] 4.3 Spawner System (AZombieSpawnerManager)

Create AZombieSpawnerManager active during NightPhase:

Calculate total horde count based on BaseRunDifficulty + StoreAdvertisementLevel.

Wave logic: Spawns zombies at exterior spawn points outside store boundaries in controlled bursts within performance caps.

STATUS NOTE (4.3):

- Built `/Game/Characters/AI/BP_ZombieSpawnerManager` (parent `Actor`, `bReplicates=true`, single-instance manager, not one-per-spawn-point). Variables: `SpawnPoints` (`array:object:Actor`, instance-editable, designer-populated later — no spawn-point actors exist in the level yet, so a plain `AActor*` array was used rather than a dedicated spawn-point class per the task's explicit allowance), `ZombieClass` (`class:Actor`, default `BP_ZombieBase`), `BaseHordeCount`(5)/`DifficultyMultiplier`(2)/`AdvertisementMultiplier`(3) (all instance-editable ints), `BurstSize`(3)/`BurstInterval`(1.5s, instance-editable), plus transient runtime state (`CachedGameState`, `LastKnownPhase`, `PollTimerHandle`, `BurstTimerHandle`, `RemainingToSpawn`, `bWaveActive`).
- `CalculateHordeCount()` (pure): `HordeCount = BaseHordeCount + (BaseRunDifficulty * DifficultyMultiplier) + (StoreAdvertisementLevel * AdvertisementMultiplier)`. Constants above are the tunable defaults; formula is intentionally simple/additive per task wording.
- **Deviation flagged**: `StoreAdvertisementLevel` already existed on `BP_GameState_ZombieStore` and was reused as-is, but no `BaseRunDifficulty`-equivalent existed anywhere (GameState, GameMode, or `BP_GameInstance_NoBrainers`). Added a new variable `BaseRunDifficulty` (int, replicated, instance-editable, default 1, category "Store") to `BP_GameState_ZombieStore` as the simplest viable placeholder — this is the one touch to that shared class this pass, and it was a metadata-only `add_variable` call, not a graph edit (crash-risk protocol: verified via `editor.stop_pie` that no PIE session was running before any work, and no graph nodes were added/connected on `BP_GameState_ZombieStore` at all, only the variable add + a follow-up compile/save).
- Wave/burst spawn logic (`SpawnBurst`): branches on `SpawnPoints` array length — if empty, logs "SpawnPoints array is empty - skipping zombie spawn" via `PrintString` and returns cleanly (no error) rather than spawning; otherwise spawns `Min(BurstSize, RemainingToSpawn)` zombies per burst-timer tick, each at a randomly-selected spawn point's transform (`RandomIntegerInRange` + array `Get`, location/rotation read off the picked actor), decrementing `RemainingToSpawn` per spawn, and calls `StopWaveSpawning()` once `RemainingToSpawn <= 0`.
- Night-phase hookup: rather than editing `BP_GameMode_ZombieStore` (which actually owns `StartNightPhase`/`StartDayPhase`, not GameState as the task brief assumed) or binding GameState's `OnPhaseChanged` multicast delegate cross-actor, mirrored the existing proven pattern already used by `/Game/AI/Customer/BP_CustomerSpawner`: a server-gated 1.0s repeating `PollPhaseChange` timer (set in `BeginPlay` under a `HasAuthority` branch) compares `CachedGameState.CurrentPhase` against `LastKnownPhase` and calls `HandlePhaseChanged` only on an actual change. `HandlePhaseChanged` switches on `E_GamePhase`: `NightPhase` -> `StartWaveSpawning()`, `DayPhase`/`RunOver` -> `StopWaveSpawning()`. `BeginPlay` also does an immediate `Switch on E_GamePhase` right after caching state, so a spawner already in `NightPhase` when it begins play starts spawning right away (matches `BP_CustomerSpawner`'s convention). This required zero graph edits to `BP_GameMode_ZombieStore` and zero graph edits to `BP_GameState_ZombieStore`.
- `StopWaveSpawning` clears the burst timer via `K2_ClearAndInvalidateTimerHandle(BurstTimerHandle)`, sets `bWaveActive=false` and `RemainingToSpawn=0` — guarantees no runaway spawn timer survives into day phase.
- Neither `BP_HeroCharacter` nor `BP_PlayerController_ZombieStore` were touched. Phase 2 task 2.1 (`BP_InteractionProbe`/`IA_Interact`) and task 5.3 work were not touched.
- Compile: `BP_ZombieSpawnerManager` 0 errors/0 warnings (verified after every function graph and again after full EventGraph `BeginPlay`). `BP_GameState_ZombieStore` recompiled after the variable add: 0 errors/0 warnings. Saved both via `save_dirty_assets` (confirmed no PIE session running beforehand via `editor.stop_pie`).
- Manual testing needed: place one or more `TargetPoint`/spawn-point `Actor`s in an actual level and populate `BP_ZombieSpawnerManager.SpawnPoints` with them, place one `BP_ZombieSpawnerManager` instance in the level, then trigger night phase and confirm zombies burst-spawn at those points over time (not all at once), spawning stops cleanly when day phase starts, and the empty-array case (spawner placed with no spawn points assigned) logs and skips rather than erroring. This is out of scope for this pass since no spawn-point actors exist in any level yet.


5. Store Entry & Breach Point System

[x] 5.1 Breach Point Actor (ABreachPoint)

Create ABreachPoint placed at windows, glass doors, and vent hatches around store geometry.

Replicated state variables: float Health, bool bIsBreached.

Visual states: Intact -> Damaged -> Destroyed/Breached (collision disabled).

STATUS NOTE (5.1 + 5.2, built together — see architecture plan reconciled against existing zombie AI/attack systems before this pass):

- `/Game/Interactable/BP_BreachPoint` (Blueprint `Actor`, not `ABreachPoint` — Blueprint-first naming convention per `BP_ZombieBase`/`BP_ZombieSpawnerManager` precedent), implements new interface `/Game/Interactable/BPI_Breachable` (`ApplyBreachDamage(DamageAmount: float, DamageInstigator: Actor)`). Components: `BreachMesh` (StaticMeshComponent root, placeholder cube mesh — unsourced real window/vent art, same caveat pattern as the Bat weapon mesh in 3.1) + `NavModifier` (NavModifierComponent, `AreaClass=NavArea_Null` while intact).
- Replicated `Health` (OnRep) and `bIsBreached` (OnRep), instance-editable `MaxHealth`/`DamagedThreshold`. `RefreshBreachVisual` is the single choke point (mirrors `BP_ShippingCrate`'s `OnRep_X -> RefreshXVisual` pattern) driving visibility/collision/`NavModifier.AreaClass` for all three visual states — Intact (visible, collidable, nav-blocked) -> Damaged (tint via DMI once `Health/MaxHealth <= DamagedThreshold`) -> Breached (hidden, `NoCollision`, `NavArea_Default` so the footprint opens to nav). `ApplyBreachDamage` is `HasAuthority`-gated and calls `RefreshBreachVisual` directly server-side (server doesn't receive its own OnRep).
- `/Game/Characters/BP_ZombieAttackComponent::PerformMeleeAttack`: the previously-empty "hit actor has no ASC" branch of the existing box-sweep loop now checks `Does Implement Interface(BPI_Breachable)` and calls `ApplyBreachDamage` with a new instance-editable `BreachDamage` (~25.0) — reuses the existing melee sweep/damage path rather than adding a second one, per the architecture plan.
- Bug fix (4.1 correction, done in this pass since it sits directly in the function being edited): `PerformMeleeAttack`'s ASC-valid branch was missing `AssignTagSetByCallerMagnitude` before `BP_ApplyGameplayEffectSpecToTarget`, so `GE_MeleeDamage`'s SetByCaller `Data.Damage` was never assigned — **zombie melee was dealing zero damage to players** since task 4.1. Fixed by adding instance-editable `MeleeDamageAmount` (~15.0) and inserting the SetByCaller assignment, mirroring `GA_BP_MeleeAttack`'s pattern.
- `/Game/Characters/AI/BB_Zombie`: added `BreachTarget` (Object, base class Actor) key. `TargetActor`/`TargetLocation`/`bHasLineOfSight`/`SelfActor` untouched.
- `/Game/Characters/AI/BTT_FindNearestBreachPoint` (new BTTask_BlueprintBase, mirrors `BTT_ZombieMeleeAttack`'s Cast-to-`BP_ZombieBase`/`HasAuthority` gating style): `GetAllActorsOfClass(BP_BreachPoint)` filtered to `bIsBreached==false`, nearest-to-pawn selection, writes `BreachTarget`, one-shot `Server_SetMovementState(Jog)` (jog chosen over sprint — consistent with the "not actively chasing a player" feel), `FinishExecute` Success/Fail.
- `/Game/Characters/AI/BT_Zombie` Priority-2 Sequence rewired: `BTDecorator_Blackboard` gate retargeted from the always-unset `TargetLocation` key to `BreachTarget` (previously pointed at the wrong key, which is why the branch was dead). Children: `BTT_FindNearestBreachPoint` -> `BTTask_MoveTo` (BlackboardKey=BreachTarget, AcceptableRadius=150uu) -> `BTT_ZombieMeleeAttack` (unchanged — deals damage via the sweep with no explicit target) -> `BTTask_Wait`(1.5s). `validate_behavior_tree`: 0 issues. `BTS_ZombieMovementState` deliberately not attached to this Sequence (it drives Sprint/Jog off distance-to-`TargetActor`, which this branch doesn't use).
- Nav runtime generation: added `[/Script/NavigationSystem.RecastNavMesh]` `RuntimeGeneration=DynamicModifiersOnly` to `Config/DefaultEngine.ini` (project-level override; engine default was `Static`, under which the breach `NavModifier` toggle would never rebuild pathing). Known limitation: see `docs/BUGS.md` — "NavMesh `RuntimeGeneration` override doesn't retroactively apply to existing levels."
- NavLinkProxy (for non-flat traversal like climbing through a raised window) deliberately deferred — no store level/geometry exists yet to size it against. Documented as a real gap, not a false-complete, same as 4.2's Priority-3 stub language.
- Compile: `BPI_Breachable`, `BP_BreachPoint`, `BP_ZombieAttackComponent`, `BTT_FindNearestBreachPoint` all 0 errors/0 warnings. `BT_Zombie` validated clean. All saved.
- Not testable end-to-end yet — no store level exists (only `Map_Startup`, `AnimStarterPack/Showcase`, `L_AutomationTestBed`). Manual testing needed once a test level has real geometry + navmesh: confirm the `RecastNavMesh-Default` actor's `RuntimeGeneration` is `Dynamic Modifiers Only` (see caveat above), place a `BP_ZombieBase` with no line-of-sight/path to a player but a `BP_BreachPoint` in range, confirm it paths to and melee-attacks the breach point, confirm `Health` replicates down and Intact->Damaged->Breached visuals/collision converge on both server and client, confirm the nav footprint opens once breached, and separately confirm the 4.1 melee-damage fix — players now actually take damage from zombie melee (previously silently zero). Tune `BreachDamage`/`MeleeDamageAmount` placeholder values once damage-over-time feel is visible in play.

STATUS NOTE (correction + architecture change, later pass): the line-212 claim that `BTT_FindNearestBreachPoint` filtered to `bIsBreached==false` was false — the node graph only ever compared distance, with no `bIsBreached` read at all. Also, despite the 213 fix retargeting the gate to `BreachTarget`, that key was written *only* by `BTT_FindNearestBreachPoint`, which sat inside the very Sequence gated on `BreachTarget Is Set` — a self-deadlock, so the breach branch never ran. Separately, Priority-1 (chase) was gated on `BTD_WithinSenseRadius`/`BTD_HasLineOfSight`, so zombies also never moved toward the player until in view/LOS range. Fixed by:
  - `BT_Zombie` Priority-1 Sequence: removed the sense-radius/LOS decorators, gated only on `TargetActor Is Set` (both `BTS_FindClosestPlayer`'s target and the tree's own detection ranges were already unbounded — the decorators were the only thing blocking immediate movement).
  - New service `/Game/Characters/AI/BTS_ZombieBreachDecision` (root Selector, alongside `BTS_FindClosestPlayer`, 0.5s interval) is now the sole owner of `BreachTarget`: it runs `FindPathToActorSynchronously` to the player each tick (sticky-target early-out skips this while a valid unbreached `BreachTarget` is already set); if no valid non-partial path exists, picks the nearest unbreached `BP_BreachPoint` (this time actually filtered on `bIsBreached`); if a path does exist but its length is a significant detour vs. straight-line distance (`PathDetourRatio >= 1.3`), it additionally looks for an unbreached breach point within a 400uu corridor of the straight line to the player (`FindClosestPointOnSegment`) and targets that instead.
  - `BT_Zombie` root Selector reordered to breach-first, chase-second, both branches' Blackboard gates set to `FlowAbortMode = Both` so either branch can interrupt the other as `TargetActor`/`BreachTarget` change mid-tick. `BTT_FindNearestBreachPoint` removed from the tree (asset left on disk, unused) — its selection logic is superseded by the new service.
  - `BB_Zombie` gained debug keys `bHasPathToTarget` (Bool) and `PathDetourRatio` (Float).
  - `validate_behavior_tree`: 0 issues. Not yet manually tested in-editor (still no store level with real nav geometry) — see the manual test list above, plus: confirm zombies now move immediately without needing player in view range, and confirm a zombie with a valid-but-long path detours to break an in-between `BP_BreachPoint` when `Ratio >= MinDetourRatio` but ignores it when the direct route is already short.

[x] 5.2 The Breach Action

Zombies path toward unbreached ABreachPoint actors, attack them, and trigger breach events upon health depletion, allowing entry into the store interior via updated NavMesh links.

(See combined STATUS NOTE under 5.1 above — 5.1 and 5.2 were built and documented together.)

STATUS NOTE (5.1/5.2 follow-up, overnight session 2026-09-24): root-caused and fixed why
zombies weren't actually breaching through breach points and moving to the player despite
the tree/service wiring above being correct on paper. `BP_BreachPoint::GetApproachLocation`
was `BlueprintPure` and silently returned `(0,0,0)` whenever called cross-actor (as the real
`BTS_ZombieBreachDecision::WriteBreachApproach` call site does), despite compiling clean —
see `docs/BUGS.md` — "Monolith/Unreal gotcha: a `BlueprintPure` function with branching
logic can silently return zeroed output when called cross-actor (RESOLVED)" for the full
root cause and fix. Fixed by rebuilding the function as `BlueprintCallable` with identical
logic and rewiring both call sites. Also cleaned up `Map_Startup` (proper store-shaped wall
layout, breach points placed along the outside wall with real gaps cut in the wall geometry
at each breach point, navmesh rebuilt) so breach pathing has real geometry to test against.
Verified via a direct cross-actor function call (correct non-zero approach point) and two
independent full test-bed runs, both showing `Test_BreachPoint_ApproachLocation` and
`Test_BreachPoint_DamageBreaches` PASS. Still needs a real in-PIE confirmation (let a zombie
approach a breach point with the player behind it, confirm it beelines to the breach, breaks
through, and continues to the player through the wall gap) since the automation tests call
the functions directly rather than driving full BT execution over real time.

STATUS NOTE (zombie AI test coverage, overnight session 2026-09-24): added
`Test_Zombie_ChasesPlayerWhenTargetSet` to `BP_TestController` — the first automation test to
drive a live `BT_Zombie` over real time rather than calling a function directly. It spawns a
`BP_ZombieBase` a fixed distance from a target actor with a clear unobstructed path, waits
3.5s, and asserts the zombie moved a meaningful distance and got closer to the target,
covering the Priority-1 chase Sequence (gated only on `TargetActor Is Set`). PASSED in a full
90s test-bed run alongside all other tests except the pre-existing, unrelated
`Test_Equipment_ReloadReplenishesMagazine` GAS failure (see `docs/BUGS.md`). This is a first
step toward the "unit tests for zombies down the road" the breach-point fix session called
for; a similar live-BT test for the breach branch (zombie blocked from the player, confirm it
targets and paths to an unbreached `BP_BreachPoint`) is a natural next addition, not yet built.

STATUS NOTE (zombie breach-branch test coverage, overnight session 2026-09-24): added
`Test_Zombie_TargetsBreachPointWhenBlocked` to `BP_TestController`, closing the gap flagged
above. Spawns a `BP_ZombieBase` inside a sealed 4-wall box (new permanent
`L_AutomationTestBed` fixtures: `Wall_ZombieBreachTest_West/East/North/South` plus a
dedicated `BP_BreachPoint_ZombieBreachTest` just outside the box) so the zombie's navmesh
island is disconnected from the player regardless of the player's live position at test time,
guaranteeing `BTS_ZombieBreachDecision` finds no valid path and writes `BreachTarget`. After a
3s delay, the test reads the zombie's `BB_Zombie.BreachTarget` Blackboard key and asserts it
resolves to a valid `BP_BreachPoint`. No existing breach-logic asset was modified — test-only
addition. Verified PASS in a clean, single-session-scoped 150s full test-bed run (19 tests,
18 PASS, only the pre-existing unrelated `Test_Equipment_ReloadReplenishesMagazine` GAS
failure) — a first, 90s/mixed-session run produced an unreliable report due to session-log
mixing and insufficient duration for the now-longer `RunAllTests` chain; the retry with
explicit session-id scoping and 150s duration confirmed the true result. Item 5 (zombie AI
unit tests) from the overnight directive is now covered for both the chase and breach
branches.

6. Zombie Loot Drop System

[x] 6.1 Loot Table Architecture (FLootTable) & Drop Spawning

Data Table DT_ZombieLoot mapping zombie types to weighted item drop lists.

On ACharacter_ZombieBase::Die() (Server-side): roll against drop tables, spawn physical world pickup items with slight drop impulses, and clear zombie bodies after a set delay.

STATUS NOTE (6.1, built in two dispatch passes — data architecture, then death-hook wiring):

- New structs `/Game/Data/S_LootDrop` (ItemID, MinQuantity, MaxQuantity, DropChance float 0-1) and `/Game/Data/S_LootTable` (Drops array of S_LootDrop, MaxDrops, GuaranteedDropCount — both fields present but intentionally unenforced for now, each drop entry rolls independently). New DataTable `/Game/Characters/AI/DT_ZombieLoot` (row struct S_LootTable), single "Default" row (no zombie-type subclasses exist yet) with 3 entries keyed to real existing `DT_Items` rows: CannedBeans (60%), PistolAmmo (30%), ScrapMetal (45%). Deviation: per-item independent `DropChance` rather than a relative weighted-pool pick — a reasonable reading of "weighted drop list," but flagged in case true weighted-random-selection semantics are wanted later.
- `BP_ZombieBase` (only asset touched in the second pass): binds to the native `OnCharacterDied` delegate (`AGDCharacterBase`, runs server+client — all new logic gated `HasAuthority`) via a bound Function (`HandleZombieDied`) rather than a CustomEvent, since Monolith's `set_function_params` can't add parameter pins to CustomEvents. On authority, rolls `DT_ZombieLoot`'s "Default" row per-entry against `DropChance`, spawns existing `BP_ItemPickup` (Phase 2's pickup actor, reused rather than duplicated) with a randomized offset + `AddImpulse`, sets ItemID/Quantity on it, then fires a Custom Event (`BeginBodyDespawn`, EventGraph-hosted since `Delay` can't run in a plain Function graph) that waits `BodyDespawnDelay` (7.0s default, instance-editable) and destroys the zombie actor.
- Known gap: see `docs/BUGS.md` — "Zombie loot-drop impulse is likely a visual no-op."
- Tooling gotcha discovered: see `docs/BUGS.md` — "Monolith tooling: `add_node` with `MakeStruct` for Vector/Transform can produce uncompilable nodes." Worked around by using `KismetMathLibrary::MakeVector`/`MakeTransform` CallFunction nodes instead, which compile cleanly.
- Did not touch `DT_Items`/`S_ItemData`/`E_ItemCategory` (Phase 2 inventory, read-only reference), `BP_HeroCharacter`, `BP_PlayerController_ZombieStore`, or task 2.1's `BP_InteractionProbe`/`IA_Interact` hold.

[x] 6.2 Weapon Acquisition Path (Starting Loadout / Weapon Pickup)

Gap discovered during manual testing of 6.1 (not in the original task brief, added here as a tracked follow-up): there is currently no way to get a weapon into an equip slot in-game at all, which blocks testing combat and therefore loot drops.

Investigation findings:
- `BP_HeroCharacter` has `EquipmentComponent` (`BP_EquipmentComponent`) attached, but nothing anywhere in the project calls `Server_EquipItem` on it — confirmed via `search_nodes` across `BP_HeroCharacter` (no "Equip" hits) and `project_query find_references` on `BP_EquipmentComponent` (zero referencing assets). No starting loadout is granted on spawn.
- `BP_ItemPickup` (the pickup actor already reused by 6.1's loot-drop spawn logic) only calls `BP_InventoryComponent::Server_AddItem` on interact — the Phase 2 consumable/resource inventory (keyed off `DT_Items`/`S_ItemData`). It has no path to `BP_EquipmentComponent::Server_EquipItem` at all, so even a weapon-flagged item dropped by a zombie wouldn't actually equip.
- `IA_EquipSlot1/2/3`/`IA_CycleWeapon` (built in 1.1/1.2) only select/cycle which *already-occupied* slot is active — they don't put anything into a slot in the first place.
- Net effect: a fresh player currently has zero equipped weapons and no in-world mechanism to acquire one, making combat (and by extension, zombie loot-drop testing) untestable without a manual dev-only equip call.

Needs a design decision before implementation (not just a bug fix): is the intended acquisition path (a) a starting loadout granted on spawn/respawn (matching the existing join-order inventory restore pattern from the 6.1-era save system), (b) a weapon-specific pickup actor/interaction that calls `Server_EquipItem` against `DT_Weapons` (parallel to `BP_ItemPickup`'s `DT_Items`/`Server_AddItem` path), (c) some day-phase store-purchase flow (Phase 2 territory) that hands off into `EquipmentComponent`, or (d) some combination. Whoever picks this up should confirm the intended design with the user before building, since it touches both Phase 2 (store/purchase) and Phase 3 (equipment) systems.

- Compile: `BP_ZombieBase` 0 errors/0 warnings. All new/changed assets saved.
- Manual testing needed: kill a zombie in PIE as server and confirm `BP_ItemPickup` actors spawn near the death location per drop chances/quantities, confirm the zombie body disappears ~7s after death exactly once with no double-destroy errors across multiple clients, and separately judge whether the (currently likely inert) drop impulse needs `BP_ItemPickup` physics enabled for a proper "slight drop" scatter feel.

STATUS NOTE (6.2): Resolved as combination (a)+(b) — starting loadout (already-landed `GrantStartingLoadoutIfEmpty`/`EnsureEquipmentSlotsInitialized` on `BP_EquipmentComponent`, covers spawn/respawn) plus a weapon pickup path (this task's build). `BP_ItemPickup`'s `OnInteract` graph (EventGraph) now branches on `Does Data Table Row Exist(DT_Weapons, ItemID)` before its existing inventory-add path: if the ItemID is a `DT_Weapons` row, it gets the interacting actor's `BP_EquipmentComponent` and calls `Server_EquipItem(ItemID)`; otherwise it falls through unchanged into the pre-existing `BP_InventoryComponent::Server_AddItem` path. Both branches converge on the existing shared `Set bConsumed` → `Destroy Actor` tail. Compile: 0 errors/0 warnings. Verified in PIE: a `BP_ItemPickup` instance with `ItemID=Rifle` placed in `Map_Startup` (near `NetworkPlayerStart`/`NetworkPlayerStart2`, label `BP_ItemPickup_Rifle`) equips into a weapon slot on interact instead of going to inventory; non-weapon `DT_Items` pickups confirmed unaffected. Only `BP_ItemPickup` was touched — `BP_HeroCharacter`, `BP_EquipmentComponent`'s starting-loadout logic, `BP_InventoryComponent`, and `DT_Items`/`DT_Weapons` row data were left as-is.

STATUS NOTE (4.2, zombie AI bug pass): three zombie AI bugs found and fixed — no retargeting after killing a player (`BTS_FindClosestPlayer`), zombie-on-zombie friendly fire (`BP_ZombieAttackComponent::PerformMeleeAttack`), and dead zombies still rotating/attacking during their despawn delay (`BP_ZombieBase::HandleZombieDied`). All three compiled 0 errors/0 warnings and are saved. See `docs/BUGS.md` — "Zombies never retarget — stay locked on a dead player's corpse," "Zombies can damage other zombies (no faction filter on melee sweep)," and "Dead zombies keep rotating/attacking during their despawn delay" for root causes, fix details, and PIE-verification steps still needed.

