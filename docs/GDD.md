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
Wave-based rounds separated by breaks, driven by a day/night cycle:
- **Night (Wave):** Zombies swarm into the store itself. Players fight to survive using weapons and placed defenses (turrets, spike traps, etc.) inside the store, and collect item drops from kills.
- **Day (Break):** A menu pops up between waves where players place looted items on shelves to stock the store. Customers come and buy the stocked items, generating money.

**Core Loop:**
Fight Zombies -> Loot item drops -> Stock shelves during the day -> Customers buy items for money -> Buy weapons/ammo/defenses with employee discount -> Repeat

## 3. Progression

**Run Structure:** Roguelite — progress and gear reset each run.

**Meta-Progression:** Persistent unlocks purchased with meta-currency, awarded as a lump sum at the end of each run (victory or defeat). The payout is calculated from that run's performance: total store cash generated, days survived, zombie kills, and shelves fully matched.

## 4. Enemies

Special zombie types are planned (e.g. fast, tanky, defense-targeting), all deriving from a single shared base zombie class.

## 5. Technical Notes

Built on top of the GASDocumentation project (Unreal's Gameplay Ability System). This may be more than the game strictly needs, but the intent is that GAS's built-in replication support will make multiplayer more feasible for this project.

**Implementation preference:** Favor Blueprint over C++ wherever practical. New gameplay classes, abilities, and content should default to Blueprint subclasses of the existing C++ base classes (e.g. `AGDMinionCharacter`, `AGDCharacterBase`) rather than new C++ classes, unless there's a concrete technical reason C++ is required.
