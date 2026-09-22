# Phase 5: Roguelite Loop, Escalation & Meta-Progression

## Technical Context

* **Engine Version:** Unreal Engine 5.7.4
* **Perspective:** First-Person
* **Architecture:** Server-authoritative difficulty scaling formulas, persistent save game state handling (`USaveGame`), and client-side meta-progression unlock trees.
* **Goal:** Implement the end-to-end run loop (15–45 min target duration), advertisement-driven escalation mechanics, customer event scheduling, victory/defeat scoring, and persistent meta-currency logic across playthroughs.

---

## Task Breakdown

### 1. Store Advertisement & Threat Escalation Engine

* [ ] **1.1 Store Advertisement System (`UStoreEscalationComponent`)**
* Replicated integer variable: `int32 StoreAdvertisementLevel`.
* Multipliers calculated per level:
* `CustomerVolumeMultiplier` (Increases daytime NPC foot traffic, archetype spawn rates, and cash pool).
* `ZombieHordeSizeMultiplier` (Increases night zombie wave count and spawn frequency at breach points).
* `ZombieStatMultiplier` (Scales zombie movement speed, health pools, and melee damage).

* [ ] **1.2 Dynamic Escalation Curve Calculation**
* Implement mathematical scaling formula evaluated at the end of each `DayPhase`:

$$\text{NightDifficulty} = (\text{CurrentDay} \times \text{BaseRunScalar}) \times (1.0 + (\text{StoreAdvertisementLevel} \times \text{AdScalar}))$$

* Sync escalation metrics to HUD so players can weigh customer profit surges against increased night threat.

---

### 2. Day/Night Schedule & Dynamic Events

* [ ] **2.1 Target Run Time & Day/Night Balancer**
* Configure scalable phase duration timers in `AGameState_ZombieStore`:
* `DayPhaseDuration`: ~60–90 seconds (fast-paced stocking, customer management, and node building).
* `NightPhaseDuration`: ~90–150 seconds per night.

* Target run length pacing: 5 to 12 total days per run (average 15 min, max 45 min).

* [ ] **2.2 Customer Event Scheduler Integration**
* Coordinate `UCustomerEventManager` with run day progression:
* Trigger high-density archetype surges (Nurses, Fighters, Rich, etc.) every 3 to 6 days.
* Broadcast event notifications during the Day Phase transition to give players a chance to stock matched items and set up targeted node defenses.

---

### 3. Run End-Conditions & Scoring

* [x] **3.1 Defeat & Victory Evaluation**
* [x] **Defeat State:** Triggered when all connected players are dead during `NightPhase`. (Already implemented pre-existing in `CheckRunOverCondition` -> `EndRun(false)`; not built as part of this task.)
* [x] **Victory State:** Triggered upon surviving the final target day (e.g., Day 10) or fulfilling a store franchise goal. (Implemented: `BP_GameMode_ZombieStore.EndNightPhase` now compares `BP_GameState_ZombieStore.CurrentDayNumber` against new `TargetDayToWin` (EditDefaultsOnly int, default 10) after a successful horde-clear, calling `EndRun(true)` instead of `StartDayPhase` once the target day is reached.)

* [x] **3.2 Run Summary Calculation**
* Calculate earned meta-currency (e.g., Franchise Points / Employee Coupons) based on:
* Total Store Cash Generated (Sales + Shipping Crate liquidations).
* Number of Days Survived.
* Total Zombie Kills & Shelves Fully Matched.
* Implemented: `BP_GameState_ZombieStore` tracks `TotalCashEarned`/`TotalZombieKills`/`ShelvesFullyMatched` live during play (incremented via `Server_AddCash`, `BP_ZombieSpawnerManager::NotifyZombieDied`, and `BP_ShelfMatchingComponent::EvaluateMatching`'s first-time-fully-matched transition), plus a new `S_RunSummary` struct (`/Game/Data/S_RunSummary`) stored as `LastRunSummary` on GameState. `BP_GameMode_ZombieStore::EndRun` now builds the summary, computes `MetaCurrencyAwarded` via a new tunable `CalculateRunReward` function (designer-editable weights: cash ratio, per-day/per-kill/per-shelf-matched flat amounts), stores it via `Server_SetRunSummary`, and awards the total into `S_SaveMeta` via the existing `AddMetaCurrency` path alongside `RecordRunEnded`'s existing `TotalRunsCompleted`/`BestDayReached` bump. `docs/GDD.md` updated to describe the stat-based end-of-run payout (previously said currency was earned randomly during play). Known limitation: see `docs/BUGS.md` — "Meta-currency awarding is host-local only in listen-server co-op."

---

### 4. Persistent Save System & Meta-Progression Shop

* [ ] **4.1 Save Game Architecture (`USaveGame_ZombieStore`)**
* Create `USaveGame_ZombieStore` class:
* `int32 TotalMetaCurrency`.
* `TArray<FName> UnlockedBlueprintIDs` (Defense blueprints permanently available in node build mode).
* `TArray<FName> UnlockedWeaponIDs` (Weapons permanently added to the in-run Employee Discount catalog).
* `TArray<FName> UnlockedPerkIDs` (Passive starting stat boosts).

* [ ] **4.2 Save/Load Manager (`UMetaProgressionSubsystem`)**
* Create a local Game Instance Subsystem (`UGameInstanceSubsystem`) to handle reading/writing save files locally across runs.
* Safely award and persist meta-currency upon run completion or defeat.

* [ ] **4.3 Meta-Shop UI & Catalog Injection (`UW_MetaShop`)**
* Main Menu / Hub Kiosk UI for spending meta-currency between runs.
* Dynamically inject unlocked blueprints (`ADefenseBase`) into the node build menu and unlocked raycast/melee weapons into the daytime store catalog for future runs.

---

## Acceptance Criteria

1. Increasing Store Advertisements scales both daytime customer traffic/archetypes and night zombie horde intensity.
2. Customer Events correctly fire every 3–6 days, integrating seamlessly into the run pacing.
3. Runs naturally end in defeat (all players dead) or victory (surviving target day count) within the 15–45 minute timeframe.
4. Meta-currency earned at run end persists locally via `USaveGame` and unlocks new defense blueprints, weapons, and perks in the Meta-Shop for subsequent runs.