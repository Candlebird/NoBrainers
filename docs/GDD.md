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
- **Night:** Zombies spawn continuously at random intervals from outside the store for the phase's full duration. Players fight to survive using weapons and placed defenses (turrets, spike traps, etc.) inside the store, and collect item drops from kills. Night ends on its timer regardless of how many zombies are still alive — surviving zombies are never forcibly despawned and can carry over into later phases.
- **Morning:** A quiet buffer phase. Neither zombies nor customers spawn; players can regroup and build. Surviving defenses are automatically restored to full health at the start of Day; destroyed defenses must be rebought. (Updated 2026-09-26: players can also pay to repair a damaged defense in any phase, at a cost proportional to missing health, and dismantle one for a 50% refund. Updated 2026-09-29: breach points (doors/walls) can also be paid-repaired the same way, but only in Morning, Day, and Dusk, never at Night. Breach points are real doors: any player can tap Interact to open or close one in any phase, while holding Interact repairs it. An open door can't be damaged and lets zombies walk straight through; a broken door can't be closed until it's repaired, and repairing always leaves it closed.)
- **Day:** Customers come and shop for stocked items, generating money; players place looted items on shelves to stock the store.
- **Dusk:** Customers stop spawning as the store closes; zombies still don't spawn. Another buffer for last-minute building/repair before Night returns.

The cycle repeats Night → Morning → Day → Dusk → Night indefinitely. Because zombies can persist across phases, defeat (all players dead) can now trigger in any phase, not just Night.

**Core Loop:**
Fight Zombies -> Loot item drops -> Stock shelves during the day -> Customers buy items for money -> Buy weapons/ammo/defenses with employee discount -> Repeat

## 3. Progression

**Run Structure:** Roguelite — progress and gear reset each run.

**Meta-Progression:** Persistent unlocks purchased with meta-currency, awarded as a lump sum at the end of each run (victory or defeat). The payout is calculated from that run's performance: total store cash generated, days survived, zombie kills, and shelves fully matched.

**Tiered perk tracks (user decision, 2026-09-30):** Most meta perks are 9-tier tracks bought in order. Each tier costs ×1.5 the previous one.
- Deep Pockets adds loot slots: +1 per tier for tiers 1–6 and +2 per tier for tiers 7–9, so 6 base slots becomes 18.
- The stat tracks each give +5% per tier (+45% at max): max health, max stamina, health regen, stamina regen, armor, fire rate, weapon damage, reload speed, and melee damage.
- All tracks are per-player: they affect only the buyer's own character.
- QuickFeet (move speed) and Scavenger (loot luck) stay single unlocks.
- The 5%-per-tier rule replaces the earlier single-unlock magnitudes. Detail is in `docs/PHASE_9_TASKLIST.md`.

## 4. Enemies

Special zombie types are planned (e.g. fast, tanky, defense-targeting), all deriving from a single shared base zombie class.

## 5. Technical Notes

Built on top of the GASDocumentation project (Unreal's Gameplay Ability System). This may be more than the game strictly needs, but the intent is that GAS's built-in replication support will make multiplayer more feasible for this project.

**Implementation preference:** Favor Blueprint over C++ wherever practical. New gameplay classes, abilities, and content should default to Blueprint subclasses of the existing C++ base classes (e.g. `AGDMinionCharacter`, `AGDCharacterBase`) rather than new C++ classes, unless there's a concrete technical reason C++ is required.
