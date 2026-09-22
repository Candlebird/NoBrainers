# Phase 5: Roguelite Loop, Escalation & Meta-Progression

## Technical Context

* **Engine Version:** Unreal Engine 5.7.4
* **Perspective:** First-Person
* **Architecture:** Server-authoritative difficulty scaling formulas, persistent save game state handling (`USaveGame`), and client-side meta-progression unlock trees.
* **Goal:** Implement the end-to-end run loop (15–45 min target duration), advertisement-driven escalation mechanics, customer event scheduling, victory/defeat scoring, and persistent meta-currency logic across playthroughs.

---

## Task Breakdown

### 1. Store Advertisement & Threat Escalation Engine

* [x] **1.1 Store Advertisement System (`BP_StoreEscalationComponent`)**
* Replicated integer variable: `int32 StoreAdvertisementLevel`.
* Multipliers calculated per level:
* `CustomerVolumeMultiplier` (Increases daytime NPC foot traffic and archetype spawn rates).
* `ZombieHordeSizeMultiplier` (Increases night zombie wave count).
* `ZombieStatMultiplier` (Scales zombie movement speed, health pools, and melee damage).

* [x] **1.2 Dynamic Escalation Curve Calculation**
* Implement mathematical scaling formula evaluated at the end of each `DayPhase`:

$$\text{NightDifficulty} = (\text{CurrentDay} \times \text{BaseRunScalar}) \times (1.0 + (\text{StoreAdvertisementLevel} \times \text{AdScalar}))$$

* Sync escalation metrics to HUD so players can weigh customer profit surges against increased night threat.

STATUS NOTE (1.1/1.2): Built as `/Game/Core/Components/BP_StoreEscalationComponent` (Blueprint ActorComponent, replicated, mounted on `BP_GameState_ZombieStore`), per this project's Blueprint-first convention — the task text's `UStoreEscalationComponent` name was illustrative, not a C++ mandate. `StoreAdvertisementLevel` already existed on GameState (raised via the kiosk's `AdvertLevel` row → `Server_AddAdvertisementLevel`, pre-existing from Phase 2/3) and was reused as the single source of truth; the component derives `NightDifficulty`/`CustomerVolumeMultiplier`/`ZombieHordeSizeMultiplier`/`ZombieStatMultiplier` from it via `RecalculateEscalation`, called from `Server_AddAdvertisementLevel`, `AdvanceDay`, and `BP_GameMode_ZombieStore::StartNightPhase`. `EffectiveAdLevel = Max(StoreAdvertisementLevel - 1, 0)` so a fresh run with zero ad purchases has no escalation bonus. `ZombieHordeSizeMultiplier` and `ZombieStatMultiplier` derive from `NightDifficulty` (clamped, monotonic); `CustomerVolumeMultiplier` derives from ad level alone. Consumers: `BP_ZombieSpawnerManager::CalculateHordeCount` (replaced its old additive ad term with a multiplicative scale by `ZombieHordeSizeMultiplier`, to avoid double-counting ad level), `BP_CustomerSpawner::GetCurrentSpawnInterval`/`GetMaxConcurrent` (same replacement pattern for `CustomerVolumeMultiplier`, event-override precedence preserved), `BP_ZombieBase` (applies a new instant Multiplicative GameplayEffect `GE_ZombieScaling` — SetByCaller tag `Data.ZombieStatScale` on `MaxHealth`/`Health` — strictly *after* the existing Override-based `GE_ZombieAttributes`, plus scales `WalkSpeed`/`JogSpeed`/`SprintSpeed`/`BP_ZombieAttackComponent::MeleeDamageAmount` by the same multiplier), and `WBP_HUD` (new `TextBlock_ThreatLevel`, bound to the component's `OnEscalationChanged` dispatcher, showing `"Ads: {Level} | Threat: {NightDifficulty}"`). Deliberately deferred, not built: "cash pool" scaling for `CustomerVolumeMultiplier` (no customer wallet/spend-budget field exists in the current data model — see `docs/BUGS.md`) and "spawn frequency at breach points" for `ZombieHordeSizeMultiplier` (the spawner uses its own designer-placed `SpawnPoints`, not `BP_BreachPoint` actors; burst-interval scaling was also left un-touched since no concrete formula was specified). All new/edited Blueprints compiled 0 errors/0 warnings and are saved. **Needs manual PIE verification**: escalation values change correctly across ad purchases/day advances/night starts, HUD text is readable and updates live, zombie stat/speed/damage scaling and customer spawn-rate/cap scaling feel correct at multiple ad levels, and a fresh Day 1/Level 1 run shows no unwanted escalation bonus.

---

### 2. Day/Night Schedule & Dynamic Events

* [x] **2.1 Target Run Time & Day/Night Balancer**
* Configure scalable phase duration timers in `AGameState_ZombieStore`:
* `DayPhaseDuration`: ~60–90 seconds (fast-paced stocking, customer management, and node building).
* `NightPhaseDuration`: ~90–150 seconds per night.

* Target run length pacing: 5 to 12 total days per run (average 15 min, max 45 min).

* [x] **2.2 Customer Event Scheduler Integration**
* Coordinate `UCustomerEventManager` with run day progression:
* Trigger high-density archetype surges (Nurses, Fighters, Rich, etc.) every 3 to 6 days.
* Broadcast event notifications during the Day Phase transition to give players a chance to stock matched items and set up targeted node defenses.

STATUS NOTE (2.1): Timers already existed on `BP_GameMode_ZombieStore` (`DayPhaseDuration`/`NightPhaseDuration`, `TimerHandle_Phase`/`TimerHandle_PhaseTick`) from earlier work, coexisting correctly with Phase 4's zombie-kill-count night-end condition (the timer is a failsafe cap, not the primary trigger). Found and fixed a real bug in the process: `TimerHandle_PhaseTick` (the looping 1s ticker driving `PhaseTimeRemaining`) was never cleared before being reset on phase transitions, so it leaked an extra looping timer per transition (2x speed on night 1, 3x on day 2, etc.) — fixed via a new `ClearPhaseTimers` function called first in `StartDayPhase`/`StartNightPhase`/`EndNightPhase`. Also replaced a magic-number `* 5.0` night-failsafe multiplier with a new tunable `NightTimeoutMultiplier` (default 1.5). New defaults: `DayPhaseDuration=75.0`, `NightPhaseDuration=120.0` (both within spec ranges; `NightTimeoutMultiplier=1.5` caps the failsafe at 180s/night). Note: at these defaults with `TargetDayToWin=10`, a full win-run is ~30–42 min depending on horde-clear timing — inside the 15–45 min band, but above the doc's stated "average 15 min" (a 15-min average would need ~5–6 days, not 10). Not resolved either way; flagging since the spec's own numbers are mutually inconsistent and no GDD text picks a side. `PhaseTimeRemaining` is computed/replicated on GameState but has no HUD consumer yet — needed for this to be PIE-verifiable; not yet built. Compiled 0/0, saved. **Needs manual PIE verification** (no HUD readout yet to verify against without one).

STATUS NOTE (2.2): Already fully implemented in a prior session/commit (`ba3cd71`) under a Blueprint-first substitution for `UCustomerEventManager` — `BP_GameMode_ZombieStore` (`EventTable`→`/Game/Data/DT_CustomerEvents`, `MinDaysBetweenEvents=3`/`MaxDaysBetweenEvents=6`, `PickEventRow`/`RollNextEventDay`/`EvaluateDailyEvent`/`AnnounceUpcomingEvent`/`ApplyEventToSpawners`), `DT_CustomerEvents` (6 rows covering Nurse/Fighter/Rich/Scavenger/TrinketCollector/Cheap archetype surges), `BP_CustomerSpawner`'s `EventArchetypeRow`/`EventArchetypeShare`/`EventIntervalMultiplier`/`EventConcurrentBonus` override triad, and `WBP_EventBanner`. This pass closed the one remaining gap: added `OnEventChanged(EventRow, bIsUpcoming)` dispatcher to `BP_GameState_ZombieStore`, broadcast from its `SetActiveEvent`/`SetPendingEvent`/`ClearActiveEvent` functions, so UI (e.g. `WBP_EventBanner`) has something to bind to. Known limitation found in the process: see `docs/BUGS.md` — "`OnEventChanged` dispatcher doesn't reach remote clients (host-only event banner)." Compiled 0/0, saved. **Needs manual PIE verification.**

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

* [x] **4.1 Save Game Architecture (`USaveGame_ZombieStore`)**
* Create `USaveGame_ZombieStore` class:
* `int32 TotalMetaCurrency`.
* `TArray<FName> UnlockedBlueprintIDs` (Defense blueprints permanently available in node build mode).
* `TArray<FName> UnlockedWeaponIDs` (Weapons permanently added to the in-run Employee Discount catalog).
* `TArray<FName> UnlockedPerkIDs` (Passive starting stat boosts).

* [x] **4.2 Save/Load Manager (`UMetaProgressionSubsystem`)**
* Create a local Game Instance Subsystem (`UGameInstanceSubsystem`) to handle reading/writing save files locally across runs.
* Safely award and persist meta-currency upon run completion or defeat.

* [x] **4.3 Meta-Shop UI & Catalog Injection (`UW_MetaShop`)** — unlock injection and shop UI both done (see STATUS NOTE)
* Main Menu / Hub Kiosk UI for spending meta-currency between runs.
* Dynamically inject unlocked blueprints (`ADefenseBase`) into the node build menu and unlocked raycast/melee weapons into the daytime store catalog for future runs.

STATUS NOTE (4.1/4.2): Both were already ~70% built pre-session as Blueprint on `/Game/Core/BP_GameInstance_NoBrainers` (this project's Blueprint-first substitution for `USaveGame_ZombieStore`/`UMetaProgressionSubsystem` — no C++ subsystem needed, same precedent as 1.1/1.2's `BP_StoreEscalationComponent`). The persistent meta-save is `/Game/Data/Save/S_SaveMeta` (wrapped by `/Game/Core/Save/BP_SaveGame_Meta`), with `MetaCurrency:int32` as the existing name for the spec's `TotalMetaCurrency` (not renamed — has live call sites) and pre-existing `UnlockedBlueprintIDs`. This pass added the two missing arrays (`UnlockedWeaponIDs`, `UnlockedPerkIDs`) to the struct, then added 8 new API functions to `BP_GameInstance_NoBrainers` mirroring the existing `UnlockBlueprint`/`IsBlueprintUnlocked` pattern: `GetMetaCurrency`, `TrySpendMetaCurrency`, `UnlockWeapon`/`IsWeaponUnlocked`/`GetUnlockedWeaponIDs`, `UnlockPerk`/`IsPerkUnlocked`/`GetUnlockedPerkIDs`. Caught and fixed a real bug in the process: the three pre-existing functions that mutate the struct (`UnlockBlueprint`, `AddMetaCurrency`, `RecordRunEnded`) had unconnected Break→Make passthrough pins for the two newly-added array fields, so calling any of them silently wiped both arrays back to empty — fixed by wiring the passthrough (see `docs/BUGS.md`, now marked Fixed). This work also extended the Monolith plugin itself with a new `blueprint.add_struct_field` action (no safe non-destructive way existed to add a field to an existing UserDefinedStruct) — see `docs/BUGS.md` for a tooling gotcha found while using it (a bad type-token silently produces the wrong field type instead of erroring). Compiled 0/0, saved. Persistent-save reads happen on whichever machine's GameInstance runs — inherits the same host-local limitation as meta-currency payout (`docs/BUGS.md`). **Needs manual PIE verification.**

STATUS NOTE (4.3, partial): The unlock-injection half is done. Defense blueprints: `BP_GameState_ZombieStore`'s existing `DT_DefenseBlueprints` seeding loop (BeginPlay, `HasAuthority` branch) now unlocks a row if `bUnlockedByDefault` OR the persistent save's `IsBlueprintUnlocked` returns true — no build-menu UI change needed since `WBP_BuildMenu` already reads unlock state live via `GameState.IsBlueprintUnlocked` + `OnUnlocksChanged`. Weapons: added `RequiredUnlockID: FName` to `S_KioskCatalogEntry` (default `None` on all current `DT_KioskCatalog` rows — nothing is gated yet, this just adds the capability), gated server-side in `BP_PlayerController_ZombieStore::CanFulfillKioskEntry` (rejects with "This item requires a meta-shop unlock." if `RequiredUnlockID` is set and not in the player's `IsWeaponUnlocked`), and filtered client-side in `WBP_KioskCatalog::RebuildCatalog` (hides locked rows; fails open on cast failure since the server gate is the real boundary). Perk system data model and application pipeline now built: `S_MetaPerkEntry` (`/Game/Data/S_MetaPerkEntry`) and `DT_MetaPerks` (`/Game/Data/DT_MetaPerks`, 4 seeded rows — `ThickSkin`/`ReinforcedVest`/`QuickFeet`/`Endurance`) hold one dedicated `GE_Perk_*` GameplayEffect per attribute vector (`GE_Perk_MaxHealth`/`GE_Perk_Armor`/`GE_Perk_MoveSpeed`/`GE_Perk_MaxStamina`, under `/Game/Characters/Abilities/Perks/`) rather than a single shared `GE_MetaPerks`, applied via `BP_PerkComponent` (mounted on `BP_PlayerController_ZombieStore`) whose reliable server RPC `SubmitUnlockedPerks` reads `BP_GameInstance_NoBrainers::GetUnlockedPerkIDs()`, is idempotency-guarded (`NOT bPerksApplied` branch before the apply loop), and resolves the owning PlayerState's ASC via `UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent`. Fixed a real race condition in that pipeline: `SubmitUnlockedPerks` runs from the PlayerController's `BeginPlay`, but its own health-top-up step (a `GE_PerkHealthTopUp` SetByCaller-`Data.HealMagnitude` Override-on-`Health` GameplayEffect, applying `GetMaxHealth()` — an unplanned-but-reasonable addition so a mid-run +MaxHealth perk unlock doesn't leave the player under-max) cast `Get Controlled Pawn` to `GDHeroCharacter`, which can silently fail if the pawn isn't possessed yet, dropping the heal. Added an `OnASCReady` backstop on `BP_HeroCharacter` (fired from `PossessedBy`/`OnRep_PlayerState`) that re-fires `SubmitUnlockedPerks` if `bPerksApplied` is still false at pawn-possession time, then unconditionally re-applies the `GE_PerkHealthTopUp` top-up locally against its own ASC (via `GetPlayerState`→`GetAbilitySystemComponent`, mirroring `BP_PerkComponent`'s spec-build sequence) — guaranteeing the heal lands regardless of `SubmitUnlockedPerks` vs. pawn-possession ordering. Added `Debug_UnlockAllPerks` (`BlueprintCallable`, no params) on `BP_GameInstance_NoBrainers` that calls `UnlockPerk` for all 4 seeded PerkIDs, for PIE testing without a shop UI. Known host-local meta-currency/save limitation still applies (see `docs/BUGS.md`). Compiled 0/0, saved on all touched assets (`BP_HeroCharacter`, `BP_GameInstance_NoBrainers`). **Still not built:** the actual Meta-Shop UI (`UW_MetaShop`/hub-kiosk widget) that would let a player spend `MetaCurrency` through the perk catalog — see `docs/BUGS.md` — "Meta-Shop UI (`UW_MetaShop`) not yet built — perk unlock/spend flow has no player-facing widget." **Needs manual PIE verification:** perks apply exactly once even across the `OnASCReady` backstop path (unlock via `Debug_UnlockAllPerks`, verify no duplicate application/heal on repeated possession events), and that a fresh PIE player does not spawn under-max-health when a +MaxHealth perk is already unlocked.

**UPDATE (2026-09-22) — decision made + a regression found and fixed:** User approved **Option B** for the Meta-Shop UI's home — a real Main Menu level (`Map_MainMenu` + `WBP_MainMenu`), not a hub-kiosk actor or a debug-key stopgap. Full scope was recorded in the "Meta-Shop UI (`UW_MetaShop`) not yet built" entry in `docs/BUGS.md`.

**UPDATE (2026-09-22) — Option B built and landed:** `Map_MainMenu`, `BP_GameMode_MainMenu`, `WBP_MainMenu`, `WBP_MetaShop`, and `WBP_MetaShopEntry` are all built, wired, compiled clean, and saved; `DefaultEngine.ini`'s default/editor startup maps repointed to `Map_MainMenu`. Task 4.3 is now checked off. Full detail (asset list, the Level Blueprint tooling gotcha and its GameMode-BeginPlay workaround, and what was deliberately deferred — weapon/defense-blueprint shop tabs, co-op host/join, post-run return-to-menu) is in `docs/BUGS.md`'s "Meta-Shop UI (`UW_MetaShop`) not yet built" entry, now marked RESOLVED. Still needs in-PIE confirmation, same as the two regression fixes above.

The user's own overnight PIE testing surfaced two regressions from this session's perk work, both logged in `docs/BUGS.md`:
- **"Player no longer spawns with a starting pistol"** — root-caused and **fixed**: the `OnASCReady` backstop branch added above had been wired directly onto `Event OnASCReady`'s single exec output pin, which replaced (rather than fanned out from) the pre-existing wire into `Parent: OnASCReady` → `GrantStartingLoadoutIfEmpty`. Fixed with an explicit `Sequence` node so both chains fire. See the BUGS.md entry for the Monolith `connect_pins` gotcha this exposed (it replaces a single exec connection instead of adding a fan-out wire). Compiled/saved; still needs in-PIE confirmation.
- **"No zombies spawn on entering night phase"** — root-caused and **fixed**: `BP_StoreEscalationComponent`'s 4 state variables had a self-recursive Blueprint Getter/Setter accessor binding. Fixed by writing a new Monolith action (`blueprint.set_variable_accessor`) to clear the binding, since no existing Blueprint/Monolith/Python tooling could do it — see the BUGS.md entry for full detail. Compiled 0/0, saved; still needs in-PIE confirmation (user unable to test at time of fix — proceeding with the Main Menu build per user instruction).

---

## Acceptance Criteria

1. Increasing Store Advertisements scales both daytime customer traffic/archetypes and night zombie horde intensity.
2. Customer Events correctly fire every 3–6 days, integrating seamlessly into the run pacing.
3. Runs naturally end in defeat (all players dead) or victory (surviving target day count) within the 15–45 minute timeframe.
4. Meta-currency earned at run end persists locally via `USaveGame` and unlocks new defense blueprints, weapons, and perks in the Meta-Shop for subsequent runs.