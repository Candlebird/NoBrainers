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

- [ ] **B.1 Type data model.** A `DT_ZombieTypes` row per type: HP, speed(s), damage, attack range,
  loot table row, cash/loot tier, unlock night, base spawn weight, anim set. `BP_ZombieBase` reads its
  row on spawn. Each type is a thin Blueprint child (`BP_Zombie_<Type>`).
- [ ] **B.2 Shambler.** The current zombie, re-expressed as the base row.
- [ ] **B.3 Runner.** It alternates a jog with 2–3 s sprint bursts and finishes with a leaping lunge
  attack. About 50% of Shambler HP. The player can't outrun it.
- [ ] **B.4 Brute.** Tanky and slow. It periodically winds up and charges in a straight line: heavy
  damage plus knockback to players and barricades it hits. If the charge misses, it's briefly
  stunned. Sidestepping is the counter.
- [ ] **B.5 Spitter.** Keeps a 10–18 m range and lobs a visible, dodgeable arcing glob. The glob
  leaves a 5 s acid puddle (damage over time plus slow). It backs off when players close in. The
  acid hurts zombies too.
- [ ] **B.6 Screamer.** Low HP; flees from players. Its shriek (on cooldown) gives zombies within
  ~12 m +40% move speed for 6 s and summons 2–4 extra Shamblers/Runners from the nearest spawn zone
  (per-Screamer cap).
- [ ] **B.7 Bloater.** Slow. Explodes on death, or after a visible 1.5 s swell-fuse when it reaches a
  player or defense. The blast damages players, defenses **and zombies**.
- [ ] **B.8 Staggered unlock.** Night 1: Shamblers only. Runners join on night 2, Spitters on 4,
  Screamers on 5, Brutes and Bloaters on 6+. Spawn weights shift toward special types with night
  number and Store Advertisement level.
- [ ] **B.9 Headshots.** 1.5× damage on head hits, all types. No per-type weak spots.
- [ ] **B.10 Elites: one per surge.** Each horde surge (D.2) includes exactly one elite: a random type
  plus one modifier (Armored +100% HP / Swift +35% speed / Regenerating out of combat), a colored
  glow, and a guaranteed better loot roll.
- [ ] **B.11 Per-type loot/cash.** Special types and elites pay more than Shamblers (`DT_ZombieLoot`).

## C. Zombie animations (Blender)

All clips are keyframed by headless Blender scripts on the `SK_Zombie` rig
(`PlaceholderAssets/Blender/SK_Zombie.blend`). `.blend`/FBX sources go in `PlaceholderAssets/`,
and imports go under `Content/Characters/Zombie/Animations/<Type>/`. **Tone: mixed by type.**
Shambler and Bloater are goofy and floppy. Runner and Screamer are twitchy and unsettling. Brute is heavy.
Spitter sits in between.

- [ ] **C.1 Per-type set.** **Blender side DONE:** 75 clips in `PlaceholderAssets/FBX/Zombie/` (`Tools/Characters/blender_zombie_anims.py`; fixed a pose-scale accumulation "spike" bug). Attack hit / Lob release ≈ 55% of clip length. UE import via `Tools/Characters/ue_import_zombie_anims.py` pending. Each type gets: idle, walk, run (or type-specific gait), claw-out-of-ground
  spawn, 3 attack variations (randomly picked), an additive hit-react, and 3 death variations
  (randomly picked). Plus type-specific clips: Runner sprint + lunge, Brute charge wind-up/charge/stun,
  Spitter lob, Screamer shriek + flee run, Bloater swell.
- [ ] **C.2 Spawn.** Every type claws up from the ground, each in its own style. The zombie is invulnerable
  and inactive until the climb ends (~1.5–3 s).
- [ ] **C.3 Anim Blueprint.** Locomotion blendspace per type, montage slots for attacks/spawn/specials,
  and an additive hit-react layer (the flinch plays on every hit). Heavy hits (shotgun, sawed-off,
  magnum, melee) also briefly interrupt the zombie's attack or movement.
- [ ] **C.4 Death → physics.** Death anim blended into physics through `PhysicalAnimationComponent`, with
  physics weight ramping up and an impulse along the killing hit's direction. **Fallback if the
  physics asset fights it:** play the death anim for ~0.5 s, then full ragdoll with the impulse. The
  body despawns later; oldest ragdolls are cleaned up once there are more than 8.

## D. Horde AI & spawning

- [ ] **D.1 Ground spawn zones.** New spawn-zone actors outside the store in `Map_Store_Outdoors`,
  **added only; nothing the user hand-placed is moved or regenerated** (list every addition here).
  Mirror them in `Test_Level_Zero`.
- [ ] **D.2 Horde surges.** About 3 surges per Night (3× spawn rate for 20–30 s) with calmer lulls
  between them, then a big finale wave in the last 60 s. A HUD banner plus groan cue gives ~3 s warning.
- [ ] **D.3 Flanking / surround.** Zombies are spread across multiple breach points and approach
  targets from assigned angles (slot-around-target), instead of forming a single conga line.
- [ ] **D.4 Alive cap.** 30 alive solo, +5 per extra player, 45 max. Surge spawns queue instead of
  overflowing the cap.

## E. Economy & balance pass

Target feel: **tight early, snowball late.** The first nights are scrappy (1–2 defenses, careful ammo);
by day ~5–7 a well-run store affords top-tier gear and upgrades. Edit the data directly and record
every change in the before/after table below with reasoning, so any line can be reverted.

- [ ] **E.1 Prices of goods** (`DT_Items` sell prices, customer tolerance interplay).
- [ ] **E.2 Weapons, ammo, defense blueprint prices** (`DT_Weapons`, `DT_AmmoCatalog`, `DT_KioskCatalog`,
  `DT_DefenseBlueprints`).
- [ ] **E.3 Trap usefulness.** The user found every trap (spike, slow strip, gas, swinging) near-pointless.
  Buff damage/uptime/area so each trap has a clear job against the new types.
- [ ] **E.4 Shelf tier upgrade curve** (`DT_ShelfTiers`) against the revenue each tier adds.
- [ ] **E.5 Free auto-repair at Day start.** Every surviving defense restores to full HP for free when
  Day begins. Destroyed defenses stay destroyed (rebuy). Remove manual paid repair.
- [ ] **E.6 Per-type loot/cash values** (with B.11).

Player movement is **out of scope** (user: leave the player alone).

### Before/after table

| Asset | Row / field | Before | After | Why |
|---|---|---|---|---|

## F. Game feel

- [ ] **F.1 Hitmarker + headshot ding.** The crosshair hitmarker flashes on every hit; distinct color
  and sound on headshots; a bigger X on kills.
- [ ] **F.2 Directional damage indicator.** A red arc points toward the attacker.
- [ ] **F.3 Damage vignette + shake.** A red edge pulse and a small camera jolt, scaled by damage.
- [ ] **F.4 Placeholder SFX.** Synthesized WAVs from a Python script
  (`PlaceholderAssets/Audio/`): dry-fire click, headshot ding, hitmarker tick, shriek, Bloater
  pop/swell, acid splat, surge groan, Brute charge roar. Each cue has a named slot so real
  Freesound sounds can replace it later.

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
- **Freesound sourcing.** Swap the synthesized SFX for CC0 Freesound sounds once there's an API key
  (`.freesound_key`, gitignored), with CC-BY sounds credited in `PlaceholderAssets/Audio/CREDITS.md`.
- **More ideas:** carry-over zombies that dig in during Day and ambush when Dusk falls; a noise
  meter (gunfire draws zombies, melee is quiet); a boss night every 5th night (a giant Brute
  variant); an ammo-scarcity pressure valve (a vending machine with surge pricing at night).
