# Phase 11 — Trap Unlocks, the Daily Blueprint Shop, Trap Upgrades and the Trap Panel

**Goal.** Make traps work like Phase 10 weapons:
- Traps are unlocked through meta progression.
- In a run, the team buys a trap's blueprint from a shared daily shop before it can be placed.
- Each placed trap can be upgraded through the loot tiers.
- Pressing E on a placed trap opens one panel for upgrade, repair and sell.

**Status (2026-09-30).** Built unattended while the user can't test. **Needs PIE testing.** See the "PIE test checklist" at the bottom.
- **Automation suite:** 186 PASS / 1 FAIL. The only failure is the known-flaky `Test_CustomerSpawnerMaxConcurrent`. All 18 Phase 11 tests pass. Two fixes landed during testing: the 6 trap CDOs now default to Common (T24b), and the blueprint shop's `IsShopOpen` and `GetCurrentRerollCost` got their missing Entry→Return exec links (T10b).

## Design decisions (confirmed with the user)

- **Unlocks:**
  - All 6 defenses are trap blueprints: SpikeTrap, SwingingTrap, Turret, Barricade, SlowStrip and GasTrap.
  - SpikeTrap and SwingingTrap are owned from the start of every run.
  - The others are one-time meta-shop unlock rows in `DT_MetaPerks` (`UnlockBlueprintID`): Barricade 120, SlowStrip 150, GasTrap 200, Turret 300.
- **Ownership:** owning a blueprint is team-wide for the run and is paid from shared StoreCash (`GameState.UnlockedBlueprintIDs`). Placing a trap still costs `DT_DefenseBlueprints.Cost`.
- **Blueprint shop:**
  - **Stock:** it rolls every Morning: 3 cards drawn from blueprints that some connected player has meta-unlocked and the team doesn't own yet, with no duplicates. With fewer candidates it shows fewer cards, and an empty card reads "All blueprints owned".
  - **Buying:** stock is shared and first come first served, and a sold card shows SOLD.
  - **Price:** `S_DefenseBlueprintEntry.BlueprintPrice`, carried over from the old kiosk prices: Spike 60, Swinging 110, Turret 200, Barricade 50, SlowStrip 50, Gas 120.
  - **Employee discount:** it's baked into those prices. The old kiosk never applied a runtime discount multiplier; its catalog prices were already the discounted ones, so there's no extra multiplier.
  - **Reroll:** $50, doubling each use, resetting each Morning. It's disabled when there's nothing new to roll.
  - **Hours:** open in Morning, Day and Dusk; closed at Night and RunOver.
  - **Purchase order:** validate, then afford, then grant, then deduct. A failed deduct rolls back the grant through `Server_RevokeBlueprint`.
- **Terminal:** the `BP_DiscountKiosk` instance with `KioskCategory = "Defense"` opens the blueprint shop. Blueprint rows are removed from `DT_KioskCatalog`.
- **Trap tiers:**
  - Each placed trap has an `E_LootTier`, starting at Common. Upgrades go Common → Uncommon → Rare → Treasure at ×1.0 / ×1.25 / ×1.5 / ×1.75.
  - An upgrade costs `Cost × 1.5^(new tier − Common)`. For Spike that's 90, 135 and 203.
  - The multiplier scales damage and effect, max health (Health rises by the same amount), attack rate, and range: pulse radius, turret detection sphere, and trap trigger volumes.
  - Stats that don't apply are skipped, so the Barricade gets health only.
  - The slow is `1 − 0.5 × mult` through the new `GE_TrapSlow`.
  - The tier replicates. Uncommon and above get a tier-colored `M_LootTierOverlay` glow.
- **Selling:** refunds 50% of the total spent (placement plus upgrades). Selling or losing the trap loses the upgrade.
- **Trap panel:**
  - Outside Build Mode, pressing E while aiming at a placed trap opens `WBP_TrapPanel`.
  - It shows the name, tier, a health bar, and current → next stats, with Upgrade, Repair and Sell buttons and their costs.
  - Upgrade and Sell are disabled at Night; Repair works in any phase.
  - It closes on Tab, Esc and E, and by itself if the trap is destroyed.
  - It replaces the Build Menu's RepairSellBox and hold-E repair on defenses.
- **Build Mode input:**
  - LMB (`IA_PrimaryAction`) places, and E no longer places. RMB (`IA_SecondaryAction`) exits Build Mode.
  - Weapon fire and aim are blocked for all of Build Mode by `State.BuildMode`.
  - Placement is allowed in Morning, Day and Dusk.
- **Save:** the mid-run save stores owned blueprints, the shop stock, the reroll count, the last rolled day, and each placed trap's socket, blueprint, tier, total spent and health. A new run resets all of it.

## Tasks

### Step A — Data
- [x] **T1.** `S_DefenseBlueprintEntry.BlueprintPrice`, with values for every `DT_DefenseBlueprints` row.
- [x] **T2.** `S_MetaPerkEntry.UnlockBlueprintID`, plus 4 trap-unlock rows in `DT_MetaPerks`.
- [x] **T3.** Blueprint rows removed from `DT_KioskCatalog`.
- [x] **T4.** New structs `S_BlueprintShopSlot` and `S_SavedDefense`, plus the new `S_SaveSession` fields.
- [x] **T5.** Gameplay tag `Data.SlowMultiplier` and `GE_TrapSlow`.

### Step B — Defenses
- [x] **T6.** `BP_DefenseBase`: replicated `Tier` and `TotalSpent`, base-stat capture, and the tier and cost helpers.
- [x] **T7.** `BP_DefenseBase`: `ApplyTierStats`, `ApplyTierGlow`, `ApplyUpgrade` and `RestoreTierState`.
- [x] **T8.** Turret uses the base attack fields (`bUsesOwnAttack`). SlowStrip uses `GE_TrapSlow`. Spike, SlowStrip and Swinging scale their trigger volumes with tier.

### Step C — Shop and save
- [x] **T10.** `/Game/Core/Shop/BP_BlueprintShopComponent`: filter, roll, purchase, reroll, open state and restore.
- [x] **T11.** GameState: `Server_RevokeBlueprint`; defaults seeded from `bUnlockedByDefault`.
- [x] **T12.** GameState hosts the component. The save snapshot and restore include unlocks, the shop and placed defenses.
- [x] **T13.** GameMode: the Morning, Day and Dusk starts roll the blueprint shop.

### Step D — Build Mode and input
- [x] **T9.** `BP_BuildModeComponent` keeps `State.BuildMode` for all of Build Mode.
- [x] **T18.** `WBP_BuildMenu`: RepairSellBox removed.
- [x] **T20.** PlayerController: trap panel open and close, E routing, RMB exit, and a phase-gate check.

### Step E — UI and RPCs
- [x] **T14.** PlayerController: blueprint shop buy and reroll RPCs, `Server_UpgradeDefense`, the ownership check on Place, and a total-spent sell refund. A main-session fix lets selling happen in every phase except Night and RunOver (before, it only worked in Day).
- [x] **T15.** `/Game/UI/WBP_BlueprintShopCard`.
- [x] **T16.** `/Game/UI/WBP_BlueprintShop`.
- [x] **T17.** `/Game/UI/WBP_TrapPanel`.
- [x] **T19.** PlayerController: `OpenBlueprintShopUI` and `CloseBlueprintShopUI`.
- [x] **T21.** `BP_DiscountKiosk` routes `KioskCategory = "Defense"` to the blueprint shop.

### Step F — Tests
- [x] **T22.** Shop roll and open state:
  - `Test_BlueprintShop_RollFromCandidates`
  - `Test_BlueprintShop_FilterExcludesOwnedAndDuplicates`
  - `Test_BlueprintShop_FewerCandidatesFewerSlots`
  - `Test_BlueprintShop_ClosedAtNight`
- [x] **T23.** Purchase and reroll:
  - `Test_BlueprintShop_PurchaseGrantsAndDeducts`
  - `Test_BlueprintShop_CantAffordNoGrantNoDeduct`
  - `Test_BlueprintShop_SecondBuyerFails`
  - `Test_BlueprintShop_RerollCostDoubles`
  - `Test_BlueprintShop_RerollDisabledWhenEmpty`
- [x] **T24.** Trap upgrade, sell and the panel's phase rules:
  - `Test_TrapUpgrade_CostFormula`
  - `Test_TrapUpgrade_StatScaling`
  - `Test_TrapUpgrade_BarricadeHealthOnly`
  - `Test_TrapSell_RefundsHalfTotalSpent`
  - `Test_TrapPanel_UpgradeSellBlockedAtNight_RepairAllowed`
- [x] **T25.** Placement, save and data:
  - `Test_BuildMode_ServerPlaceAllowedInMorning`
  - `Test_BuildMode_ServerPlaceRequiresOwnedBlueprint`
  - `Test_Save_BlueprintShopAndDefensesRoundTrip`
  - `Test_Data_MetaTrapUnlockRows`

**Regression set that must stay green:** `Test_WeaponShop_*`, `Test_Defense_*`, `Test_K5_*`, `Test_BuildMode*`, `Test_BuildModePlacementRequest`, `Test_InteractionUI_CloseActive`, `Test_Save_*`, `Test_Equipment_*`, `Test_Loot_*`, `Test_Data_*`, `Test_Meta*`. The known-flaky `Test_CustomerSpawnerMaxConcurrent` is excluded.

## Status notes

- See docs/BUGS.md — "Trap upgrades and blueprint purchases after the last save are lost on quit (Phase 11)."
- See docs/BUGS.md — "Blueprint shop reroll availability doesn't refresh when a player with new meta unlocks joins mid-day (Phase 11)."
- See docs/BUGS.md — "Saved traps are matched to sockets by actor name; renamed sockets drop old saved traps (Phase 11)."
- See docs/BUGS.md — "Hold-E repair on placed traps is replaced by the trap panel's instant Repair button (Phase 11)."
- See docs/BUGS.md — "Treasure SlowStrip slows zombies to 12.5% speed; watch balance (Phase 11)."
- See docs/BUGS.md — "Trap panel and blueprint shop give no failure feedback from the server (Phase 11)."
- See docs/BUGS.md — "Turret only targets the first overlapped zombie (pre-existing)."
- See docs/BUGS.md — "Dead Phase 11 leftovers: WBP_BuildMenu.TrackedSocket and the PC's defense hold-repair path (Phase 11)."

## PIE test checklist

1. **Meta shop:** the 4 Trap unlock rows appear with costs 120/150/200/300, and buying one works. The meta shop is one scrolling list, so scroll down to the Trap rows.
2. **Blueprint shop:**
   - The Defense kiosk opens the 3-card shop. The Weapons kiosk still opens the weapon shop. (`KioskCategory = "Defense"` on the map instance couldn't be confirmed without opening the map. It's most likely `Kiosk_Upgrades`.)
   - Only meta-unlocked blueprints you don't own appear. Empty cards read "All blueprints owned".
   - Buying deducts StoreCash, unlocks the entry in the Build Menu, and shows SOLD to both players.
   - The reroll costs $50 and then $100, or reads "Nothing new to roll".
   - At Night it shows Closed. It closes on Tab, Esc and E.
3. **Build Mode:**
   - LMB places, and E doesn't. RMB exits Build Mode (with or without a selection) and does not aim.
   - Weapons don't fire in Build Mode, even with no selection.
   - You can place in Morning, Day and Dusk. Unowned entries are locked.
4. **Trap panel:**
   - Outside Build Mode, E on a placed trap opens it, showing the name, the tier color, the health bar and the current → next stats. Check that the panel background isn't transparent.
   - Upgrading raises the glow color for both players, raises MaxHealth and Health by the same amount, and charges the right amount (Spike: 90 / 135 / 203).
   - Repair works at Night. Upgrade and Sell are disabled at Night.
   - Sell refunds half of everything spent on that trap.
   - It closes on Tab, Esc and E, and closes by itself if the trap is destroyed.
5. **Turret and SlowStrip:** a Rare turret fires faster, farther and harder. A higher-tier SlowStrip slows more.
6. **Barricade:** an upgrade only raises its HP.
7. **Save:** save mid-run, then load.
   - Owned blueprints, the shop stock (including SOLD) and the reroll cost come back.
   - Placed traps reappear on their sockets with the same tier and health.
   - A new run goes back to Spike and Swinging only, with no traps placed.
