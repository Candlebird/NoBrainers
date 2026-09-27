# Phase 7: Zombie Variety, Combat Depth & Balance

Planned 2026-09-25 from the user's post-playtest list. The main complaint: the game was too easy,
and kiting zombies was the dominant strategy because every zombie behaved the same. All design
calls below were confirmed with the user in a Q&A before the overnight run. Don't re-litigate
them; if one turns out to be infeasible, log it in `docs/BUGS.md` and pick the closest fallback
noted on the task.

**Work order (user-set):** A (bugs) → B (zombie types) → C (animations) → D (horde AI) → E (balance)
→ F (game feel). Commit locally after each group (no push).

## Morning test checklist

_Filled in as groups land. Each line is something that needs manual PIE confirmation._

- **A.2/A.3:** Empty the mag (reserve > 0), pull trigger → click once + reload starts by itself. Spam fire during reload → nothing. Reserve 0 → click only, no reload. Other client doesn't hear the click.
- **A.4:** Fire to ≤25% of the mag → ammo text red + pulsing; reload/swap to melee → white, steady.
- **A.5:** Each shot kicks the view up and eases back; sustained SMG fire doesn't drift permanently; shotgun/sawed-off/magnum also shake. Check kick direction is UP.
- **A.1:** Fire until reserve < what the magazine needs, reload → magazine gains exactly the leftover reserve; reserve hits 0; nothing vanishes.
- **B/C (types, spawn, anims):** Night zombies claw out of the ground and can't be damaged during the climb, then chase. Placed/test zombies (no climb) act immediately.
- **B.8:** Night 1 = Shamblers only; Runners from N2, Spitters N4, Screamers N5, Brutes/Bloaters N6+. Specials more common at higher Ad level.
- **Speed:** Shamblers now jog, then sprint near you. Judge whether it's too hard.
- **Runner:** 2–3 s sprint bursts, leaping lunge at ~3–4 m, can't be outrun.
- **Brute:** roar + windup, straight charge, heavy damage + knockback (**check knockback on a remote client**). Smashes barricades. Sidestep → it hits the wall and is stunned ~1.5 s. Other zombies in its path get shoved.
- **Spitter:** holds 10–18 m, backs off when you close in. Green glob arcs and is dodgeable (and doesn't pop on the Spitter itself). Puddle lasts 5 s, damages + slows you, hurts zombies.
- **Screamer:** flees within 8 m. Shriek visibly speeds nearby zombies for 6 s and brings 2–4 extras (max 6 per Screamer).
- **Bloater:** swells 1.5 s near a player/barricade then pops, damaging players, barricades and zombies. Shooting it dead also pops it (once).
- **Headshots:** head hits do 1.5×, and per-type weak spots do 2× (gold hitmarker + ding added in K1).
- **Hit-react/stagger:** every hit flinches; shotgun/sawed-off/magnum/melee interrupt attack/movement ~0.4 s.
- **Death:** per-type death anim, then ragdoll thrown along the killing hit. If the body freezes instead, the physics asset (`PA_SK_Zombie`) isn't assigned. ≤8 bodies stay.
- **Loot/cash:** specials drop and pay more (Brute/Bloater most).
- **Two clients:** anims, climb, deaths and puddles look the same on both.
- **D.1:** At Night, zombies claw up at several points outside the store near each breach point; the climb sits on the ground (not floating/sunk — spawn Z is nav ground + 92).
- **D.2:** ~8% into Night, red "SURGE INCOMING" banner + groan; ~3 s later spawning speeds up for 20–30 s; 3 times per Night. Last ~63 s: "FINAL SURGE" banner and a heavy wave until dawn. **Co-op:** banner + groan on the client too.
- **D.3:** Chasing zombies approach from spread angles and curve in, going straight once within ~7 m. Breach behavior unchanged.
- **D.4:** Solo alive count never > 30; 2 players cap 35. Queued surge zombies trickle in after the surge ends. Screamer summons near the cap don't exceed it.
- **D.4:** queued surge spawns are **discarded when Night ends** (user confirmed 2026-09-26).
- **B.10:** One elite per surge with a colored light: blue Armored (~2× tanky), amber Swift (faster — confirm the speed actually applies), green Regenerating (heals after ~4 s without damage). Check the light sits at chest height, not at the feet. Elite drops at least 2 items; glow visible on host and client.

- **E.3 Spike:** zombies on a Spike lose HP every ~0.5 s; a Runner crossing Spike + Slow Strip dies or nearly dies.
- **E.3 Slow Strip:** zombies on/near the strip move at **half speed**, and it does not compound over repeated pulses; normal speed ~1 s after leaving. Shamblers too (C++ MoveSpeed floor lowered 150 → 25).
- **E.3 Gas:** packs inside the ~3 m radius lose HP steadily; surges thin out.
- **E.3 Swinging:** a Shambler/Runner in range dies in one hit (~every 1.5 s); a Brute at a barricade next to it dies in ~4 hits.
- **E.3:** traps never hurt players; no double loot from trap kills. **Co-op:** trap kills/slows show on a client. If traps hit nothing, check the zombie capsule object type is Pawn.
- **E.5:** damage a defense at night, reach Day → full HP (Build Menu HP text). A defense destroyed at night stays gone. Client sees the repaired HP. Build Menu has no Repair button; the text says "(auto-repairs at Day start)"; Sell still works.
- **Defense HP fix:** a hit for more than half a defense's current HP (e.g. Brute on a 100 HP barricade) no longer destroys it; it survives with the right HP and breaks only at 0. (Was a pure-node double-subtract in `BP_DefenseBase.ApplyBreachDamage`, found by `Test_Defense_AutoRepairAtDayStart`.)
- **E.6:** an elite pays ~3× its type cash; Shamblers pay 2.
- **E.1/E.2:** Nights 1–2 afford 1–2 defenses (Spike 60, Slow Strip 50, Barricade 50) and ammo bites (Pistol ammo 12). By Day 5–7 SMG/Long Rifle (250/350) and shelf Tier 3 are reachable. Pricier trinkets (Gold Watch 75, Antler Trophy 70, Vintage Coin 50) still sell.

---

## A. Weapon bugs & gun feel

- [x] **A.1 Reload with partial reserve zeroes all ammo (bug).** **DONE:** root cause was `ConsumeFromAmmoPool` re-evaluating its pure `Min(Requested, Pool)` after the pool write (pool already 0 → returned 0). Now cached in local `FoundConsumed` before the write. Covered by `Test_Equipment_ReloadPartialReserve` (+ `_ZeroReserveNoOp`), both PASS. When you reload with less reserve than
  it takes to fill the magazine, both the magazine and the reserve end up at 0. Expected:
  `Taken = min(MagSize - Mag, Reserve)`, then `Mag += Taken` and `Reserve -= Taken`. Area:
  `BP_EquipmentComponent` (`Server_Reload`/`FinishReload`, pooled reserve via
  `S_AmmoPoolEntry`; see `docs/AMMO_POOL_REDESIGN.md`).
- [x] **A.2 Auto-reload on dry-fire.** **DONE** in `GA_BP_FireWeapon` (children inherit): empty-mag false branch → if not reloading: local click, then `CanReload` → `Server_Reload`. Pulling the trigger with an empty magazine and reserve > 0 starts a
  reload. Dry-fire only: the reload never starts automatically after the last shot. Hold-to-fire
  must not retrigger it every tick while a reload is in progress.
- [x] **A.3 Dry-fire click.** **DONE** (`SFX_DryFire`, locally controlled only). An empty-trigger click SFX plays on dry-fire, alongside the auto-reload start.
- [x] **A.4 Low-ammo warning.** **DONE** in `WBP_HUD` `RefreshAmmo` (`Anim_LowAmmoPulse`; replaced the old red-at-0 tint). The HUD ammo count turns red and pulses at ≤25% of the magazine (`WBP_HUD`).
- [x] **A.5 Camera kick + recoil.** **DONE:** `S_WeaponData` RecoilPitch/RecoilRecoverySpeed/CameraShakeScale, `BP_HeroCharacter.AddRecoil` (+ timer recovery), `CS_WeaponKick`, called from `GA_BP_FireWeapon`. LeverAction got the fallback 0.6°. Per-weapon vertical kick with recovery (data on `DT_Weapons`), plus a
  small camera shake on shotgun, sawed-off and magnum shots.

## B. Zombie types

GDD §4: every type derives from one shared base class. All types reuse `SK_Zombie`, and each gets
its own animation set (group C). **Wrecker was cut by the user; see Proposals.**

- [x] **B.1 Type data model.** **DONE:** `DT_ZombieTypes` + `S_ZombieTypeData`; `BP_ZombieBase` applies its row on spawn (GE_ZombieTypeHealth / GE_ZombieSetMoveSpeed); children in `/Game/Characters/Zombies/`. A `DT_ZombieTypes` row per type: HP, speed(s), damage, attack range,
  loot table row, cash/loot tier, unlock night, base spawn weight, anim set. `BP_ZombieBase` reads its
  row on spawn. Each type is a thin Blueprint child (`BP_Zombie_<Type>`).
- [x] **B.2 Shambler.** **DONE:** `BP_Zombie_Shambler` (base row). The current zombie, re-expressed as the base row.
- [x] **B.3 Runner.** **DONE:** `BP_Zombie_Runner`: ToggleBurst sprint bursts + CheckLunge (lunge anim + LaunchCharacter, 3 s cooldown). It alternates a jog with 2–3 s sprint bursts and finishes with a leaping lunge
  attack. About 50% of Shambler HP. The player can't outrun it.
- [x] **B.4 Brute.** **DONE:** `BP_Zombie_Brute`: windup+roar → sweep-moved charge (1100 u/s, ≤1.5 s); player hit = 40 dmg + knockback; barricade = 100 breach dmg; zombies are shoved aside; wall = stun. 8 s cooldown. Tanky and slow. It periodically winds up and charges in a straight line: heavy
  damage plus knockback to players and barricades it hits. If the charge misses, it's briefly
  stunned. Sidestepping is the counter.
- [x] **B.5 Spitter.** **DONE:** `BP_Zombie_Spitter` + `BP_SpitterGlob` + `BP_AcidPuddle`: backs off <1000, lobs at 1000–1800 on 4 s cooldown. Glob ignores its owner (Spitter) via GetOwner. Keeps a 10–18 m range and lobs a visible, dodgeable arcing glob. The glob
  leaves a 5 s acid puddle (damage over time plus slow). It backs off when players close in. The
  acid hurts zombies too.
- [x] **B.6 Screamer.** **DONE:** `BP_Zombie_Screamer`: flees <800, shriek (15 s cd) buffs zombies in 1200 u (×1.4, 6 s) and calls `SpawnSummoned` (2–4, cap 6). Low HP; flees from players. Its shriek (on cooldown) gives zombies within
  ~12 m +40% move speed for 6 s and summons 2–4 extra Shamblers/Runners from the nearest spawn zone
  (per-Screamer cap).
- [x] **B.7 Bloater.** **DONE:** `BP_Zombie_Bloater`: 200 u trigger → 1.5 s swell → 400 u blast (60 dmg, `GE_BloaterBlast`) to anything with an ASC (zombies too) and breachables; also on death (once, `bExploded`). Slow. Explodes on death, or after a visible 1.5 s swell-fuse when it reaches a
  player or defense. The blast damages players, defenses **and zombies**.
- [x] **B.8 Staggered unlock.** **DONE:** `BP_ZombieSpawnerManager.PickZombieClassFor(Night, AdLevel)` / `ComputeSpawnWeight` read unlock night + weight from `DT_ZombieTypes`. Night 1: Shamblers only. Runners join on night 2, Spitters on 4,
  Screamers on 5, Brutes and Bloaters on 6+. Spawn weights shift toward special types with night
  number and Store Advertisement level.
- [x] **B.9 Headshots.** **DONE:** `BP_ZombieBase.GetHeadshotMultiplier` (head bone only, 1.5×), applied per pellet in `GA_BP_FireWeapon` (`bLastShotHeadshot` kept for F.1). 1.5× damage on head hits, all types. **Update (K1, 2026-09-26):** per-type weak spots added on top. `DT_ZombieTypes` `WeakSpot*` columns give Brute spine_03 from behind, Bloater spine_01 from the front, and Spitter neck_01 from the front, each at 2.0×. A weak-spot hit also counts as a headshot for the gold hitmarker. Bloater "early detonation" was not built.
- [x] **B.10 Elites: one per surge.** **DONE:** `BP_ZombieBase.MakeElite(Modifier)` (1 Armored / 2 Swift / 3 Regenerating) + `EliteRegenTick`, replicated `EliteModifier` → `OnRep_EliteModifier` lights `EliteGlowLight` (PointLight). Spawner makes the first zombie spawned after `BeginSurge` elite (`bSurgeElitePending`). `DT_ZombieLoot` row `Elite` (2 guaranteed drops). Test: `Test_Zombie_EliteModifierApplies`. Each horde surge (D.2) includes exactly one elite: a random type
  plus one modifier (Armored +100% HP / Swift +35% speed / Regenerating out of combat), a colored
  glow, and a guaranteed better loot roll.
- [x] **B.11 Per-type loot/cash.** **DONE:** `LootRowName` per type row feeds `Server_RollAndSpawnLoot`; `CashReward` per type. Special types and elites pay more than Shamblers (`DT_ZombieLoot`).

## C. Zombie animations (Blender)

All clips are keyframed by headless Blender scripts on the `SK_Zombie` rig
(`PlaceholderAssets/Blender/SK_Zombie.blend`). `.blend`/FBX sources go in `PlaceholderAssets/`,
and imports go under `Content/Characters/Zombie/Animations/<Type>/`. **Tone: mixed by type.**
Shambler and Bloater are goofy and floppy. Runner and Screamer are twitchy and unsettling. Brute is heavy.
Spitter sits in between.

- [x] **C.1 Per-type set.** **DONE:** Anim sets wired into `ABP_SK_Zombie` via C.3. **Blender side DONE:** 75 clips in `PlaceholderAssets/FBX/Zombie/` (`Tools/Characters/blender_zombie_anims.py`; fixed a pose-scale accumulation "spike" bug). Attack hit / Lob release ≈ 55% of clip length. **UE import DONE:** 75 AnimSequences under `/Game/Characters/Zombie/Animations/<Type>/` (HitReact = additive local space, frame 0 base). Set in the Anim BP pending (C.3). Each type gets: idle, walk, run (or type-specific gait), claw-out-of-ground
  spawn, 3 attack variations (randomly picked), an additive hit-react, and 3 death variations
  (randomly picked). Plus type-specific clips: Runner sprint + lunge, Brute charge wind-up/charge/stun,
  Spitter lob, Screamer shriek + flee run, Bloater swell.
- [x] **C.2 Spawn.** **DONE:** Per-type climb anim on spawn; `GE_SpawnInvulnerable` + AI inactive until the climb ends (`OnZombieActivated`). Every type claws up from the ground, each in its own style. The zombie is invulnerable
  and inactive until the climb ends (~1.5–3 s).
- [x] **C.3 Anim Blueprint.** **DONE:** `ABP_SK_Zombie`: BlendListByInt(ZombieAnimIndex) over 6 `BS_Zombie_*_Locomotion` → Slot → ApplyAdditive per-type HitReact (driven by `OnZombieHitReact`). Heavy hits stagger via `RegisterHit`; `BTT_ZombieMeleeAttack` aborts while staggered/action-locked. Locomotion blendspace per type, montage slots for attacks/spawn/specials,
  and an additive hit-react layer (the flinch plays on every hit). Heavy hits (shotgun, sawed-off,
  magnum, melee) also briefly interrupt the zombie's attack or movement.
- [x] **C.4 Death → physics.** **DONE:** **Fallback used:** `Multicast_PlayDeath` plays a random death anim ~0.5 s then `StartRagdoll` with impulse along the kill direction; spawner keeps ≤8 corpses (`RegisterCorpse`). See docs/BUGS.md — "C.4 uses ragdoll fallback, not PhysicalAnimationComponent blend." Death anim blended into physics through `PhysicalAnimationComponent`, with
  physics weight ramping up and an impulse along the killing hit's direction. **Fallback if the
  physics asset fights it:** play the death anim for ~0.5 s, then full ragdoll with the impulse. The
  body despawns later; oldest ragdolls are cleaned up once there are more than 8.

## D. Horde AI & spawning

- [x] **D.1 Ground spawn zones.** **DONE:** new `BP_ZombieSpawnZone` (`ZoneRadius`, `bZoneEnabled`, `GetRandomSpawnTransform`); spawner `CollectSpawnZones` at night start and rotates through zones (`GetNextSpawnTransform`), `ZSpawn_*` TargetPoints kept as fallback. One zone per `BP_BreachPoint` (6 in the store map, 2 in the test map, not the 7/4 first estimated), folder `SpawnZones`, ~12–15 m outward, on navmesh:
  - `Map_Store_Outdoors`: `ZSpawnZone_Breach_Front1` (-1489, -543, 0), `_Front2` (-1511, -169, 0), `_Front3` (-1520, 210, 0), `_SideL` (4956, -3816, 0), `_SideR` (5054, 3728, 0), `_Dock` (8446, 2216, 8).
  - `Test_Level_Zero`: `ZSpawnZone_BP_BreachPoint` (-929, 2451, 140), `ZSpawnZone_BP_BreachPoint2` (-1651, -2451, 140).
  Original spec: New spawn-zone actors outside the store in `Map_Store_Outdoors`,
  **added only; nothing the user hand-placed is moved or regenerated** (list every addition here).
  Mirror them in `Test_Level_Zero`.
- [x] **D.2 Horde surges.** **DONE:** spawner `ScheduleNextSurge` → `AnnounceSurge` (bumps replicated `GameState.SurgeSerial` / `bSurgeIsFinale`) → +3 s `BeginSurge` (queues `Max(6, HordeCount × 1.5 if finale)` into `PendingSurgeSpawns`, 3× tick rate) → `EndSurge` after 20–30 s (finale 60 s). Surges at 8% / 28% / 48% of night length + finale 63 s before end. `WBP_EventBanner.PollSurgeState` shows red "SURGE INCOMING" / "FINAL SURGE" banner + `SFX_SurgeGroan` when `SurgeSerial` changes. Original spec: About 3 surges per Night (3× spawn rate for 20–30 s) with calmer lulls
  between them, then a big finale wave in the last 60 s. A HUD banner plus groan cue gives ~3 s warning.
- [x] **D.3 Flanking / surround.** **DONE:** `BTS_ZombieBreachDecision.UpdateFlankLocation` gives each zombie a persisted signed angle (15–55°, BB `FlankAngle`) and writes a navmesh flank point (BB `FlankLocation`) while > 7 m from its target; `BT_Zombie` `Sequence_Flank` (between breach and chase) moves there, aborting when the key clears. Original spec: Zombies are spread across multiple breach points and approach
  targets from assigned angles (slot-around-target), instead of forming a single conga line.
- [x] **D.4 Alive cap.** **DONE:** spawner `ComputeAliveCap` (30 + 5 per extra player, max 45); `SpawnTick` only drains `PendingSurgeSpawns` while alive < cap (`ComputeSpawnAllocation`); Screamer `SpawnSummoned` clamped to the cap. Queued surge spawns are dropped at dawn (see checklist). Tests: `Test_ZombieSpawner_AliveCapFormula`, `Test_ZombieSpawner_SurgeQueueRespectsCap`. Original spec: 30 alive solo, +5 per extra player, 45 max. Surge spawns queue instead of
  overflowing the cap.

## E. Economy & balance pass

Target feel: **tight early, snowball late.** The first nights are scrappy (1–2 defenses, careful ammo);
by day ~5–7 a well-run store affords top-tier gear and upgrades. Edit the data directly and record
every change in the before/after table below with reasoning, so any line can be reverted.

- [x] **E.1 Prices of goods** (`DT_Items` sell prices, customer tolerance interplay).
  **DONE — DT_Items sell/discount prices rebalanced (table below).**
- [x] **E.2 Weapons, ammo, defense blueprint prices** (`DT_Weapons`, `DT_AmmoCatalog`, `DT_KioskCatalog`,
  `DT_DefenseBlueprints`).
  **DONE — weapon damage, ammo, kiosk and defense prices rebalanced (table below).**
- [x] **E.3 Trap usefulness.** The user found every trap (spike, slow strip, gas, swinging) near-pointless.
  Buff damage/uptime/area so each trap has a clear job against the new types.
  **DONE — root cause: every trap applied an empty GE once on overlap. Traps now pulse via a timer in BP_DefenseBase (ApplyTrapHit/TrapPulse) with per-trap interval/radius/damage/wear; Slow Strip halves MoveSpeed (GE_Slow ×0.5, 1 s, non-stacking; C++ floor 150→25).**
- [x] **E.4 Shelf tier upgrade curve** (`DT_ShelfTiers`) against the revenue each tier adds.
  **DONE — Tier1 150→140, Tier2 250→280.**
- [x] **E.5 Free auto-repair at Day start.** Every surviving defense restores to full HP for free when
  Day begins. Destroyed defenses stay destroyed (rebuy). Remove manual paid repair.
  **DONE — BP_GameMode_ZombieStore.AutoRepairDefenses at the end of StartDayPhase → BP_DefenseBase.RestoreFullHealth; Repair button, BP OnServerRepairDefense and C++ Server_RepairDefense removed; RepairCostPerHP set to 0.**
- [x] **E.6 Per-type loot/cash values** (with B.11).
  **DONE — cash rewards and loot chances (table below); elites pay 3× cash (BP_ZombieBase.EliteCashMult).**

Player movement is **out of scope** (user: leave the player alone).

### Before/after table

| Asset | Row / field | Before | After | Why |
|---|---|---|---|---|
| DT_Items | Pistol BaseSellPrice / DiscountCost | 80 / 35 | 30 / 13 | Selling found/starter weapons was an early cash exploit; tighten early income |
| DT_Items | Bat BaseSellPrice / DiscountCost | 30 / 12 | 15 / 6 | Selling found/starter weapons was an early cash exploit; tighten early income |
| DT_Items | PipeWrench BaseSellPrice / DiscountCost | 25 / 10 | 20 / 8 | Selling found/starter weapons was an early cash exploit; tighten early income |
| DT_Items | CanoePaddle BaseSellPrice / DiscountCost | 20 / 8 | 15 / 6 | Selling found/starter weapons was an early cash exploit; tighten early income |
| DT_Items | Rifle BaseSellPrice / DiscountCost | 120 / 55 | 90 / 40 | Selling found/starter weapons was an early cash exploit; tighten early income |
| DT_Items | Shotgun BaseSellPrice / DiscountCost | 150 / 65 | 120 / 52 | Selling found/starter weapons was an early cash exploit; tighten early income |
| DT_Items | FireAxe BaseSellPrice / DiscountCost | 70 / 30 | 60 / 26 | Selling found/starter weapons was an early cash exploit; tighten early income |
| DT_Items | LeverAction BaseSellPrice / DiscountCost | 160 / 70 | 135 / 58 | Selling found/starter weapons was an early cash exploit; tighten early income |
| DT_Items | SawedOff BaseSellPrice / DiscountCost | 110 / 50 | 105 / 45 | Selling found/starter weapons was an early cash exploit; tighten early income |
| DT_Items | GoldWatch BaseSellPrice / DiscountCost | 60 / 30 | 75 / 34 | Rare trinkets reward risky kills (snowball late) |
| DT_Items | AntlerTrophy BaseSellPrice / DiscountCost | 55 / 25 | 70 / 32 | Rare trinkets reward risky kills (snowball late) |
| DT_Items | VintageCoin BaseSellPrice / DiscountCost | 40 / 18 | 50 / 22 | Rare trinkets reward risky kills (snowball late) |
| DT_Weapons | LongRifle BaseDamage | 45 | 90 | Top-tier price needs a top-tier hit |
| DT_Weapons | LeverAction BaseDamage | 28 | 40 | Was weaker than cheaper guns |
| DT_KioskCatalog | PipeWrench Cost | 40 | 35 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | CanoePaddle Cost | 35 | 25 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | Machete Cost | 60 | 90 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | FireAxe Cost | 110 | 100 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | Magnum Cost | 250 | 150 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | LeverAction Cost | 275 | 225 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | SMG Cost | 175 | 250 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | LongRifle Cost | 300 | 350 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | SpikeTrap Cost | 75 | 60 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | SlowStrip Cost | 60 | 50 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | GasTrap Cost | 90 | 120 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_KioskCatalog | SwingingTrap Cost | 75 | 110 | Cheap early options, pricier late power; trap prices track their new usefulness |
| DT_AmmoCatalog | PistolAmmo Cost | 8 | 12 | Ammo should bite early |
| DT_AmmoCatalog | RifleAmmo Cost | 10 | 15 | Ammo should bite early |
| DT_AmmoCatalog | ShotgunShells Cost | 12 | 15 | Ammo should bite early |
| DT_DefenseBlueprints | SpikeTrap Cost | 75 | 60 | Kept in sync with the kiosk |
| DT_DefenseBlueprints | SwingingTrap Cost | 75 | 110 | Kept in sync with the kiosk |
| DT_DefenseBlueprints | SlowStrip Cost | 60 | 50 | Kept in sync with the kiosk |
| DT_DefenseBlueprints | GasTrap Cost | 90 | 120 | Kept in sync with the kiosk |
| DT_DefenseBlueprints | RepairCostPerHP (all 6 rows) | 1.0 (Turret 2.0) | 0 | Paid repair removed (E.5) |
| DT_ShelfTiers | Tier1 UpgradeCost | 150 | 140 | First upgrade reachable by ~Day 2 |
| DT_ShelfTiers | Tier2 UpgradeCost | 250 | 280 | Mid-game sink |
| DT_ZombieTypes | Shambler CashReward | 0 | 2 | Specials worth hunting; Shamblers pay a trickle |
| DT_ZombieTypes | Spitter CashReward | 10 | 12 | Specials worth hunting; Shamblers pay a trickle |
| DT_ZombieTypes | Screamer CashReward | 15 | 20 | Specials worth hunting; Shamblers pay a trickle |
| DT_ZombieTypes | Bloater CashReward | 15 | 20 | Specials worth hunting; Shamblers pay a trickle |
| DT_ZombieTypes | Brute CashReward | 25 | 40 | Specials worth hunting; Shamblers pay a trickle |
| BP_ZombieBase | EliteCashMult (new) | — | 3 | An elite kill pays 3× type cash |
| DT_ZombieLoot | Runner MaxDrops | 3 | 2 | Each special drops loot that fits its theme |
| DT_ZombieLoot | Screamer GuaranteedDropCount | 0 | 1 | Each special drops loot that fits its theme |
| DT_ZombieLoot | Screamer GoldWatch / VintageCoin / LuckyCharm / BigfootFigurine / AntlerTrophy | .015 / .0225 / .03 / .0225 / .015 | ×2 | Each special drops loot that fits its theme |
| DT_ZombieLoot | Spitter Bandage / MedKit / Painkillers | .0675 / .0225 / .0525 | ×2 | Each special drops loot that fits its theme |
| DT_ZombieLoot | Brute Nails / ScrapMetal / DuctTape | .09 / .11 / .12 | ×1.5 | Each special drops loot that fits its theme |
| DT_ZombieLoot | Bloater CannedBeans / SpoiledMeat / BeefJerky | .09 / .13 / .09 | ×1.5 | Each special drops loot that fits its theme |
| DT_ZombieLoot | Elite GoldWatch / VintageCoin / AntlerTrophy | .02 / .03 / .02 | ×2 | Each special drops loot that fits its theme |
| BP_Trap_Spike | Pulse interval / radius / damage / wear | one hit on overlap, empty GE | 0.5 s / 125 / 25 / 0.25 | Traps were near-useless (E.3) |
| BP_Trap_Swinging | Pulse interval / radius / damage / wear | one hit on overlap, empty GE | 1.5 s / 175 / 100 / 1.0 | Traps were near-useless (E.3) |
| BP_Trap_Gas | Pulse interval / radius / damage / wear | one hit on overlap, empty GE | 0.5 s / 300 / 8 / 0 | Traps were near-useless (E.3) |
| BP_Trap_SlowStrip | Pulse interval / radius / damage / wear | one hit on overlap, empty GE | 0.5 s / 200 / 0 / 0 + GE_Slow | Traps were near-useless (E.3) |
| GE_Slow | Duration / stacking | 3 s / by source | 1 s / by target, limit 1 | Halve speed while standing in the strip, no compounding |
| GDAttributeSetBase.cpp | MoveSpeed clamp floor | 150 | 25 | Let slows affect 150-speed walkers |

## G. Playtest fixes (2026-09-26)

From the user's first playtest of A–E.

- [x] **G.1 Upside-down spawns.** Some zombies spawn upside down at ~45°. **DONE:** zone, spawn-point and fallback spawn transforms used the full actor rotation. They're now yaw-only (`BP_ZombieSpawnZone.GetRandomSpawnTransform`, `BP_ZombieSpawnerManager.GetNextSpawnTransform`). **USER TEST:** no tilted zombies over a few nights.
- [x] **G.2 Spawn count scales with players.** Night 1 spawns far too many. Scale the horde count by
  player count; solo = ~60% of the current amount. **DONE:** `CalculateHordeCount` multiplies by `min(1, 0.6 + 0.4×(players−1))`, then ceil, with a floor of 1. Players come from `GameMode.GetLivingPlayerCount`. This covers the night count and surges. **USER TEST:** solo hordes are noticeably smaller.
- [x] **G.3 Weapon camera shake off.** Set every shake value to 0 for now (recoil kick stays). **DONE:** `DT_Weapons.CameraShakeScale` = 0 on all rows.
- [ ] **G.4 Blank surge banner.** The horde/surge banner pops up with no text. **PARTIAL:** no defect found statically; the surge literals changed to "HORDE SURGE INCOMING!" / "FINAL SURGE INCOMING!". **USER TEST:** check whether it still shows blank. See docs/BUGS.md — "Surge warning banner shows no text (not reproduced statically)."
- [ ] **G.5 Door fixation.** Zombies sometimes keep breaking doors after they have a clear path to
  the player. **DONE:** in `BTS_ZombieBreachDecision.ReceiveTickAI`, the "breach point not yet broken" branch had no exec out, so the path re-check never ran mid-breach. It now re-checks every tick and clears BreachTarget once a full path exists (the BT decorator already aborts on change). **USER TEST:** open a second route mid-breach; the zombie should leave the door within ~1 s.
- [x] **G.6 Run start.** The run starts at Dawn; starting cash 50; 4× starting pistol ammo. **DONE:** `BP_GameState_ZombieStore.StartingStoreCash` 250 → 50; `DT_AmmoTypes.PistolAmmo.DefaultStockpile` 48 → 192 (Max 500). Every new run already starts in Morning (= Dawn) via `BeginPlay → StartMorningPhase`. If a run didn't start at Dawn, that was most likely a resumed session save (`bResumeSessionOnStart`). **USER TEST:** start a new run with no save present: Morning phase, 50 cash, 192 pistol reserve.
- [ ] **G.7 Ammo pickup.** A distinct walk-over pickup that zombies drop and that refills part of
  the ammo pool automatically (separate from the sellable "ammo box" loot item). **DONE:**
  - New `/Game/Interactable/BP_AmmoRefillPickup`: a spinning, bobbing green can (`SM_AmmoPickup`, Blender) with a 60 cm overlap sphere, server-only.
  - It calls `BP_EquipmentComponent.Server_AddAmmo` for each ammo type the hero carries (Pistol 12 / Rifle 8 / Shotgun 6, instance-editable) and despawns after 60 s.
  - `BP_ZombieBase.Server_RollAndSpawnLoot` drops one at 12% (`AmmoDropChance`), or 100% for elites.
  - It still gets consumed when the carried types are already full, and has no pickup SFX yet (`PickupSound` is unset).
  - **USER TEST:** kill zombies; cans drop sometimes, always from elites; walking over one adds reserve ammo.
- [x] **G.8 Melee `CachedHero` Accessed None** in `GA_BP_MeleeAttack.RegisterHit` (spams while meleeing). **DONE:** the cast that set `CachedHero` had no exec input (never ran). A new cast in the live chain writes `PendingHitDirection`, which RegisterHit now reads. See docs/BUGS.md — "GA_BP_MeleeAttack has a dead CachedHero/CachedEquipment setup block."
- [x] **G.9 Melee range ×1.3.** **DONE:** `DT_Weapons.MeleeRange` ×1.3 (Bat/Shotgun 195, PipeWrench 169, Machete 208, FireAxe 221, CanoePaddle 273); the trace reads the row.
- [x] **G.10 Stockable shelf model.** A new, distinct shelf mesh that reads as "stock me" (Blender).
  DONE: `SM_StockShelf` (`PlaceholderAssets/`, `Tools/Props/blender_store_fixtures.py`, imported by
  `Tools/Props/ue_import_store_fixtures.py` into `/Game/Environment/StoreFixtures/`). It is a
  240 cm, 4-tier empty gondola with a glowing header. `BP_ShelfActor.ShelfMesh` uses it at z=-50,
  since actor pivots sit 50 cm above the floor. Slot fallback Z is now -20+28·row, matching the
  board tops. InteractionBox is (1,0,33) with extent 38×122×85. StockSign and StockFloorPad are hidden.
  The 12 placed shelves in Map_Store_Outdoors carried stale per-instance overrides of the old mesh.
  Only those three components were reset to the class defaults. USER TEST: shelves sit on the
  floor, stocked items rest on the boards, the category label is readable, and interact works
  from the front.
- [x] **G.11 Kiosk and checkout counter models.** Distinct meshes for each kiosk type and the
  checkout counter, so it's obvious they're interactable (Blender).
  DONE: `SM_CheckoutCounter` (belt, register, card reader, lane light) is on
  `BP_CheckoutCounter.CounterMesh`, and its old InteractionMesh cube is hidden.
  `SM_AmmoKiosk`, `SM_DiscountKiosk` and `SM_CloseShopStation` are on each BP's InteractionMesh.
  All sit at z=-50 (CloseShop at -160, matching its placed height). Discount, Upgrades and
  Advertising share `BP_DiscountKiosk`, so they share one model. USER TEST: each fixture sits on
  the floor facing into the store, the cashier side of the checkout is reachable, and every
  interact prompt still triggers.

## H. Playtest fixes, round 2 (2026-09-26)

From the user's playtest of G.

- [x] **H.1 Floating shelves, 2× size.** In game the shelves floated, although the BP viewport looked right. The placed shelves' component transforms didn't match the class defaults. **DONE:**
  - `SM_StockShelf` was rebuilt at about 2× size, fitting 4 items per row.
  - The `BP_ShelfActor` InteractionBox is now extent 38×218×170. The label moved up and was scaled.
  - Every placed shelf's components were reset to the class defaults. Three shelves moved slightly to clear walls or other fixtures.
  - **USER TEST:** shelves sit on the floor, 4 items per row, and interact works.
- [x] **H.2 Drops ignore pawns.** `BP_ItemPickup` and `BP_AmmoPickup` InteractionMesh and InteractionBox ignore the Pawn channel. **USER TEST:** stand on a dropped item; no spinning or launching.
- [x] **H.3 Weapon sounds.** Every sound is a synthesized placeholder (`Tools/Audio/synth_sfx.py`).
  - Each gun has a unique fire and reload sound: `BP_EquipmentComponent` WeaponFireSounds and WeaponReloadSounds maps, played via `Multicast_PlaySoundAtLocation`, with the fire sound played from `GA_BP_FireWeapon`.
  - `GA_BP_MeleeAttack` plays a whoosh on the swing and a clang on hit.
  - **USER TEST:** each gun sounds different when it fires and reloads; melee whooshes and clangs. The shooter on a remote client hears their own shot about one round trip late (multicast from the server).
- [x] **H.4 Zombie sounds.**
  - `BP_ZombieBase` HurtSound / DeathSound / AttackSound.
  - Hurt fires via the new C++ `OnHealthChangedBP` event and is throttled to once per 0.4 s. Death plays in HandleZombieDied, attack in Server_PlayAttackAnim.
  - The Bloater has no DeathSound, since it keeps its pop.
  - The defaults are set on each child CDO, because the parent defaults didn't propagate.
  - **USER TEST:** hurt, death and attack sounds play, and the hurt sound doesn't spam.
- [x] **H.5 Drag-and-drop stocking.**
  - C++ `UGDBlueprintLibrary::MakeItemDragOp` / `GetItemDragOpInfo`.
  - `WBP_InventorySlot` is a drag source (tag "Inventory"). `WBP_ShelfSlot` accepts drops onto empty slots and is a drag source (tag "Shelf"). `WBP_Inventory` accepts shelf drops, which take the item back.
  - In every case the SlotButton is HitTestInvisible, and clicks are routed through `HandleSlotClicked` on mouse-up, so click-to-trade still works. Slots show an amber hover tint.
  - See docs/BUGS.md — "Server_StockItemToSlot doesn't check slot occupancy."
  - **USER TEST:** drag inventory → empty shelf slot to stock it, drag shelf slot → inventory panel to take it back, and check that click, right-click and hover still work.
- [x] **H.6 Editor startup crash.** An AsyncLoading2 NeedLoad assert fired on the `BP_PlayerController_ZombieStore` CDO. **DONE:** the GameMode constructor loaded `BP_HeroCharacter` synchronously, which recursed through asset cycles added in G. The load now happens in `BeginPlay`. See docs/BUGS.md — "Hard class references form asset load cycles." **USER TEST:** the editor opens cleanly, and respawn still works.
- [x] **H.7 Tests.** Added `Test_Pickups_IgnorePawnCollision`, `Test_Audio_WeaponSoundMapsComplete` and `Test_DragDrop_ItemDragOpRoundTrip`.

## I. Real audio + sound settings (2026-09-26, user request)

STATUS NOTE: this is Phase 6-scope audio work (ParentTaskList audio transitions), done during Phase 7 at the user's request.

- [x] **I.1 Real SFX.** All 35 placeholder SFX were replaced with Freesound sounds, trimmed to the onset with faded tails and imported as .wav. Credits are in `docs/AUDIO_CREDITS.md`. The OAuth flow is in the `freesound-audio` skill.
- [x] **I.2 Sound classes.** `SC_Master` sits at the root, with `SC_Music`, `SC_SFX` and `SC_UI` as children, plus `SMix_UserSettings`. `DefaultSoundClassName` is `SC_SFX`.
- [x] **I.3 Settings on Auto Settings.** The Auto Settings plugin (2.1.3) is enabled. It must be installed in the engine on every machine that builds the project.
  - `/Game/Core/Settings/ST_Audio_{Master,Music,SFX,UI}Volume` persist to UserSettings.ini. Defaults are 1.0 / 0.7 / 1.0 / 1.0.
  - `BP_GameInstance_NoBrainers.GetVolume`/`SetVolume` go through the setting registry. `ApplyAudioSettings` re-runs on `OnAppliedValueChanged`.
  - `BP_SaveGame_Settings` was deleted.
- [x] **I.4 Options menu.**
  - `WBP_OptionsMenu` has 4 `WBP_VolumeSliderRow` rows (NativeSliderSettingWidget) and a Back button. Quit to Main Menu needs two clicks and appears in game only.
  - Close keys are read from the `IA_CloseUI`/`IA_ToggleInventory`/`IA_Interact` mappings.
  - Main menu: a Settings button. In game: Escape opens the menu when no interaction window is open. The game doesn't pause (co-op).
  - Quit to Main Menu doesn't save beyond the existing autosaves, and a host quitting drops clients.
- [x] **I.5 Music.**
  - `MUS_Day` / `MUS_Night` come from Freesound. `BP_MusicPlayerComponent` sits on the PlayerController and is local only, with a 3 s crossfade on phase change.
  - Day and Morning use the day track; Dusk and Night use the night track (the Dusk mapping is a design call, not from the GDD). RunOver fades out.
  - The main menu plays the day track.
- [x] **I.6 Tests.** Added `Test_Audio_SoundClassesAssigned`, `Test_Settings_VolumeRoundTrip`, `Test_Settings_VolumeClamp` and `Test_Settings_AudioKeysRegistered`.
- See docs/BUGS.md — "Older interaction widgets hard-code Tab/Escape/E close keys." and "Monolith has no Get Subsystem node (K2Node_GetSubsystem)."

## J. Video/Controls settings (2026-09-26, user request)

STATUS NOTE: an extension of section I, built at the user's request. It isn't part of the A–F plan.

- [x] **J.1 Input config.** Enhanced Input user settings are on, with class `AutoSettingsEnhancedInputUserSettings` (DefaultInput.ini). `AutoSettingsInputConfig` registers `IMC_Default` and `IMC_Inventory`, and Escape cancels a capture (DefaultGame.ini).
- [x] **J.2 Setting types.** `/Game/Core/Settings/ST_Video_*` (resolution, window mode, VSync, frame rate limit, quality preset, resolution scale, FOV), `ST_Controls_LookSensitivity`, `ST_Controls_InvertY`, `ST_Input_KeyMapping`.
- [x] **J.3 Remappable mappings.**
  - `IMC_Default` has 15 remappable keyboard/mouse mappings and 11 remappable gamepad (`_Pad`) mappings. `IMC_Inventory` has QuickDrop and QuickDrop_Pad.
  - The sticks, mouse look and `IA_CloseUI` (Escape / gamepad Menu) can't be rebound (design call). There's no gamepad menu navigation.
- [x] **J.4 Applying settings.**
  - `BP_GameInstance_NoBrainers` has `GetSettingString`/`SetSettingString`, `ApplyVideoSettings(bForce)` (skipped when nothing changed) and `OnLocalSettingsApplied`.
  - The PlayerController (local only) and the main menu apply video settings on start.
  - `BP_HeroCharacter` applies look sensitivity, invert Y and FOV, locally controlled only.
- [x] **J.5 Options menu.**
  - `WBP_OptionsMenu` has Audio / Video / Controls tabs. Row widgets live in `/Game/UI/Settings/`: SliderRow, ComboRow, CheckRow, KeyBindSelector, KeyBindRow.
  - The Controls tab shows 18 action rows with Keyboard/Mouse and Gamepad columns.
  - Capture guard: close keys are ignored during a rebind and for 0.3 s after it. Close keys are rebuilt from the current bindings on every key press.
- [x] **J.6 Tests.** Added `Test_Settings_VideoKeysRegistered`, `Test_Settings_SettingStringRoundTrip`, `Test_Player_LookSettingsApplied`, `Test_Input_GamepadMappingsPresent` and `Test_Input_UserSettingsEnabled`.
- [ ] **J.7 User test in Standalone:** video changes, rebinds that persist across relaunch, gamepad bindings, and co-op isolation.
- See docs/BUGS.md — "Older interaction widgets hard-code Tab/Escape/E close keys." and "Monolith editing gaps found during the Video/Controls settings build."

## F. Game feel

- [x] **F.1 Hitmarker + headshot ding.** (Built in K1.) The crosshair hitmarker flashes on every hit; distinct color
  and sound on headshots; a bigger X on kills.
- [x] **F.2 Directional damage indicator.** (Built in K1.) A red arc points toward the attacker.
- [x] **F.3 Damage vignette + shake.** (Built in K1.) A red edge pulse and a small camera jolt, scaled by damage.
- [ ] **F.4 Placeholder SFX.** Synthesized WAVs from a Python script
  (`PlaceholderAssets/Audio/`): dry-fire click, headshot ding, hitmarker tick, shriek, Bloater
  pop/swell, acid splat, surge groan, Brute charge roar. Each cue has a named slot so real
  Freesound sounds can replace it later.

---

## K. Finish Phase 6 + F + picked proposals (2026-09-26 Q&A)

User-confirmed design calls (don't re-litigate):
- **Post-process:** outlines + light toon shading, **with a toggle and an intensity slider** (Video tab of `WBP_OptionsMenu`).
- **Gore:** green goo only, for hits and deaths. No confetti.
- **Build menu:** keep the grid and polish it (green affordable cost, socket-type tag). No radial/carousel.
- **Store dressing (Phase 6 §1.2):** skipped for now.
- **Downed state:** no new mechanic. The teammate row shows DEAD + a respawn countdown.
- **Music:** intensity crossfades. Day goes "hot" during customer events; Night goes "hot" as the zombie count rises and during surges.
- **Audio source:** Freesound CC0/CC-BY via the `freesound-audio` skill (replaces F.4's synthesized WAVs). Every sound gets a named slot.
- **Proposals picked:** per-type weak spots, and a boss night every 5th night. Everything else stays unscheduled.
- The uncommitted zombie arm-pose rework (`Tools/Characters/blender_zombie_anims.py` + re-exported anims) predates this run; leave it out of K commits.

**Follow-up decisions (2026-09-26 Q&A, round 2):**
- **Boss night end:** the night still ends on its timer, and killing the boss is optional. A kill pays a bonus. A surviving boss carries over like any other zombie.
- **Boss toughness:** scales with player count, at about 8× Brute HP per player. It is 1.6× Brute size and slower.
- **Cel shader:** on by default at medium outline thickness with light toon banding. The toggle and slider live in Options > Video.
- **Night music:** calm, tense, and intense tracks crossfade by how many zombies are alive. Surges and the boss push it to intense.
- **Ammo can at full ammo:** the pickup is refused with an "Ammo full" prompt, and the can stays on the floor.
- **Customer icons:** only special archetypes get one (Rich $, Nurse cross, other event types). Regular shoppers get none.
- **Tracer:** delete the dead Niagara TracerFX branch and keep the faux-projectile tracer. This is done in K7.
- **"+$N" popups:** world text at the sale point (register or shelf), visible to everyone nearby.

**Follow-up decisions (2026-09-26 Q&A, round 3):**
- **Zombie vocals:** mixed. Horror growls and snarls in combat; silly sounds on idle and death (burps, gurgles, an arcade squeak). Pitch varies by type.
- **Customer reactions:** Simlish gibberish blips (happy, annoyed, "hmm") plus an archetype chime. No real words.
- **Day music:** crossfades from the calm track to a busier, more upbeat layer while a customer event is active.
- **Surge/boss warnings:** none. Only the music intensity reacts.
- **Socket highlights:** color by type (Floor green, Wall blue, TurretBase orange, Other purple), but **more subtle than the current ones**. Lower opacity/glow, with a pulse when aimed at.
- **Placement pop:** the defense drops into place from a short height and lands with a thud (plus a dust puff).
- **Cel outlines:** dark ink everywhere. No extra zombie readability (no through-wall outlines, not even for the boss).
- **Boss kill bonus:** scales with boss number (about $150 × boss number) into shared store cash, plus a guaranteed rare loot drop.
- **Respawn countdown:** only the dead player sees it (a big, centered countdown while spectating). Teammates see just "DEAD" in their teammate list.
- **Occupied shelf slot (K7):** swap. The dragged item takes the slot, and the old item goes back to the player's inventory.
- **Interact prompt:** verb only ("[E] Stock", "[E] Open", "[E] Pick up", "[E] Repair"). It shows whatever key Interact is bound to.

**Follow-up decisions (2026-09-26 Q&A, round 4):**
- **Order:** K7 bug fixes first, then K3 → K4 → K5 → K6.
- **Boss size:** a Blender-made mesh scaled to 1.6× Brute at the source, with the Brute anims retargeted. It is imported and used at 1×1×1 (unit-scale rule). No actor or component scale.
- **Audio gaps:** when Freesound has no fit, synthesize a placeholder (a Python-made WAV or a MetaSound) and log it in docs/BUGS.md.
- **Budget:** no token cap for the overnight run. Keep going until done or blocked.

**Follow-up decisions (2026-09-26 Q&A, round 5):**
- **Dismantle refund:** 50% of the defense's price.
- **Repair:** paid, any phase. Hold E on a damaged defense; the cost is proportional to missing health. The auto-restore at Day start stays.
- **Build menu polish:** show the aimed socket's type and grey out entries that don't fit it; a per-entry info tooltip (damage/HP/cost/description); icons/thumbnails instead of text-only tiles.
- **Boss readability:** a top-of-screen boss health bar with a name (e.g. "Manager of the Dead") while it's alive. No tint, no accessory, no new attack.

Work order: K7 first, then K3 → K6 (round 4). Commit locally after each group (no push).

- [x] **K1 Combat feel:** F.1, F.2, F.3 (Phase 6 §2.2 hitmarker), plus per-type weak spots.
  > **STATUS NOTE (2026-09-26):** Built. Everything compiles clean, and the automation covers the weak-spot data and multipliers.
  > - **Damage feedback:** C++ `AGDHeroCharacter::ClientNotifyDamageTaken` → BP `OnLocalDamageTaken` plays `CS_DamageJolt`, then `WBP_HUD.ShowDamageFeedback` (vignette `M_UI_DamageVignette` + directional arc). Owning client only.
  > - **Hitmarkers:** `GA_BP_FireWeapon` aggregates one marker per shot (highest pellet type), and `GA_BP_MeleeAttack` marks each swing. Both call `BP_HeroCharacter.Client_ShowHitMarker`, then `WBP_HUD.ShowHitMarker`: 1 = white, 2 = gold + ding, 3 = red X + kill SFX.
  > - **Needs in-PIE confirmation** (host + client):
  >   - Weak spots: Brute back, Bloater belly from the front, Spitter throat each do 2×.
  >   - Victim-only vignette, jolt, and arc.
  >   - Marker colors and sounds.
  >   - A shotgun kill shows a single X.
- [x] **K2 Combat VFX (Phase 6 §1.3):** tracers, cartoon muzzle flash, green-goo hit and death FX.
  - STATUS NOTE (2026-09-26): built, compiles clean, **needs 2-player PIE confirmation**.
    - New assets: `M_VFX_GooBlob` and `NS_GooSplat` (user params Color, BurstCount, Speed, SpriteSize). `NS_MuzzleFlash` is now a short, bright yellow pop.
    - `BP_EquipmentComponent` has an `ImpactFX` variable and a `SpawnImpactFX` function. Zombie hits give a green splat; other hits give a grey puff; misses give nothing. `Multicast_FireTracer` gained a `HitActor` input and is unreliable. There is a new `Multicast_PlayImpactFX` (unreliable).
    - `GA_BP_FireWeapon` passes the hit actor. `GA_BP_MeleeAttack` plays the goo on zombie hits. `BP_ZombieBase.Multicast_PlayDeath` plays a big goo burst (`DeathGooFX`).
    - New test: `Test_VFX_CombatFXAssigned`. The suite passes 70/70.
    - See docs/BUGS.md — "`Multicast_FireTracer`: the TracerFX Niagara branch never runs." and "`NS_MuzzleFlash` has no velocity module."
- [x] **K3 Audio (F.4, Phase 6 §3.1–3.3):** F.4 cue list, retail/build/trap SFX, customer reactions, zombie vocals/breach thuds, intensity music, the G.7 `PickupSound`.
  - STATUS NOTE (2026-09-26): built, compiles clean, suite passes 73/73, **needs 2-player PIE confirmation**.
    - **Content:**
      - 12 retail/build/defense/breach/pickup SFX.
      - 9 synthesized Simlish blips plus an archetype chime.
      - 8 zombie vocals, and 3 new music tracks (`MUS_DayHot`, `MUS_NightTense`, `MUS_NightIntense`).
      - Everything except the Simlish blips comes from Freesound CC0/CC-BY; credits are in `docs/AUDIO_CREDITS.md`.
      - Attenuation and concurrency settings in `/Game/Audio/Settings/` apply to 69 sounds.
    - **Music:** `BP_MusicPlayerComponent` was rewritten to pick the track by intensity:
      - Day uses the calm track, or the hot track while a customer event is active. Morning is always calm.
      - Night/Dusk goes calm → tense (≥8 zombies) → intense (≥20 zombies, or `bForceIntenseMusic` during a surge).
      - Changes to a more intense track happen at once; changes back down wait out an 8 s hold.
      - This also fixes the bug where music never played (FadeIn was never executed).
    - **Gameplay audio:**
      - Traps and the turret play a hit sound; repair plays a sound; placing a defense plays a socket snap.
      - Breach points thud when hit and crash when broken.
      - The ammo pickup is heard by every player.
      - Checkout plays a beep, a cha-ching and a blip, routed through `BP_Customer`.
      - Customers make "hmm" or annoyed blips at empty shelves.
      - Special archetypes chime once.
      - Zombies make ambient growl/idle vocals with a per-type pitch and a silly death sound (Bloaters pop instead).
      - The surge banner groan was removed.
    - **New tests:** `Test_Audio_K3{DefenseSounds,ZombieVoice,CustomerMusic}Assigned`.
    - **PIE checks (2 players):**
      1. Music plays.
      2. An event day plays the hot track.
      3. At night the music rises with the zombie count, and a surge jumps it to intense.
      4. Trap and turret sounds play, and repair plays at Day start.
      5. Placing a defense snaps. Breach points thud and crash, but not on join or restore.
      6. The client hears the ammo pickup.
      7. Checkout plays its sounds; customers make "hmm" and annoyed blips; special archetypes chime once.
      8. Zombie vocals have per-type pitches, and deaths sound silly.
      9. Sounds fade with distance.
      10. The F.4 cues still play.
    - See docs/BUGS.md — "K3 audio: synthesized placeholders." and "`BP_CheckoutCounter` doesn't replicate."
- [x] **K4 Visuals (Phase 6 §1.1, rest of §1.3):** `M_PostProcess_CelShader` + toggle/slider, build-mode socket highlights + placement pop, "+$N" popups, customer archetype icons.
    - **STATUS NOTE (2026-09-27, K4 done):** compiles clean; 79/79 tests pass; gate 2 ALIGNED; needs a PIE check. "+$N" appears at the register only, since shelf stocking isn't a sale.
    - **PIE checklist:**
      1. The cel shader is on by default. The Options > Video toggle and slider work, persist, and are per-client.
      2. Socket type colors are subtle; the aimed socket pulses; leaving build mode hides the markers.
      3. A placed defense shows on host and client, with the drop, thud and dust; the occupied socket's marker hides.
      4. "+$N" rises above the register on both machines.
      5. Rich, Fighter, Nurse, Scavenger and TrinketCollector show icons; Normal and Cheap show none. If an icon doesn't render, tick Usage > Used with Sprites on `M_CustomerIcon`.
    - K4 also fixed `bReplicates`: `BP_DefenseSocket` and all 6 defense subclass CDOs had it set to false, so placed defenses and socket state never reached clients.
    - See docs/BUGS.md — "K4 defense visuals: replication gaps."
- [ ] **K5 UI gaps (Phase 6 §2.1–2.4):** DEAD label + own-screen respawn countdown, per-actor interact verb, combo/event banner check, build grid polish, repair/dismantle prompt.
    - **STATUS NOTE (2026-09-27, K5 done):** compiles clean; 86/86 tests pass; gate 2 found only a docs gap, now fixed; needs a PIE check. Not ticked until the PIE checks pass.
      - **Death:** dead teammates show a red "DEAD". Only the dead player sees `WBP_HUD.Text_RespawnCountdown` ("RESPAWN IN M:SS" at night, "RESPAWN AT DAWN" otherwise).
      - **Interact prompt:**
        - `BP_Interaction_Base.InteractVerb`, with 7 child verbs (Stock, Open, Pick up ×2, Buy Ammo, Open Kiosk, Close Shop).
        - The prompt key comes from IA_Interact's live mapping (`PC.GetInteractKeyText`).
      - **Paid repair:**
        - Hold E for 1 s on a damaged defense, in any phase; runs through `PC.Server_RepairDefense`.
        - Cost = ceil(missing HP × `RepairCostPerHP`), minimum $1, recomputed on the server. Releasing early costs nothing.
        - The Day auto-restore is unchanged.
      - **Build menu:**
        - Dismantle refunds 50% (all rows `SellRefundPercent 0.5`).
        - Grid entries have icons (`/Game/UI/Icons/Defense/`), tooltips with damage/HP/cost, and a green/red/grey cost.
        - A socket-type label, and entries that don't fit the socket are greyed.
        - An occupied socket shows "HP X/Y   Repair: $N (hold E)" and "Dismantle (+$N)".
      - **Banners:** the surge banner is unhooked per the round-3 decision (music only). The customer event banner has an empty-title guard. There's no combo feature to check.
      - **PIE checklist:**
        1. The prompt reads "[E] Stock" etc., and rebinding IA_Interact changes the key.
        2. On a damaged barricade and a floor trap: "Repair ($N)" plus the hold bar. Releasing early costs nothing, a broke player gets "Not enough cash", and a full hold restores HP on host and client.
        3. At night, the dead player sees the RESPAWN countdown and the teammate sees DEAD.
        4. Build menu: the socket label is right, non-fitting entries are greyed, the cost is green or red, and the tooltip and icons show.
        5. "Dismantle (+$half)" refunds exactly 50%.
        6. A customer event banner shows its text.
      - See docs/BUGS.md — "Phase 6 UI pass: known limitations."
      - See docs/BUGS.md — "Shelf matching-row combo bonus never built."
      - See docs/BUGS.md — "Surge warning banner shows no text (not reproduced statically)."
- [x] **K6 Boss night:** every 5th night, a giant Brute variant + a bigger surge + a kill cash bonus.

> **STATUS NOTE (2026-09-27, K6 done; 92/92 automation tests pass, needs PIE):**
> - **Boss:** `BP_Zombie_Boss` (`/Game/Characters/Zombies/`) on the new `SK_Zombie_Boss` mesh (~1.6× Brute, unit scale, Blender source in `PlaceholderAssets/`), plus a `Boss` row in `DT_ZombieTypes` and `DT_ZombieLoot` (GoldWatch / AntlerTrophy / VintageCoin).
> - **Shared anims:** `SK_Zombie_Skeleton`'s bone retargeting was changed so the boss mesh can reuse the zombie anims. To revert, set all 60 bones back to `Animation`.
> - **Game state:** `BP_GameState_ZombieStore` has `BossNightInterval` 5, `BossKillBonusPerBoss` 150, `BossMaxPlayerScale` 4, and `ActiveBoss`. Its functions are `IsBossNightFor`, `GetBossNumberFor`, `IsBossAlive` (null-guarded), `ComputeBossMaxHealth`, and `ComputeBossKillBonus` (150 × boss number, paid to store cash on the kill).
> - **Spawner:** `BP_ZombieSpawnerManager` scales the surge budget by `BossSurgeBudgetScale` (1.5) on boss nights and spawns one boss on the first surge. The boss is not despawned at night end, so it persists into Morning.
> - **Music and HUD:** music stays intense while the boss is alive. `WBP_HUD` shows the "Manager of the Dead" boss bar top-centre (`UpdateBossBar`).
> - **Tests:** 6 `Test_K6_*` checks in `BP_TestController`, including `Test_K6_BossSurgeScale`.
> - **Change from the task wording:** the cash bonus is paid for killing the boss, not for surviving the night.
> - See docs/BUGS.md — "K6 boss night: known limitations."
- [x] **K7 Bugs:** the G.7 ammo can is consumed at full ammo; `Server_StockItemToSlot` doesn't check occupancy; old widgets hard-code their close keys; delete the dead TracerFX branch in `Multicast_FireTracer`.

> **STATUS NOTE (2026-09-26, K7 done; compiles clean, needs PIE):**
> - **Ammo can:**
>   - `BP_AmmoRefillPickup` only refills pools below `MaxStockpile`.
>   - When every pool is full, the can stays in the world and the player sees "Ammo full" through a new generic HUD status line (`WBP_HUD.ShowStatusMessage`, `BP_HeroCharacter.Client_ShowStatusMessage`).
> - **Shelf swap:**
>   - `Server_StockItemToSlot` now returns an occupied slot's old item to the player's inventory before stocking the new one.
>   - The `WBP_ShelfSlot.OnDrop` guard that only allowed drops on empty slots was removed.
> - **Close keys:**
>   - The new `PC.IsUICloseKey` reads the live bindings for `IA_CloseUI`, `IA_ToggleInventory` and `IA_Interact`.
>   - It is used by the shelf panel, inventory, kiosk catalog and build menu. The build menu also closes on the key bound to `IA_ToggleBuildMode`.
> - **Tracer:** the dead TracerFX branch was removed from `Multicast_FireTracer`.
>
> **PIE checks:**
> - Walking over an ammo can with full ammo leaves it on the ground and shows "Ammo full". Walking over it with ammo missing refills and consumes it.
> - Drag or click a different item onto an occupied shelf slot: the old item returns to your inventory.
> - Rebind Inventory in Options, then open the shelf, inventory, kiosk and build menu: each closes on the new key, Escape and E. The build menu also closes on the build key.
> - Tracers still show when firing.
>
> See docs/BUGS.md — "Server_StockItemToSlot doesn't check slot occupancy." and "Older interaction widgets hard-code Tab/Escape/E close keys."

---

## Proposals (not scheduled; for the user to pick from later)

Anti-kiting / "make it more interesting" ideas that weren't picked for tonight:

- **Wrecker (defense-targeting type).** Cut from tonight by the user. Proposed: it goes for the nearest
  defense first, deals double damage to defenses, and only fights back when no defense is in range.
- **Lunge + grab.** Zombies close gaps with a short lunge; a grab slows or pins the player briefly.
- **Store-raiding zombies.** Some zombies go after shelves or the register and destroy stock or cash
  if ignored, so you can't drag the horde around the parking lot.
- **Per-type weak spots.** The Brute's back, the Bloater's belly (early detonation), the Spitter's throat sac.
- **Night objectives.** Optional challenges (e.g. "protect the register", "kill 3 Screamers before they
  shriek") that pay bonus cash.
- **Zombie-type intel.** A "Tonight: Runners, Spitters" preview at Dusk, plus a codex entry the first
  time you meet each type.
- **Damage numbers / micro hit-stop / Brute knockback camera tumble.** Offered, not picked.
- **Freesound sourcing.** DONE on 2026-09-26 (see section I). OAuth token in `Tools/Audio/.freesound_token.json`
  (gitignored), with CC-BY sounds credited in `docs/AUDIO_CREDITS.md`.
- **More ideas:** carry-over zombies that dig in during Day and ambush when Dusk falls; a noise
  meter (gunfire draws zombies, melee is quiet); a boss night every 5th night (a giant Brute
  variant); an ammo-scarcity pressure valve (a vending machine with surge pricing at night).
