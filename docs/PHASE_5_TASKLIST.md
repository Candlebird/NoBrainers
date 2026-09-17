\# Phase 5: Roguelite Loop, Escalation \& Meta-Progression



\## Technical Context



\* \*\*Engine Version:\*\* Unreal Engine 5.7.4

\* \*\*Perspective:\*\* First-Person

\* \*\*Architecture:\*\* Server-authoritative difficulty scaling formulas, persistent save game state handling (`USaveGame`), and client-side meta-progression unlock trees.

\* \*\*Goal:\*\* Implement the end-to-end run loop (15–45 min target duration), escalation mechanics driven by store advertisements, victory/defeat scoring, and persistent meta-currency logic across playthroughs.



\---



\## Task Breakdown



\### 1. Store Advertisement \& Threat Escalation Engine



\* \[ ] \*\*1.1 Store Advertisement System (`UStoreEscalationComponent`)\*\*

\* Replicated integer variable: `int32 StoreAdvertisementLevel`.

\* Multipliers calculated per level:

\* `CustomerVolumeMultiplier` (Increases daytime NPC foot traffic \& customer cash pool).

\* `ZombieHordeSizeMultiplier` (Increases night zombie count and spawn frequency).

\* `ZombieStatMultiplier` (Scales zombie movement speed, health pools, and armor).









\* \[ ] \*\*1.2 Dynamic Escalation Curve Calculation\*\*

\* Implement mathematical scaling formula evaluated at the end of each `DayPhase`:







$$\\text{NightDifficulty} = (\\text{CurrentDay} \\times \\text{BaseRunScalar}) \\times (1.0 + (\\text{StoreAdvertisementLevel} \\times \\text{AdScalar}))$$



\* Sync escalation metrics to HUD so players can assess the risk/reward before advancing to the night phase.



\---



\### 2. Run Timer, Balance \& End-Conditions



\* \[ ] \*\*2.1 Target Run Time Balancer\*\*

\* Configure scalable day/night duration timers in `AGameState\_ZombieStore`:

\* `DayPhaseDuration`: \~60–90 seconds (forces fast-paced stocking and defense prep).

\* `NightPhaseDuration`: \~90–150 seconds per night.





\* Target run length pacing: 5 to 12 total days per run (average 15 min, max 45 min).





\* \[ ] \*\*2.2 Run Defeat \& Victory Evaluation\*\*

\* \*\*Defeat State:\*\* Triggered when all connected players are dead during `NightPhase`.

\* \*\*Victory State:\*\* Triggered upon surviving the final target day (e.g., Day 10) or fulfilling a store franchise goal.

\* \*\*Run Summary Calculation:\*\* Calculate earned meta-currency based on:

\* Total Store Cash Generated.

\* Number of Days Survived.

\* Total Zombie Kills \& Shelves Fully Matched.











\---



\### 3. Persistent Save System \& Meta-Currency



\* \[ ] \*\*3.1 Save Game Architecture (`USaveGame\_ZombieStore`)\*\*

\* Create `USaveGame\_ZombieStore` class:

\* `int32 TotalMetaCurrency` (e.g., Franchise Points / Employee Coupons).

\* `TArray UnlockedBlueprintIDs` (Weapons, Traps, Shelves unlocked permanently).

\* `TArray UnlockedPerkIDs` (Passive starting stat boosts).









\* \[ ] \*\*3.2 Save/Load Manager (`UMetaProgressionSubsystem`)\*\*

\* Create a local Game Instance Subsystem (`UGameInstanceSubsystem`) to handle reading/writing save files locally across runs.

\* Safely award and persist meta-currency upon run completion or run defeat.







\---



\### 4. Meta-Progression Shop \& Unlocks



\* \[ ] \*\*4.1 Meta-Shop UI (`UW\_MetaShop`)\*\*

\* Main Menu / Hub Kiosk UI for spending meta-currency between runs.

\* Unlockable categories:

\* \*\*Weapons:\*\* Unlocks higher tier guns/melee tools for the in-run Employee Discount Store pool.

\* \*\*Defenses:\*\* Unlocks specialized traps (e.g., Flame turrets, Freeze pads, Electric fences).

\* \*\*Store Upgrades:\*\* Unlocks starting perks (e.g., Start with +20% extra store cash, faster shelf stocking speed).









\* \[ ] \*\*4.2 Loot Table Injection System\*\*

\* Modify `DT\_Items`, `DT\_ZombieLoot`, and the Employee Discount Shop catalog dynamically at runtime based on active `UnlockedBlueprintIDs`.







\---



\## Acceptance Criteria



1\. Increasing the Store Advertisement level visibly increases both daytime customer traffic/profit and night zombie horde size/health.

2\. Runs naturally end in defeat (all players die) or victory (surviving the final day target) within the 15–45 minute timeframe.

3\. Meta-currency is accurately calculated at run end and saved locally via `USaveGame`.

4\. Players can access the Meta-Shop in the main menu/hub, purchase unlocks, and see those unlocked items appear in subsequent gameplay runs.

