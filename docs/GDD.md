# No Brainers — Game Design Document

## 1. Game Overview: Pitch

**Game Title:** No Brainers

**Genre(s):** Survival Horde Shooter, Store-Sim, Third-Person Shooter

**Target Audience:** 13+. Players who enjoy over-the-shoulder, fun-oriented shooters, and people looking for a fun game to play with friends.

**Player Count:** Solo or co-op, up to 4 players.

**Platform:** PC only. Online co-op only — no split-screen.

**Tone:** Comedic and goofy.

**High Concept (The "Elevator Pitch"):**
No Brainers is a co-op, over-the-shoulder shooter about surviving the night inside a store overrun by zombies — using turrets, spike traps, and other passive defenses alongside your guns to hold out — then spending the day looting zombie drops to restock shelves and turn a profit.

**Why This Game? (The "Why We're Making It"):**
No Brainers is our first dip into the multiplayer genre. It's a test of how well we can handle networking while building a game that's focused on that "let's play a game and hang out" feeling you get from other multiplayer games.

**Unique Selling Points (USPs):**
- Point 1: Survive-the-night combat inside the store itself — turrets, spike traps, and other placeable defenses supplement your guns as zombies push in, rather than defending a separate perimeter.
- Point 2: Customer/store-sim day loop — looted zombie drops become shelf stock that customers actually shop for, blending shooter combat with a lighthearted retail-sim layer.

## 2. Core Gameplay: Experience

**Session Structure:**
A four-phase, time-based day/night cycle (updated 2026-09-24 — user-confirmed; previously wave-based, ending Night on a zombie-kill count rather than a timer):
- **Night:** Zombies spawn continuously at random intervals from outside the store for the phase's full duration. Players fight to survive using weapons and placed defenses (turrets, spike traps, etc.) inside the store, and collect item drops from kills. Night ends on its timer (except Night 9, the final night; see below) regardless of how many zombies are still alive — surviving zombies are never forcibly despawned and can carry over into later phases.
- **Morning:** A quiet buffer phase. Neither zombies nor customers spawn; players can regroup and build. Surviving defenses are automatically restored to full health at the start of Day; destroyed defenses must be rebought. (Updated 2026-09-26: players can also pay to repair a damaged defense in any phase, at a cost proportional to missing health, and dismantle one for a 50% refund. Updated 2026-09-29: breach points (doors/walls) can also be paid-repaired the same way, but only in Morning, Day, and Dusk, never at Night. Breach points are real doors: any player can tap Interact to open or close one in any phase, while holding Interact repairs it. An open door can't be damaged and lets zombies walk straight through; a broken door can't be closed until it's repaired, and repairing always leaves it closed. Updated 2026-09-30: traps can be placed in Morning, Day and Dusk. Dismantling refunds 50% of everything spent on the trap, placement plus upgrades. Upgrading and selling are closed at Night, while repair works in any phase. Players manage a placed trap by pressing E on it.)
- **Day:** Customers come and shop for stocked items, generating money; players place looted items on shelves to stock the store. (Updated 2026-09-30: the weapon kiosk sells a shared daily stock of 4 tiered weapons, rolled each Morning. It's open in Morning, Day and Dusk and closed at Night, and paid rerolls double in cost. The Defense kiosk likewise sells a shared daily stock of 3 trap blueprints, and is also closed at Night.)
- **Dusk:** Customers stop spawning as the store closes; zombies still don't spawn. Another buffer for last-minute building/repair before Night returns.

The cycle repeats Night → Morning → Day → Dusk → Night indefinitely. Because zombies can persist across phases, defeat (all players dead) can now trigger in any phase, not just Night.

(Updated 2026-09-30, user decision, Phase 12: **the run is won on Night 9.** The game's theme is groups of 3. Night 9 has no timer, and it ends when the team kills the 3-phase Final Boss, which wins the run and adds +300 meta-currency to the payout. The host then chooses **Cash Out** or **Continue into Endless**. Endless nights ramp zombie health and damage by +12% per night (compounding), with more and faster spawns and more elites. Every endless night has a boss: the Swamp boss, or the Final Boss on every 3rd night. The host gets the same choice again each endless dawn. The endless payout is the normal payout × (1 + 0.10 per endless night survived) plus the victory bonus, and a wipe in Endless keeps everything earned. Detail is in `docs/PHASE_12_TASKLIST.md`.)

(Updated 2026-09-30, user-requested: a new run starts at Dusk of Day 1 to cut the wait before the first Night. Day 1 has no Day phase, so there are no customers and no daily-event roll that day. Both kiosk shops still roll their stock at that first Dusk. A resumed session keeps its saved phase, and a new run's first session save is at Morning of Day 2.)

**Core Loop:**
Fight Zombies -> Loot item drops -> Stock shelves during the day -> Customers buy items for money -> Buy tiered weapons from the daily weapon shop and trap blueprints from the daily blueprint shop, place and upgrade traps, buy ammo with employee discount -> Repeat

**Onboarding (user decision, 2026-10-01, Phase 13):** New players learn in play, not in a separate tutorial level. A small HUD card shows one goal at a time, only when it can be done in the current phase, and hides at Night. Goals cover stocking, sales, shelf combos and fully matched shelves; placing, managing and buying traps; doors; and the weapon, Defense and ammo kiosks, rerolls and tiers. Each goal is learned once per profile and is driven only by that player's own actions. Every phase change shows a banner with the phase name, plus a one-line explanation the first two times a player sees that phase. A "How to Play" codex is available from the main menu and from Options (Tutorial > How to Play), and the meta shop shows two hints on the first visit after a run. Options has a Tutorial hints toggle and a Reset tutorial progress button. Tutorial text is plain and instructional, an exception to the game's comedic tone. Every player's first Spike Trap placement in each run is free; selling it refunds 50% of the normal price. Detail is in `docs/PHASE_13_TASKLIST.md`.

## 3. Progression

**Run Structure:** Roguelite — progress and gear reset each run.

**Meta-Progression:** Persistent unlocks purchased with meta-currency, awarded as a lump sum at the end of each run (victory or defeat). The payout is calculated from that run's performance: total store cash generated, days survived, zombie kills, and shelves fully matched.

**Tiered perk tracks (user decision, 2026-09-30):** Most meta perks are 9-tier tracks bought in order. Each tier costs ×1.5 the previous one.
- The stat tracks each give +5% per tier (+45% at max): max health, max stamina, health regen, stamina regen, armor, fire rate, weapon damage, reload speed, and melee damage.
- All tracks are per-player: they affect only the buyer's own character.
- QuickFeet (move speed) and Scavenger (loot luck) stay single unlocks.
- The 5%-per-tier rule replaces the earlier single-unlock magnitudes. Detail is in `docs/PHASE_9_TASKLIST.md`.

**Carry model (user decision, 2026-10-01):** There is no inventory. Each player carries one item in their hands and can't shoot while carrying. E picks up, places on the shelf slot being looked at, or sets the item down at their feet. Night loot stays on the floor and must be carried to the storage zone around the deposit box; Dusk deletes every loose item outside it. The Deep Pockets perk is removed with no refund. Shelf slots go 2/4/6/8/12. Throwing (hold fire) and the economy retune follow. Full decisions: `docs/CARRY_OVERHAUL_DECISIONS.md`.

**Weapon tiers and daily weapon shop (user decision, 2026-09-30):** Weapons use the same 5 rarity tiers as loot drops.
- **Tier multipliers:** Junk ×0.9, Common ×1.0, Uncommon ×1.1, Rare ×1.2, Treasure ×1.3.
  - Guns: the multiplier applies to damage, fire rate, magazine size and reload speed. Magazine size rounds to the nearest whole number, gains at least +1 per tier above Common, and loses at least 1 at Junk.
  - Melee: the multiplier applies to damage and swing speed.
  - Tier multipliers stack (multiply) with the meta perk multipliers.
- **Showing the tier:** the held weapon shows a HUD tier label and a tier-colored glow that teammates can see.
- **Sources:**
  - The starting loadout is Junk (updated 2026-09-30: everything starts at Junk).
  - Zombie weapon drops roll a tier on the loot curve. They are rare and come mostly from elites; the boss always drops one.
  - A replaced weapon drops on the floor, keeping its tier.
- **Keeping weapons:** death keeps your weapons. A new run resets them, consistent with "gear resets each run". A mid-run save stores equipment tiers and the shop state.
- **Weapon shop:**
  - Every Morning it rolls 4 weapons: 1 primary, 2 secondary and 1 melee, with no duplicates. If a slot type has nothing available, the slot is filled from another type.
  - Tiers come from a dedicated weapon-shop curve for the current day (`DT_WeaponShopTierCurve`): day 1 is 80% Junk / 20% Common, rising toward Uncommon and Rare by day 10. Zombie weapon drops keep the night loot curve.
  - Stock is shared and first come first served, paid from shared StoreCash.
  - Price = DT_Weapons.Price × 0.75 for Junk, and × 1.5 per tier above Common. The employee discount no longer applies to weapons; it still applies to trap blueprints and marketing. For blueprints it's baked into `BlueprintPrice` (updated 2026-09-30).
  - Paid reroll: $50, doubling each use and resetting each Morning.
- **Weapon unlocks:** weapons are one-time meta-shop unlocks. The shop draws from the union of all connected players' unlocks. The defaults are Pistol, Rifle, Magnum and Bat: the starter plus the cheapest weapon of each type.
- Detail is in `docs/PHASE_10_TASKLIST.md`.

**Trap unlocks, blueprint shop and trap upgrades (user decision, 2026-09-30):** Traps follow the weapon model.
- **Unlocks:** Spike and Swinging traps are available from the start. The others are one-time meta-shop unlocks: Barricade 120, SlowStrip 150, GasTrap 200, Turret 300.
- **Blueprint shop:**
  - In a run, the team has to buy a trap's blueprint once before anyone can place it. Placing each trap still costs its normal price.
  - The Defense kiosk sells a shared daily stock of 3 blueprints, rolled each Morning. It draws from the union of all connected players' meta unlocks, minus blueprints the team already owns, with no duplicates.
  - Stock is first come first served, paid from shared StoreCash at `BlueprintPrice`.
  - Paid reroll: $50, doubling each use and resetting each Morning.
  - It's closed at Night.
- **Trap tiers:**
  - Each placed trap starts at Junk and can be upgraded to Common, Uncommon, Rare and Treasure (×1.0 / ×1.25 / ×1.5 / ×1.75 / ×2.0). (Updated 2026-09-30: everything starts at Junk.)
  - An upgrade costs `Cost × 1.5^(new tier − Common)`, so Junk→Common costs the trap's price. A Spike (60) upgrades for 60, 90, 135, then 203.
  - SlowStrip slow is diminishing, capped at 90%: `SlowPercent = 90 − 40 × (2 − mult)²` (Junk 50, Common 67.5, Uncommon 80, Rare 87.5, Treasure 90).
  - Only Common and above glow; Junk has no glow.
  - The multiplier scales damage and effect, health, attack rate, and range or area, wherever each applies.
  - The tier shows as a colored glow, and selling or losing the trap loses it.
- **Selling:** refunds 50% of everything spent on the trap.
- **Managing a trap:** outside Build Mode, press E on a placed trap to open its panel: stats, Upgrade, Repair and Sell.
- **Build Mode controls:** left click places and right click exits. Weapons can't fire or aim in Build Mode.
- **Save:** the mid-run save stores owned blueprints, the shop state, and every placed trap's tier, total spent and health. A new run resets them.
- Detail is in `docs/PHASE_11_TASKLIST.md`.

## 4. Enemies

Special zombie types are planned (e.g. fast, tanky, defense-targeting), all deriving from a single shared base zombie class.

**Combat feel (user decision, 2026-09-30, Phase 12):**
- **Zombie attacks:** melee zombie and boss attacks deal damage at the apex of the swing, and only if the target is still in range, so players can dodge by stepping back. Spitter globs and Bloater explosions are unchanged.
- **Stagger:** player melee hits stagger zombies for 0.35 × the weapon's swing interval, clamped to 0.25–0.8 s. Brutes take half, and bosses are immune.
- **Hit feedback:** player hits show a green goo splat and a brief white flash.
- **Bosses:** the Swamp boss comes on Nights 3 and 6. The Night 9 Final Boss is an upgraded Swamp boss with 3 health phases: normal; then it summons 3 special adds and moves faster; then it enrages and summons more often.

## 5. Technical Notes

Built on top of the GASDocumentation project (Unreal's Gameplay Ability System). This may be more than the game strictly needs, but the intent is that GAS's built-in replication support will make multiplayer more feasible for this project.

**Implementation preference:** Favor Blueprint over C++ wherever practical. New gameplay classes, abilities, and content should default to Blueprint subclasses of the existing C++ base classes (e.g. `AGDMinionCharacter`, `AGDCharacterBase`) rather than new C++ classes, unless there's a concrete technical reason C++ is required.
