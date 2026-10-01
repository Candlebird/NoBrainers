# Phase 12 — Combat Feel, the Night 9 Victory, Endless Mode and the Bug Audit

**Goal.** Give a run a real ending and make melee combat feel right:
- Nights come in threes, and the run is won by killing an upgraded 3-phase Swamp boss on Night 9.
- After winning, the team can cash out or keep going into a ramping Endless mode.
- Zombie attacks land on the swing's apex, and the player can dodge them.
- Melee hits stagger zombies, show a goo splat and flash, and use one clean swing animation per weapon class.
- Two new melee weapons: the Sledgehammer and the Katana.
- BUGS.md gets audited, so it matches the game again.

**Status (2026-09-30).** Overnight run complete. Groups A–F built (need PIE). Vision gate 2 found DRIFT on docs only; it's fixed. C3 tint: see docs/BUGS.md — "Final Boss material is not darkened or red-tinted (Phase 12)."

**Group order is the cut order.** Groups land A → E. If the night runs short, cut from the end (E first).

## Design decisions (confirmed with the user)

### Run length and victory
- **Night 9 is the final night.** The game's theme is groups of 3. The boss still spawns every 3rd night (3 and 6) as the regular Swamp boss.
- **Night 9 has no timer.** Regular spawns run as normal, and the **Final Boss** spawns during the night. The night ends only when the Final Boss dies, which wins the run. A wipe on Night 9 is a normal defeat.
- **Victory bonus:** a flat **+300 meta-currency** on top of the normal run payout.

### Final Boss (`BP_Zombie_FinalBoss`, a child of `BP_Zombie_Boss`)
- **Look:** the same `SK_Zombie_SwampBoss` mesh, unscaled (assets stay 1×1×1). It gets a new material instance (darker, with glowing veins), a constant aura VFX, and a VFX burst at each phase change.
- **Phases by health:**
  1. **100–66%:** fights like the Swamp boss.
  2. **66–33%:** summons adds and moves faster.
  3. **Below 33%:** enraged. It attacks faster and summons more often.
- **Adds:** each summon spawns **3 mixed special zombies** from the Phase 7 special types (the architect picks the classes and the summon interval for each phase).
- **Attack timing:** uses the apex notify like every other melee zombie (see Combat feel).
- **Stagger:** immune. Hit flash only.

### Endless mode
- **Entry:** the victory screen offers **Continue into Endless** or **Cash Out**. The **host decides**, and clients see the choice and its result.
- **Each endless dawn** (the Morning after every endless night) shows the same Continue / Cash Out choice before the day phase.
- **Payout:** the normal run payout × (1 + 0.10 × endless nights survived), plus the +300 victory bonus. **Dying in Endless keeps everything earned**, so a wipe there pays out like a cash-out.
- **Bosses:** every endless night is a boss night. The regular Swamp boss comes on most nights, and the 3-phase Final Boss on every 3rd night (12, 15, 18…). Both scale with the ramp below.
- **Ramp, per endless night past 9:**
  - Zombie health and damage: **+12%**, compounding. Night 15 is about 1.7× health.
  - Zombie count: **+10%**.
  - Spawn interval: **−5%**, with a floor of 50% of the base.
  - Elite chance: **+3 points**, capped at 40%.
  - Loot curves don't ramp. Nights past the last `DT_LootNightCurve` row (10) use that last row.
- **Save:** the mid-run save stores the endless flag and the night count. Resuming an endless run continues the ramp from where it was.

### Run summary (victory, cash-out and defeat)
- **Per-player stats:** kills, damage dealt, deaths, and items looted (the architect can add a cheap extra stat or two that the systems already track).
- **Team stats:** nights survived, total store cash earned, total kills, and shelves fully matched.
- **Meta-currency:** an animated count-up of the payout, with the lines shown (base payout, endless multiplier, victory bonus).

### Death and spectating
- **Better death screen:** a styled "You died" overlay with the respawn timer, plus the name of the teammate being spectated.
- **Switching targets:** the existing **Fire** action goes to the next living teammate and **Aim** goes to the previous one, while spectating. No new keys; all input goes through Enhanced Input (`IMC_Default`).

### Combat feel
- **Zombie attack apex:** all melee zombies and both bosses deal damage at an **anim notify at the swing's apex**, not when they come into range. At the notify, the target is hit **only if it is still in attack range**, so stepping back dodges the attack. Spitter globs and Bloater explosions are unchanged.
- **Stagger:** a player melee hit freezes the zombie: no movement, the AI paused, and any attack wind-up cancelled.
  - Duration = **0.35 × the weapon's effective swing interval**, after tier and perk speed scaling, clamped to **0.25–0.8 s**. That's about 0.3 s for the Machete and 0.77 s for the Fire Axe.
  - Brutes take **half** the duration. Both bosses are **immune**.
  - Stagger is server-authoritative and replicated.
- **Hit feedback:** every damaging player hit on a zombie (melee or gun) shows a **green goo splat** (Niagara) and a brief **white flash** on the zombie's mesh, multicast. Nothing else: no hitstop or camera kick.
- **Player swing animations:** authored in Blender, one per weapon class. Each is **one solid swing with good follow-through**, and the hit lands **once**, at a notify. This fixes the current janky double hit. The play rate scales with the effective swing speed, so the animation has to look good sped up.
  - **One-handed swing:** Machete, Pipe Wrench, Bat, Katana.
  - **Two-handed heavy swing:** Fire Axe, Canoe Paddle, Sledgehammer.

### New melee weapons (meta-shop unlocks)
- **Sledgehammer:** two-handed and heavy. Swing interval about 2.6 s, damage about 90, longest stagger (it hits the 0.8 s cap). Unlock price **250**.
- **Katana:** one-handed, fast and long-reaching. Swing interval about 0.8 s, damage about 45, `MeleeRange` about 260. Unlock price **300**.
- Both meshes are made in Blender at the correct size, then imported at 1×1×1. Both join the daily weapon shop's melee pool once unlocked. The architect sets the `DT_Weapons.Price` values by comparison with the Fire Axe and Machete.

### Balance
- **Magnum:** `BaseDamage` 35 → **65**. It was below the Pistol's 38 despite its slower fire.
- **Night 1 loot leak:** `DT_LootNightCurve` Night 1 is already 71.8% Junk / 28.2% Common, but the user saw a legendary-tier sellable drop on Night 1. Some modifier path (elite tier shift, soft pity, the Ad nudge, or a sellable-item path that skips the curve) lets drops exceed the night's tiers. **Find it and clamp all zombie drops to the highest tier with a non-zero weight on that night's row.** The curve itself stays as it is.
  - The boss loot piñata and the boss's guaranteed weapon drop are exempt. That's my call, not a user decision: the boss reward is meant to be special.

### Bug audit
- A scout checks every open `docs/BUGS.md` entry against the current assets and classifies it as **Fixed**, **Stale** (it no longer applies) or **Still open**. The main session updates BUGS.md.
- Small confirmed bugs (a single asset with a clear fix) are fixed tonight, one builder call per asset, at most about 4.
- Bigger ones stay as clear, current entries for a later phase.

## Tasks

The architect turns these into dispatch-ready packets. The numbers are for tracking, not packet boundaries.

### Group A — Bug audit and balance
- [x] **A1.** Scout: audit every open BUGS.md entry and classify it (Fixed / Stale / Still open), with evidence for each.
- [x] **A2.** Main session: update BUGS.md from the audit.
- [x] **A3.** Fix the small confirmed bugs from A1, at most about 4, one builder call per asset. Done: muzzle flash, meta shop icons, Junk pickup glow. The Long Rifle shelf fix was deferred (multi-asset); see docs/BUGS.md — "Long rifle overlaps neighbouring slots on T4 shelves."
- [x] **A4.** Night loot leak: trace the path and clamp zombie drops to the night's highest allowed tier (boss exempt). Nights past row 10 use row 10.
- [x] **A5.** `DT_Weapons.Magnum.BaseDamage` = 65.

### Group B — Combat feel
- [x] **B1.** Zombie apex notify: add an attack-apex notify to every melee zombie attack montage and both bosses. Damage applies at the notify with a range re-check. Remove the damage that applies immediately when in range.
- [x] **B2.** Zombie stagger: a replicated stagger on `BP_ZombieBase` (stops movement, pauses the AI, cancels the wind-up). It's driven by the player melee hit, uses 0.35 × the effective interval clamped to 0.25–0.8 s, is halved for Brutes, and bosses are immune.
- [x] **B3.** Hit feedback: a green goo splat Niagara system plus a white flash on the zombie mesh, multicast on every damaging player hit.
- [x] **B4.** Blender: the one-handed swing and the two-handed heavy swing for the player skeleton. One solid swing with follow-through, with a hit notify at contact.
- [x] **B5.** `DT_Weapons`: a melee-class (or attack-montage) column, filled for each melee row by the 1H/2H grouping above.
- [x] **B6.** `GA_BP_MeleeAttack`: pick the montage by class, set the play rate from the effective swing interval, and apply damage once at the hit notify (fixes the double hit). The montage start section check is in docs/BUGS.md — "Melee swing montages: length and start section unverified."

### Group C — Night 9 victory
- [x] **C1.** Run stats tracking: per-player and team counters, replicated, and kept in the mid-run save.
- [x] **C2.** `BP_Zombie_FinalBoss`: the 3 phases, the summons, faster movement in phase 2, and enrage in phase 3.
- [x] **C3.** Final boss look: the material instance, the aura Niagara, and the phase-change burst.
- [x] **C4.** GameMode/GameState: Night 9 is the final night with no timer and a Final Boss spawn. The boss's death sets the Victory state, which replaces the normal Night → Morning flow.
- [x] **C5.** Payout: the +300 victory bonus and the endless multiplier hook.
- [x] **C6.** `WBP_RunSummary`: per-player and team stats, the meta-currency count-up, and host-only Continue / Cash Out buttons (clients see a waiting state). It is used for victory, cash-out and defeat.

### Group D — Endless mode and death screen
- [x] **D1.** Endless state: the flag and night count, the ramp multipliers applied at spawn, and the boss on every night (the Final Boss on nights divisible by 3). Saved and restored.
- [x] **D2.** The endless dawn choice: at each endless Morning, the host gets Continue / Cash Out before the day phase. Cash Out → payout → summary → Main Menu.
- [x] **D3.** Death screen: the styled overlay with the respawn timer and the spectated name. Fire switches to the next teammate and Aim to the previous one while spectating.

### Group E — New melee weapons
- [x] **E1.** Blender: the Sledgehammer and Katana meshes, sized correctly at the source, imported to `/Game/Weapons/Meshes/`.
- [x] **E2.** `DT_Weapons` rows for both (stats above, plus the melee class), the `DT_MetaPerks` unlock rows (250 / 300), and entry into the shop's melee pool.

### Group F — Tests and wrap-up
- [x] **F1.** Tests: apex dodge (out of range at the notify means no damage), stagger duration and the Brute/boss rules, the loot clamp on Night 1, the Magnum damage, the final-night flag and the victory trigger, the endless ramp multiplier, and the payout math. 8 tests added: 7 pass, and Test_ZombieApexDodge fails because of a test-harness problem. See docs/BUGS.md — "Test_ZombieApexDodge fails because the hero is dead (Phase 12, test harness)."
- [x] **F2.** Vision gate 2, the GDD check, commits through `ue-git-manager` (local only), and the run log.

## PIE test checklist (for the user, after the run)
1. Melee a regular zombie with the Machete and then the Fire Axe. Check that each stagger is visibly short and long, that there's one clean swing with no double hit, and that the goo splat and flash appear.
2. Let a zombie start its swing, then step back. It should miss. Stand still, and it should hit at the apex, not on contact.
3. Night 1 drops are Junk and Common only. Elites can't go above Common.
4. The Magnum kills a regular zombie in about 2 shots.
5. Use the dev console or a save to jump to Night 9. The Final Boss spawns with its tint and aura. At 66% it bursts, summons 3 specials and moves faster. At 33% it enrages. There's no night timer.
6. Kill the Final Boss. The run summary shows the stats, counts up the payout including +300, and the host sees Continue / Cash Out (also check a client in a 2-player session).
7. Continue: Night 10 has a regular Swamp boss and tougher zombies. At the endless dawn, the choice appears again. Cash Out: the payout matches the summary.
8. Die in multiplayer. The death screen shows the spectated name, and Fire/Aim cycle teammates.
9. Unlock the Sledgehammer and Katana in the meta shop. They appear in the daily weapon shop, use the right swing, and look right in the hand.
