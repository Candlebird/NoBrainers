# Phase 10 — Weapon Tiers and the Daily Weapon Shop

**Goal.** Give weapons the same 5 rarity tiers as loot drops (Junk, Common, Uncommon, Rare, Treasure), with the tier raising the weapon's stats. Replace the flat weapon kiosk with a shared daily shop that rolls 4 tiered weapons every Morning, with tiers that improve as the days go on.

**Status (2026-09-30).** Built unattended while the user can't test. **Needs PIE testing.** See the "PIE test checklist" at the bottom.
- **Automation suite:** all 18 new tests pass.
- One regression was found: `Test_Equipment_ReloadReplenishesMagazine` was failing because later synchronous tests re-equipped the hero while its reload wait was running. The fix moves it to the end of the sync chain.
- The only remaining failure is the known-flaky `Test_CustomerSpawnerMaxConcurrent`.

## Design decisions (confirmed with the user)

- **Tier multipliers:** Junk ×0.9, Common ×1.0, Uncommon ×1.1, Rare ×1.2, Treasure ×1.3.
  - Guns: the multiplier applies to damage, fire rate, magazine size and reload speed.
  - Melee: the multiplier applies to damage and swing speed.
  - The tier multiplier multiplies with the Phase 9 meta perk multipliers.
- **Magazine size** is `round(Base × mult)`, with at least +1 per tier above Common and at least −1 at Junk. It never drops below 1, and melee (magazine ≤ 0) is unchanged.
- **Showing the tier:** the HUD shows a tier label for the held weapon. The held weapon also has a tier-colored overlay glow, driven by the replicated equipment slots, so teammates see it too.
- **Sources:**
  - The starting loadout is Junk (Junk-start follow-up, 2026-09-30).
  - Zombie weapon drops are rare: 1% for normal zombies and 20% for elites. The boss drops one 100% of the time. The tier rolls on the night loot curve for the current day.
  - Equipping over an occupied slot drops the old weapon on the floor, keeping its tier.
- **Ownership:** weapons are kept on death and respawn. A new run resets them. The mid-run save stores equipment tiers and the shop state.
- **Weapon shop:**
  - It rolls every Morning: 1 primary, 2 secondary and 1 melee, with no duplicate weapons. If a type has no candidates, the slot is filled from another type.
  - The pool is the union of all connected players' meta weapon unlocks. The defaults are Pistol, Rifle, Magnum and Bat.
  - Each slot's tier rolls on `DT_WeaponShopTierCurve` for `CurrentDayNumber` (via `BFL_LootMath.GetWeaponShopCurveRow`; Junk-start follow-up, 2026-09-30).
  - Price = `DT_Weapons.Price × 0.75` at Junk, and `× 1.5^(tier − Common)` at Common and above. The employee discount doesn't apply to weapons.
  - Purchases are paid from the shared StoreCash. Stock is shared and first come first served, and a sold slot shows SOLD.
  - It's open in Morning, Day and Dusk, and closed at Night.
  - Paid reroll: $50, doubling each use, resetting each Morning. A reroll rerolls all 4 slots.
- **Terminal:** the existing `BP_DiscountKiosk` instance with `KioskCategory = "Weapons"` now opens the weapon shop. Weapon rows are removed from `DT_KioskCatalog`.
- **UI:** 4 cards with stat deltas against the weapon you hold in that slot type, a SOLD state, and a reroll button. It closes on Tab, Esc and E through Enhanced Input.

## Tasks

### Step A — Data
- [x] **T1.** `S_EquipmentSlot.Tier` (E_LootTier).
- [x] **T2.** New `S_WeaponShopSlot` struct: WeaponID, Tier, Price, bSold.
- [x] **T3.** `S_WeaponData.Price`, with prices filled in for every `DT_Weapons` row.
- [x] **T4.** `S_MetaPerkEntry.UnlockWeaponID`, plus 9 weapon-unlock rows in `DT_MetaPerks`.
- [x] **T5.** Weapon rows removed from `DT_KioskCatalog`.
- [x] **T6.** `S_SavePlayerInventory.Equipment`.
- [x] **T7.** `S_SaveSession` shop fields: slots, reroll count, last rolled day.

### Step B — Tier math and equipment
- [x] **T8.** `/Game/Core/Loot/BFL_WeaponTiers`: stat multiplier, tiered magazine size, price, and the active-weapon tier multiplier (safe fallbacks).
- [x] **T9.** `BP_EquipmentComponent`: tier kept through every slot rebuild, `PendingEquipTier`, and `EquipWeaponWithTier(ItemID, Tier)`.
- [x] **T10.** `BP_ItemPickup`: `bTierLocked` and `ApplyWeaponTier`. Weapons default to Common, and OnInteract equips with the pickup's tier.
- [x] **T11.** `BP_EquipmentComponent`: tiered `GetSlotMagazineSize`, reload time ÷ (perk × tier), and a rewritten `RestoreEquipment`.
- [x] **T12.** `GA_BP_FireWeapon`: damage and fire rate × tier multiplier (stacked with perks).
- [x] **T13.** `GA_BP_MeleeAttack`: damage and swing speed × tier multiplier.
- [x] **T14.** `WBP_HUD`: `Text_WeaponTier` label for the held weapon.
- [x] **T15.** `BP_EquipmentComponent`: `DropSlotAsPickup` (the replaced weapon drops with its tier) and `ApplyHeldWeaponTierGlow` (overlay MID of `M_LootTierOverlay`).

### Step C — Daily shop
- [x] **T16.** `/Game/Core/Shop/BP_WeaponShopComponent`: replicated `ShopSlots` and `RerollCount`, pool helpers, `IsShopOpen`, `GetCurrentRerollCost`, `RestoreShopState`.
- [x] **T17.** `RollShopSlots(Pool, Day)` and `Server_RollDailyShop(bForce)`: a 1/2/1 mix, no duplicates, fill from another type, curve tiers.
- [x] **T18.** `TryPurchaseSlot(SlotIndex, Buyer)` and `TryReroll()`.
- [x] **T19.** `BP_GameState_ZombieStore` hosts the component, and its save snapshot and restore include the shop.
- [x] **T20.** `BP_GameMode_ZombieStore`: the Morning, Day and Dusk starts call `Server_RollDailyShop(false)`, which only rolls once per day. `RespawnDeadPlayers` keeps the dead pawn's equipment, or takes the saved equipment for a joining player.
- [x] **T21.** `BP_GameInstance_NoBrainers`: saves and loads equipment and shop fields. `TakeNextPlayerEquipment`. A new run clears the pending session data.

### Step D — Drops
- [x] **T22.** `BP_ZombieBase`: `WeaponDropChance` 0.01 / `EliteWeaponDropChance` 0.20, and `Server_TryDropWeapon` spawns a tier-locked weapon pickup.
- [x] **T23.** `BP_Zombie_Boss`: `WeaponDropChance` 1.0. All other zombie subclasses had stale 0/0 values, now reset to 0.01/0.20.

### Step E — UI
- [x] **T24.** `BP_PlayerController_ZombieStore`: purchase and reroll server RPCs, plus the weapon shop in `IsInteractionUIOpen` / `CloseActiveInteractionUI`.
- [x] **T25.** `/Game/UI/WBP_WeaponShopCard`: tier border, name, tier, price, stat deltas, and a SOLD / Closed / Can't afford / Buy state.
- [x] **T26.** `/Game/UI/WBP_WeaponShop`: 4 cards, the reroll button with its cost, and a live refresh on `OnShopChanged` and StoreCash.
- [x] **T27.** `BP_PlayerController_ZombieStore.OpenWeaponShopUI`.
- [x] **T28.** `BP_DiscountKiosk` routes `KioskCategory = "Weapons"` to the weapon shop.

### Step F — Tests
- [x] **T29.** Tier math, equipment and drops:
  - `Test_WeaponTier_StatMult`
  - `Test_WeaponTier_MagazineRounding`
  - `Test_WeaponTier_PriceFormula`
  - `Test_WeaponTier_SentinelPaths`
  - `Test_Equipment_DropKeepsTier`
  - `Test_Equipment_TierSurvivesRespawn`
  - `Test_Zombie_WeaponDropTierLocked`
- [x] **T30.** Shop roll:
  - `Test_WeaponShop_RollSlotMix`
  - `Test_WeaponShop_RollNoDuplicates`
  - `Test_WeaponShop_FillFromOtherType`
  - `Test_WeaponShop_TierFromCurve`
  - `Test_WeaponShop_ClosedAtNight`
- [x] **T31.** Purchase, reroll and save:
  - `Test_WeaponShop_PurchaseDeductsAndSells`
  - `Test_WeaponShop_SecondBuyerFails`
  - `Test_WeaponShop_InvalidPurchaseNoDeduct`
  - `Test_WeaponShop_RerollCostDoubles`
  - `Test_WeaponShop_MorningResetsReroll`
  - `Test_Save_EquipmentAndShopRoundTrip`

**Regression set that must stay green:** `Test_Equipment_*`, `Test_Weapons_AllRowsHaveAttackInterval`, `Test_Weapon_CooldownBlocksRefire`, `Test_Data_WeaponRowsComplete`, `Test_Bloom_*`, `Test_Loot_*`, `Test_Player_SpawnsWithStartingPistol`, `Test_K5_InteractablesHaveVerbs`, `Test_InteractionUI_CloseActive`.

## Status notes

- **Junk-start follow-up (2026-09-30):** the starting pistol is now Junk (`GrantStartingLoadoutIfEmpty` calls `EquipWeaponWithTier(Pistol, Junk)`), and the weapon shop rolls tiers on its own curve, `DT_WeaponShopTierCurve` via `BFL_LootMath.GetWeaponShopCurveRow(CurrentDayNumber)`. Day 1 is 80% Junk / 20% Common. Zombie drops keep the night curve.

- See docs/BUGS.md — "Re-picking a dropped weapon refills its magazine (Phase 10)."
- See docs/BUGS.md — "Dropped weapons don't carry reserve ammo (Phase 10)."
- See docs/BUGS.md — "Zombie weapon drops ignore elite/pity tier shifts (Phase 10)."
- See docs/BUGS.md — "Weapon shop purchases after the Day save are lost on quit (Phase 10)."
- See docs/BUGS.md — "Weapon shop charges even if the equip fails (Phase 10)."

## PIE test checklist

1. **Tiers on held weapons:**
   - The starting pistol shows "Junk" on the HUD with the Junk glow, and does slightly less damage (×0.9).
   - Pick up a Rare or Treasure weapon. The HUD label and the glow color change, and a second player sees the same glow.
   - A higher tier does more damage, fires faster, reloads faster and has a bigger magazine: a Rare pistol has 8 rounds instead of 6.
   - A Junk weapon is weaker and has 1 fewer round.
   - Tiers stack with the meta perks: a maxed FireRate perk plus a Treasure gun is faster than either alone.
2. **Drops:**
   - Equipping over an occupied slot drops the old weapon, and it keeps its tier when picked back up.
   - Elites sometimes drop a weapon, and normal zombies rarely do.
   - The boss always drops one.
3. **Weapon shop terminal:**
   - The Weapons kiosk opens the new shop, not the old flat catalog.
   - It shows 4 cards: 1 primary, 2 secondary and 1 melee, with no duplicates.
   - Tier colors and prices look right: Common = DT price, Uncommon ×1.5, Junk ×0.75.
   - Stat deltas compare against your held weapon of that type.
   - It closes on Tab, Esc and E.
4. **Buying:**
   - Buying deducts StoreCash, equips the weapon (dropping your old one), and the card shows SOLD for every player.
   - A second player can't buy the same slot.
   - Can't afford: the button is disabled and no cash is taken.
5. **Reroll:** the first reroll costs $50, then $100 and $200. The cost resets to $50 the next Morning, and every Morning gives a fresh stock.
6. **Phases:** the shop can be used in Morning, Day and Dusk. At Night it shows Closed and purchases fail.
7. **Tier progression:** the day 1 shop shows only Junk and Common, mostly Junk. Uncommon starts appearing a few days in, and stock tiers trend upward on later days (for example, day 1 vs day 8 or later).
8. **Pool:** unlock a new weapon in the meta shop. It can then appear in the stock, and with 2 players the pool is the union of both players' unlocks.
9. **Respawn and save:**
   - Die at Night. After respawning in Morning you still hold the same weapons and tiers.
   - Save and quit mid-run, then load. Equipment tiers, the shop stock (including SOLD slots) and the reroll cost are restored.
   - Start a new run: back to a Junk starter pistol only.
