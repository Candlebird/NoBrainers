# Phase 14: Carry-One-Item Overhaul

**Goal.** Give the Day retail loop more to do and make stocking less tedious. Players carry one item in their hands instead of using an inventory. Full user decisions are in `docs/CARRY_OVERHAUL_DECISIONS.md`, which is authoritative.

**Status (2026-10-01).** Checkpoint 1 (core carry, place, storage zone, inventory removal) was built unattended overnight. Everything compiles. **It needs PIE testing, and the storage zone must be placed in `Map_Store_Outdoors` by hand before playing** (steps below). Checkpoint 2 (throwing) was built on 2026-10-02 and also needs PIE testing. Checkpoint 3 (economy retune and customer scaling) was built on 2026-10-02 and needs PIE testing.

## Before you play: place the storage zone

Agents never edit `Map_Store_Outdoors`. **Until a zone is placed, Dusk deletes every loose pickup on the map.**

1. Open `/Game/Levels/Map_Store_Outdoors` and select the placed `BP_DepositBox`. Note its Location and Rotation.
2. Drag `/Game/Interactable/BP_StorageZone` from the Content Browser into the level.
3. Set the zone's Location X and Y to the box's values, and Z to the floor height plus 200. Set Rotation Yaw to the box's Yaw.
4. Select the `ZoneBox` component and adjust `Box Extent` (default 300, 300, 200) until the green wireframe covers the storage floor. Keep the deposit box inside it. Keep scale at 1,1,1 and change the extent instead.
5. Save the map.

## Checkpoint 1 tasks (built)

- [x] **T1.** Tag `State.Carrying`, added to ActivationBlockedTags on `GA_BP_FireWeapon`, `GA_BP_MeleeAttack` and the 6 `GA_BP_Fire*` children.
- [x] **T2.** `BP_ShelfActor`: pure `FindNearestSlot(WorldPoint, bOccupied)`. Prompt reads "Stock / Take (hold: Upgrade)".
- [x] **T3.** New `BP_StorageZone` with `IsLocationInZone`.
- [x] **T4.** `WBP_ShelfSlot` is display-only (drag/drop and click handling removed).
- [x] **T5.** Tutorial goal and codex text updated for carrying. Their localization keys became plain text.
- [x] **T6.** `BP_PerkComponent` no longer refreshes loot slots.
- [x] **T7.** New replicated `BP_CarryComponent` (carried item, hand mesh, carry tag, drop at feet, drop on death). `BP_ItemPickup.bPlayerDropped`.
- [x] **T8.** `BP_HeroCharacter` uses `CarryComponent` instead of `InventoryComponent`. The gun hides while carrying.
- [x] **T9.** `BP_ItemPickup`: E picks up into the hands, and full hands show "Hands full - set your item down first."
- [x] **T10.** `BP_ShippingCrate` accepts the carried item.
- [x] **T11.** Player controller: E flow (pick up, place on the looked-at shelf slot, drop at feet; tap/hold on shelf with empty hands).
- [x] **T12.** Player controller: `Server_StockItemToSlot` (swap when occupied), `Server_TakeItemFromSlot`. Reload and Build Mode are blocked while carrying. Kiosk Stockroom Expansion is blocked ("being reworked"), and kiosk Item entries show "Unavailable".
- [x] **T13.** Player controller: inventory and deposit UI, quick drop and the related RPCs removed. Tab only closes windows now.
- [x] **T14.** `BP_GameMode_ZombieStore.CleanupLooseItems` runs at Dusk start and deletes every pickup outside all storage zones.
- [x] **T15.** Session save keeps every loose non-weapon pickup and every carried item.
- [x] **T16.** `BP_DepositBox` is a storage marker. E while carrying drops at your feet. On load, saved items respawn as pickups in a 6-wide grid inside the zone.
- [x] **T17.** Tests: 7 obsolete tests deleted, 4 retargeted.
- [x] **T18.** Deleted `BP_InventoryComponent`, `WBP_Inventory`, `WBP_InventorySlot`, `WBP_ItemContextMenu`, `WBP_DepositBox`, `WBP_DepositEntry`, `IMC_Inventory`, `IA_QuickDrop`. Removed Deep Pockets (`DT_MetaPerks` row, `BFL_MetaTiers` functions), with no refund.
- [x] **T19.** New carry tests (6, Retail suite): PickupSetsCarried, DropAtFeet, PlaceAndTakeShelf, DeathDropsItem, BlocksFireTag, DuskCleanupSparesZone (kept last in Retail).

## PIE test checklist (Checkpoint 1)

Run as a 2-player listen server (host plus a client), and check each item on both players.

1. **Pick up.** Pick up a loot item with E. The gun hides and the item shows in your hands. The other player sees it too.
2. **Full hands.** E on a second pickup while carrying shows "Hands full - set your item down first." and the pickup stays.
3. **No combat while carrying.** LMB and melee do nothing. Reload does nothing. Build Mode shows "Put the item down first."
4. **Weapon cycling.** Cycling weapons while carrying keeps the gun hidden.
5. **Drop.** E at open floor sets the item down at your feet.
6. **Shelf place.** E on a shelf places the item in the looked-at slot. On an occupied slot, the items swap.
7. **Shelf take and upgrade.** With empty hands, tap E on a shelf to take an item. Hold E (about 0.4 s) to open the upgrade panel, which closes on Tab, Escape and E. The shelf trade panel opens and closes cleanly.
8. **Tab.** Tab no longer opens an inventory.
9. **Crate.** E on the shipping crate while carrying puts the item in it, and the crate visual updates.
10. **Deposit box.** E on the box while carrying drops the item. Empty-handed, it shows "Set items down near the deposit box. Items in the storage area survive Dusk." **Also try from the client:** the box now acts only on the server, where before it ran on the player's own machine.
11. **Dusk cleanup.** Drop one item inside the storage zone and one outside, then let Dusk start. Only the inside item survives. Weapon pickups outside the zone are deleted too.
12. **Death.** Die while carrying. The item drops at your feet, and after respawn you can fire again. If fire stays blocked, see risk 4 in the plan: a leftover carry tag.
13. **Save and load.** Quit at Morning with items in storage and in hand, then resume. They come back as pickups in a grid inside the zone with the right meshes.
14. **Kiosk.** Stockroom Expansion shows "Stockroom Expansion is being reworked." and charges nothing.
15. **Auto-fire edge.** Holding auto-fire and then picking something up keeps firing until release. This is known (ActivationBlockedTags don't cancel a running ability).

## Checkpoint 2 tasks (built 2026-10-02, needs PIE testing)

- [x] **T1.** New `IA_Throw` (Boolean) in `/Game/Characters/Input/`, mapped in `IMC_Default` to Left Mouse Button and Gamepad Right Trigger. `IA_PrimaryAction` keeps the same keys.
- [x] **T2.** `BFL_LootMath.GetThrowDamageForTier(Tier)` returns Junk 10 / Common 20 / Uncommon 30 / Rare 45 / Treasure 60. `GetThrowDamageForItem(ItemID)` uses the `DT_Items` row tier, and unknown items return 10.
- [x] **T3.** New `/Game/Interactable/BP_ThrownItem`: a replicated, bouncing projectile. `ResolveImpact` behaves like this:
  - Each zombie takes at most one `GE_MeleeDamage` hit (SetByCaller `Data.Damage`) per throw.
  - A first-contact shelf hit fills the nearest empty slot.
  - Anything else becomes a floor pickup when it stops, or after 8 s.
- [x] **T4.** `BP_CarryComponent.ThrowCarried(Charge, AimDir)` is server-only. Speed is lerped from 600 to 1800 by charge. It spawns `BP_ThrownItem` and clears the carried item.
- [x] **T5.** Player controller:
  - `IA_Throw` Started begins a charge when carrying, with no cursor shown and not spectating.
  - Completed runs `ReleaseThrow`: charge = held seconds / 1.0, capped at 1. Aim is the camera forward vector plus a small upward lift. It calls `Server_ThrowCarried`.
- [x] **T6.** Tests (Retail): `Test_Carry_ThrowDamageByTier`, `Test_Carry_ThrowHitsZombieOnce`, `Test_Carry_ThrowIntoShelfFillsNearestEmpty`. `Test_Carry_DuskCleanupSparesZone` stays the last Retail row.

**Design notes.**
- Throw damage uses the item's base tier in `DT_Items`, not the tier rolled when the pickup dropped. The carry stores only the ItemID, so the same item always throws for the same damage.
- Build Mode is refused while carrying (CP1 T12), so a throw press can't place a defense. `IA_Throw` and `IA_PrimaryAction` share Left Mouse. Weapon fire is blocked while carrying by `State.Carrying`.
- There is no charge meter UI.

## PIE test checklist (Checkpoint 2)

Run as a 2-player listen server (host plus a client).

1. **Charge.** Tap and release gives a short lob. A 1 s hold throws much farther. The item leaves your hands and the gun reappears.
2. **Zombie hit.** It damages once. Rare and Treasure items hit noticeably harder than Junk.
3. **Crowd bounce.** Each zombie is damaged at most once per throw.
4. **Direct shelf hit.** The item fills the nearest *empty* slot. The mesh and shelf UI update for both players. Occupied slots are never overwritten.
5. **Full shelf.** A direct hit lands the item as a floor pickup.
6. **Floor bounce into a shelf.** It lands as a pickup and does *not* stock.
7. **Miss.** The item comes to rest as a pickup, and E picks it up.
8. **Client throw.** The host sees the client's throw and its outcome, and vice versa.
9. **Empty hands.** LMB fires the gun normally. While carrying, the gun never fires.
10. **UI open (cursor shown).** LMB doesn't throw.
11. **Build Mode and spectating.** Defense placement and spectator LMB still work.
11b. **Carrying plus Build Mode.**
   - You can't enter Build Mode while carrying.
   - Enter Build Mode first, then try to pick up an item and press LMB. A throw press never places a defense, and nothing fires twice.
12. **Gamepad.** RT charges and throws.
13. **Self-hit.** The item never hits or blocks the thrower on release.
14. **Dusk.** Landed items outside the zone are cleaned up, and ones inside survive.
15. **Tutorial and combo after a throw-stock.** See `docs/BUGS.md` — "Throw-to-shelf stocking bypasses Server_StockItemToSlot side effects."

## Checkpoint 3 tasks (built 2026-10-02, needs PIE testing)

- [x] **T1.** `DT_ShelfTiers`: slots 2 / 4 / 6 / 8 / 12, columns 2 / 4 / 6 / 4 / 6, meshes T0 / T0 / T1 / T2 / T3.
  - **Playtest fix (2026-10-02):** the meshes didn't match the new slot counts. `SM_StockShelf_T0..T4` were rebuilt as 1×2, 1×4, 1×6, 2×4 and 2×6, with a restyled frame (`Tools/Props/blender_store_fixtures.py`). Each tier now uses its own mesh. Rows sit at z 45 and 140, and `BP_ShelfActor.GetSlotTransform` uses Z = 45 + 95·row, so the bigger items fit.
  - All 23 `SM_Item_*` meshes are now 3× real size, 1.5× the previous size (`blender_gear.py` `ITEM_SCALE`), and still imported at 1×.
  - **Playtest fix (2026-10-02):** the HUD hold bar (`WBP_HUD.Bar_RepairHold`, moved out of the interact-prompt border) now fills for shelf hold-E and the throw charge as well as breach repair. The PC has `GetShelfHoldProgress`, `GetThrowChargeProgress` and `GetHoldBarProgress` (the max of the three), and the HUD polls it from Event Tick. The free Spike can be placed again (`BP_BuildModeComponent.CanAffordSelected` honours `bFreeSpike`).
- [x] **T2.** `DT_Items`: `BaseSellPrice` x3 on the 23 loot-pool rows.
- [x] **T3.** `DT_ZombieLoot`: drop chances cut to about 1/3 (Default and Runner 0.047, Spitter 0.053). Elites guarantee 0 extra, and the boss pinata is 3 (max 4) with at least 1 Treasure.
- [x] **T4.** `BP_ZombieBase.RollTieredLoot`: elites drop exactly 1 item.
- [x] **T5.** `BP_StoreEscalationComponent.BaseCustomerBudget` 150 → 450.
- [x] **T6.** `BP_ShelfMatchingComponent`:
  - Fully matched means `BestClusterSize >= NumSlots`.
  - New pure `GetComboThresholds(NumSlots)`: Pair 2, Mid max(3, half) capped at Top, Top = all slots.
  - `GetComboMultiplierForSize(Size, NumSlots)` returns 1.0 / 1.25 / 1.5 / 1.75.
- [x] **T7.** `BP_CustomerSpawner`:
  - The spawn interval and max concurrent customers scale by a stock factor: `clamp(0.25 + 0.075 × stocked items, 0.25, 2.0)`.
  - New vars `StockScaleMin`, `StockScalePerItem`, `StockScaleMax`.
  - New functions `GetTotalStockedItemCount`, `ComputeStockScaleFactor`, `GetStockScaleFactor`.
- [x] **T8.** `DT_CodexEntries`: Store_01, 03 and 04 rewritten for the new slots and combos.
- [x] **T9.** `Tools/loot_sim_data.json` updated. Over 1000 runs, every night lands in band.
- [x] **T11.** Tests: failing tests retargeted to the new values. New Retail tests: `Test_Shelf_MatchedAllSlotsSameCategory`, `Test_ShelfCombo_ThresholdsScaleWithSlots`, `Test_CustomerSpawner_IntervalScalesWithStock`.

## PIE test checklist (Checkpoint 3)

Run on a 2-player listen server.

1. **Slots.** A new shelf has 2 slots. Each upgrade gives 4, 6, 8, then 12, and the slot UI lays out without overlap. Tier0 looks like Tier1 (D2).
2. **Drops.** Night drops are noticeably rarer, and each sells for about 3x. Elites drop about 1 item, and the boss pinata gives at least 3.
3. **Customers.** Customers still buy the higher-priced items. None of them leave because of budget more often than before.
4. **Matched.** A 2-slot shelf holding two items of one category counts as fully matched. Mixing categories does not.
5. **Combos scale.** In the shelf panel:
   - On a 4-slot shelf: 2 same-category adjacent items show +25%, 3 show +50%, and 4 show +75%.
   - On an 8-slot shelf: 4 adjacent items show +50%, and +75% appears only when all 8 match.
6. **Spawn pace.**
   - With empty shelves, customers trickle in about every 32 s.
   - With about 10 items stocked, the pace is the same as before.
   - With 24 or more items, it is about 2x, with more customers in the store at once.
7. **Client.** The client sees the same shelves, prices and customer flow.

## Status notes

- **Pending user decisions:**
  - **Stockroom Expansion.** The kiosk entry is blocked until you decide what it should do now that there's no box capacity. The `DT_KioskCatalog` row is kept.
  - **Save restore into storage.** Saves happen at Morning, so unstored Night loot is moved into storage on resume. Weapons lying on the floor aren't saved.
  - **Dusk deletes weapons.** Weapon pickups outside the zone are deleted, as a literal reading of "deletes every loose item".
  - **D1, combo curve (CP3).** Combo thresholds scale with slot count: pair 2, mid max(3, half), top = all slots. So +75% needs a full shelf on 8- and 12-slot shelves. The alternatives are absolute thresholds (2/3/5) or a purely proportional curve.
  - **D2, Tier0 mesh (CP3).** The 2-slot Tier0 reuses the T0 mesh, so it looks the same as Tier1.
  - **D3, empty-store trickle (CP3).** With zero stock, customers still arrive at a quarter of the base rate (about every 32 s) instead of stopping.
  - **Customer budget (CP3).** `BaseCustomerBudget` was tripled to 450 to match the x3 prices, so affordability stays the same.
- **Known limitations, follow-ups:**
  - Prompts are static. Pickups still say "Pick up" when your hands are full.
  - The storage zone has no in-game visual, only the editor wireframe.
  - Kiosk Item entries are Unavailable, because there's no inventory to put them in.
  - Tutorial and codex text lost its localization keys.
  - Shelf slot positions assume the slot meshes attach to the shelf root.
  - A dropped pickup keeps the default Quantity.
  - A thrown item in flight at Dusk or save time, or one that falls out of the world, is lost. See `docs/BUGS.md` — "Thrown item lost if mid-flight at Dusk/save or past KillZ."
  - The crate shows the wrong message if adding the carried item fails.
  - Old saves can lose shelf items. See `docs/BUGS.md` — "Shelf tier retune truncates items from old saves (Phase 14 CP3)."
