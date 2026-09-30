# Phase 8: Loot Economy & Inventory

Planned 2026-09-29 from the user's economy complaint: loot drops are fully random, so Night 1
can pay anywhere from ~$300 to ~$1200. The goal is loot income that is predictable per night,
grows with the day number, rewards elites and bosses, and is limited by what players can carry.
All design calls below were confirmed with the user in a 6-round Q&A. Don't re-litigate them.
If one turns out to be infeasible, log it in `docs/BUGS.md` and pick the closest fallback noted
on the task.

**Status:** planned, not started.

## Confirmed design decisions

| Topic | Decision |
|---|---|
| Scaling model | **Tiered tables.** Every item gets a value tier: Junk / Common / Uncommon / Rare / Treasure. A per-night curve shifts the tier weights upward. |
| Income target | Night 1 loot ≈ **$700 ±30%** (about $500–$900). It grows **~+20% per night**: N5 ≈ $1450, N10 ≈ $3600. Loot value only; customer sales and kill cash are separate. |
| What scales | **Both** the value (tier weights) and the count (drops per kill) rise with the night. |
| Bad-luck protection | **Soft pity.** Track the loot value dropped so far this night against the expected curve. While it runs behind, tier weights ramp up until it catches up. |
| Elites | Roll the current night's table **shifted +1 tier**, with **2–3 guaranteed drops**. |
| Bosses | **Loot piñata:** on death, a burst of **8–12 items** arcs out around the corpse. The count scales with boss number, and at least 1 item is Treasure tier. This replaces K6's single "guaranteed rare" boss drop. The boss cash bonus is unchanged. |
| Base price | Reuse `DT_Items.BaseSellPrice`. No new price field. |
| Price display | Tier-colored glow on dropped items; name/price/tier on the pickup prompt, the inventory tooltip and shelf slots. Rare+ drops also get a **light beam**. |
| Inventory cap | **6 slots for loot items only.** Equipped weapons (Primary/Secondary/Melee) and walk-over ammo pickups don't count. |
| Stacking | Removed. Each item takes one slot. Existing stacked saves are **not migrated**; wiping them is fine. |
| Full inventory | Pickup is **blocked**, and an "Inventory full" HUD message shows. |
| Offload | A **stockroom deposit box** inside the store. It **holds 12 items**, and a day-phase upgrade raises that. |
| Floor loot | **Never despawns** (unchanged). The box capacity is what limits banking everything. |
| Bulky items | None. 1 item = 1 slot. |
| Ads | A higher Ad escalation level nudges loot tier weights upward. |
| Meta perks | New perks: **+1 inventory slot** and **Luck** (a small tier-weight boost). |
| Co-op | Shared drops, first come first served (unchanged). |
| Customer demand | Out of scope. No customer logic changes. |
| End-of-night recap | None. |
| Tuning | An offline **Python loot simulator** checks the income band before PIE. |

## Work order

A (data) → B (roll logic) → G.1 (simulator) → G.2 (tuning) → C (inventory) → D (deposit box) → E
(price display) → F (perks) → G.3 (tests). B has to land before the simulator can mirror it, and
tuning happens before any UI, so the numbers are right before anyone playtests. Commit locally
after each group (no push).

## Morning test checklist

_Filled in as groups land. Each line is something that needs manual PIE confirmation._

---

## A. Loot data model

- [ ] **A.1 Loot tiers on items.** Add `E_LootTier` (Junk, Common, Uncommon, Rare, Treasure) and
  a `LootTier` column on the `DT_Items` row struct. Assign every row a tier by `BaseSellPrice`
  band. Starting bands: Junk <$10, Common $10–24, Uncommon $25–44, Rare $45–69, Treasure $70+.
  Weapons sold as items get a tier too.
- [ ] **A.2 Per-night tier curve.** Create `DT_LootNightCurve`. Each row is a night number and
  holds tier weights (5 floats), `BonusMaxDrops` (int) and `ExpectedNightValue` (the
  +20%/night target, used by pity). Author nights 1–10. Nights past the last row reuse the last
  row's weights and keep growing `ExpectedNightValue` by ×1.2 per night.
- [ ] **A.3 Rework `DT_ZombieLoot` rows.** Replace per-item chances with: `DropChance`,
  `GuaranteedDropCount`, `MaxDrops`, `TierOffset` (int; Elite = +1), and a themed item bias list.
  The themed list keeps the Phase 7 E.6 flavor (Spitter → medical, Brute → hardware, and so on)
  by picking themed items more often *within* the rolled tier. The old flat per-item chances go
  away.
- [ ] **A.4 Boss piñata row.** Rework the `Boss` row: `PinataBaseCount` 8, `PinataPerBossNumber`
  +1 (capped at 12), `MinTreasureCount` 1, `TierOffset` +1.

## B. Roll logic (`BP_ZombieBase.Server_RollAndSpawnLoot`)

- [ ] **B.1 Tiered roll.** Rewrite the roll so that:
  1. The drop count = the type row's guaranteed drops + chance-based extras, capped at
     `MaxDrops + BonusMaxDrops(night)`.
  2. For each drop, roll a tier from the night's weights, shifted by (type `TierOffset` + Ads
     nudge + Luck perk + pity boost).
  3. Pick an item within that tier, weighted toward the type's themed list.
  Keep the existing ammo-pickup roll (`AmmoDropChance`, 100% for elites) separate and unchanged.
- [ ] **B.2 Tier shift math.** Implement a shift as moving a fraction of each tier's weight to the
  next tier up. It is a float, so a partial nudge like Ads +0.25 or Luck +0.15 works. Elite +1.0
  is a full step. Clamp so that Treasure never exceeds a cap (starting value 35%), except for the
  boss piñata.
- [ ] **B.3 Soft pity.** `BP_GameState_ZombieStore` keeps `NightLootValueDropped` (the sum of
  dropped items' `BaseSellPrice`) and compares it with
  `ExpectedNightValue × elapsed night fraction`. While the drop value runs more than 15% behind,
  add a pity tier shift that grows with the deficit (max +1.0), and remove it once caught up.
  Reset it at night start. Server-only.
- [ ] **B.4 Ads nudge.** Read the store's current Ad escalation level from
  `BP_StoreEscalationComponent` and map it to a tier shift (starting at +0.1 per Ad level,
  max +0.5).
- [ ] **B.5 Elite roll.** Elites use their type row with `TierOffset` +1 and 2–3 guaranteed
  drops. Replaces the old `Elite` row behavior.
- [ ] **B.6 Boss piñata burst.** On boss death, spawn the piñata count of items. Scatter them
  with a randomized outward/up impulse in a ring around the corpse, and force at least
  `MinTreasureCount` Treasure. Make sure the items land on reachable floor (not inside the
  corpse or level geometry) and the burst replicates to clients. Remove K6's single guaranteed
  rare drop so it doesn't pay twice.

## C. Inventory: no stacking, 6-slot cap

- [ ] **C.1 Remove stacking.** Each inventory entry is one item (quantity is always 1). Update
  the add, remove, drop and stock paths plus the save/load serialization. Old saves with stacks
  can be wiped; no migration.
- [ ] **C.2 Loot slot cap.** Add `MaxLootSlots` (default 6, replicated) to the inventory
  component, with a server-side `HasFreeLootSlot` check. Weapons routed to `Server_EquipItem`
  and `BP_AmmoPickup` bypass the cap.
- [ ] **C.3 Blocked pickup.** `BP_ItemPickup` interaction checks the cap on the server. When
  it's full, the item stays on the floor and the picking player sees an "Inventory full" HUD
  message (through the existing `WBP_HUD` status message).
- [ ] **C.4 Cap edge cases.** These paths must respect the cap:
  - taking an item back from a shelf (click and drag)
  - the K7 occupied-slot swap (the old item returns to inventory — with a full inventory,
    the swap is still 1-for-1, so it's allowed)
  - withdrawing from the deposit box
  - any code path that grants loot directly
  When a path would overflow, block it with the same message. Never drop items silently.
- [ ] **C.5 Inventory UI.** `WBP_Inventory` shows exactly `MaxLootSlots` fixed slots (6, or 7
  with the perk), with filled and empty states and no quantity text.

## D. Stockroom deposit box

- [ ] **D.1 `BP_DepositBox` actor.** An interactable, replicated storage container that holds
  `Capacity` items (default 12). Its UI shows the box contents and the player's inventory side by
  side. It supports deposit (inventory → box) and withdraw (box → inventory, capped at 6), all
  through server RPCs. It must close on Tab, Escape and E, and its input goes through Enhanced
  Input.
- [ ] **D.2 Full-box behavior.** When the box is full, deposits are blocked with a "Stockroom
  full" message. The box empties only through withdrawals, so players must pull items out and
  stock shelves during the day to free space.
- [ ] **D.3 Placement.** Place one box in the stockroom/back area of `Map_Store_Outdoors`, and
  one in `Test_Level_Zero`. **`Map_Store_Outdoors` has user hand edits: spawn the actor into the
  level with an editor action. Never regenerate the map through LevelView.**
- [ ] **D.4 Persistence.** Box contents save and load with the run, alongside shelf stock.
- [ ] **D.5 Capacity upgrade.** A day-phase kiosk purchase (`DT_KioskCatalog` row) raises the
  capacity: 12 → 18 → 24. The price is a starting value, tuned in G.2.

## E. Price and tier display

- [ ] **E.1 Tier glow on drops.** `BP_ItemPickup` gets a replicated `LootTier` and a tier-colored
  glow/outline. Colors: Junk gray, Common white, Uncommon green, Rare blue, Treasure gold. It has
  to read clearly at night on host and client.
- [ ] **E.2 Rare+ light beam.** Rare and Treasure drops shoot a short vertical light beam in their
  tier color (Niagara or an emissive mesh), visible across the store. It stops once the item is
  picked up.
- [ ] **E.3 Pickup prompt.** The world interaction prompt shows the item name, `BaseSellPrice` and
  a tier label/color.
- [ ] **E.4 Inventory tooltip.** Hovering an inventory slot shows the name, price and tier.
- [ ] **E.5 Shelf slot price.** Stocked `WBP_ShelfSlot` entries show the item's price with a tier
  color accent.

## F. Meta perks

- [ ] **F.1 +1 Slot perk.** A new meta-shop perk (Phase 5 perk pipeline) sets `MaxLootSlots` to 7.
  It has to replicate so the UI shows 7 slots.
- [ ] **F.2 Luck perk.** A new meta-shop perk adds a small tier shift (starting at +0.15) to that
  player's kills. Decide during implementation whether "that player" means the killer or the whole
  team, and default to the killer. It feeds into B.2.

## G. Tuning tools and tests

- [x] **G.1 Loot simulator.** Write `Tools/loot_sim.py`. It reads CSV/JSON exports of `DT_Items`,
  `DT_ZombieLoot` and `DT_LootNightCurve`, plus the per-night spawn mix (from the spawner's surge
  budget and type unlock nights). It mirrors B.1–B.6, including pity and elites, then simulates
  1000 runs of 10 nights. It reports mean, p10, p90, min and max loot value per night against the
  target band. The kill fraction and Ad level are CLI flags.
- [x] **G.2 Tune to band.** Iterate the tier weights, drop counts and tier bands until the sim
  puts p10 and p90 inside ±30% of target for nights 1–10 at Ad level 0 and at max. Record the
  final values in a table in this file, as Phase 7 did.
### G.2 tuning results

Sim: 1000 runs, kill fraction 0.85, seed 42, luck 0. Band = p10 >= 70% and p90 <= 130% of target. All nights IN_BAND at Ad 1 and Ad 6. Values are per-night loot value.

| Night | Target | Ad1 mean | Ad1 p10 | Ad1 p90 | Ad6 mean | Ad6 p10 | Ad6 p90 | Junk/Com/Unc/Rare/Tre | Bonus |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 700.0 | 612.7 | 559.0 | 665.1 | 742.3 | 661.9 | 831.0 | 0.718/0.282/0.0/0.0/0.0 | 0 |
| 2 | 840.0 | 746.4 | 676.9 | 819.1 | 896.8 | 791.0 | 1008.0 | 0.562/0.34/0.098/0.0/0.0 | 0 |
| 3 | 1008.0 | 901.4 | 808.0 | 1002.0 | 1095.2 | 942.0 | 1253.0 | 0.47/0.34/0.149/0.041/0.0 | 0 |
| 4 | 1209.6 | 1069.9 | 957.0 | 1182.1 | 1267.9 | 1106.9 | 1450.3 | 0.34/0.327/0.27/0.064/0.0 | 0 |
| 5 | 1451.5 | 1260.4 | 1118.0 | 1405.0 | 1527.6 | 1322.0 | 1764.2 | 0.384/0.379/0.1/0.074/0.063 | 0 |
| 6 | 1741.8 | 1460.5 | 1351.0 | 1581.0 | 1881.1 | 1664.0 | 2119.0 | 0.402/0.401/0.166/0.024/0.006 | 0 |
| 7 | 2090.2 | 1796.4 | 1637.0 | 1958.1 | 2214.1 | 1942.0 | 2493.0 | 0.357/0.261/0.257/0.086/0.039 | 0 |
| 8 | 2508.2 | 2158.4 | 1969.0 | 2366.1 | 2618.3 | 2317.9 | 2939.1 | 0.286/0.252/0.223/0.168/0.071 | 0 |
| 9 | 3009.9 | 2662.5 | 2392.9 | 2946.1 | 3163.7 | 2757.9 | 3583.0 | 0.253/0.218/0.188/0.184/0.157 | 0 |
| 10 | 3611.8 | 3229.0 | 2952.0 | 3550.0 | 3920.7 | 3483.0 | 4386.3 | 0.32/0.208/0.194/0.168/0.111 | 2 |

Final DT_ZombieLoot: MaxDrops 2 on all non-Boss rows. DropChance 0.14 (Default, Runner), 0.16 (Spitter, Screamer, Brute, Bloater). Boss row unchanged. DT_Items LootTier not changed. ExpectedNightValue and BaseSellPrice not changed. Piñata value is reported separately and excluded from the band. Pity does most of the Ad-level smoothing, so the base weights sit below target on purpose.

StockroomExpansion price: 250, untuned.

- [ ] **G.3 Automation tests.** Add `Test_*` checks in `BP_TestController`:
  - the tier roll respects the night weights
  - an elite shift gives a higher mean tier
  - a pity boost engages while behind and releases once caught up
  - the piñata count, and that it includes at least 1 Treasure
  - a pickup is blocked at 6 and allowed at 7 with the perk
  - a shelf take-back is blocked when the inventory is full
  - a deposit is blocked when the box is full
  - box contents round-trip through save/load

## Risks and notes

- **Existing tuning.** Phase 7 E.6's loot chance table is superseded by A.3. The L.3 kill cash
  values are unchanged.
- **Shelf economy.** The shelf slot economy still has an open issue. See docs/BUGS.md — "Shelf
  slot economy unverified after the 16-shelf conversion." Loot income changes will interact with
  it, so revisit it after G.2.
- **Simulator drift.** The sim is a copy of the roll logic. Any later change to B.x must also be
  made in `Tools/loot_sim.py`, or the sim will drift from the game.
