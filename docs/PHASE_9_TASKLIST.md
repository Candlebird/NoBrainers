# Phase 9 — Tiered Meta Progression

**Goal.** Turn the single-unlock meta perks into 9-tier tracks the player buys in order with meta-currency. Every track is per-player: it changes only the buying player's own pawn and inventory, never teammates or the world.

**Status (2026-09-30).** Built unattended while the user couldn't test. Everything compiles and passes automation, and it's committed locally, not pushed. **Needs PIE testing.** See the "PIE test checklist" at the bottom.

**SUPERSEDED IN PART (2026-10-01):** The Deep Pockets track was removed with no refund by the Carry Overhaul (`docs/PHASE_14_TASKLIST.md`). Deep Pockets rows, tasks and checklist items here are obsolete; the other tracks are unchanged.

## Design decisions (confirmed with the user)

- **Deep Pockets** gives +1 loot slot at tiers 1–6 and +2 at tiers 7–9. That's 6 base slots, 12 at T6 and 18 at T9.
- **Stat tracks** give +5% per tier, up to +45% at T9.
- **Price** is `round(BaseCost × 1.5^(Tier−1))`.
- **Walk speed** is left out as a tiered track. QuickFeet stays a single unlock.
- **Scavenger** stays a single unlock. It's loot luck, which affects the team and world, so it isn't player-specific.

## Data model

- **Rows.** Each track is one row in `DT_MetaPerks`. `S_MetaPerkEntry` has a new `MaxTier` int (default 1).
- **IDs.** Tier 1's ID is the row name, and tier N's is `<Row>_T<N>` (e.g. `FireRate_T4`). All tier IDs go in the existing `UnlockedPerkIDs` name array, so the save format is unchanged.
- **Owned tier** is how many tiers are owned in a row, counting up from 1. A pre-Phase-9 save that owns `DeepPockets` reads as Deep Pockets tier 1.
- **Effects.** Each track applies one infinite GameplayEffect on the server, with the SetByCaller `Data.PerkMagnitude` = per-tier magnitude × tier.

| Track | Stat | Per tier | Base cost |
|---|---|---|---|
| DeepPockets | loot slots | +1 (T1–6), +2 (T7–9) | 150 |
| ThickSkin | MaxHealth | +5 | 100 |
| Endurance | MaxStamina | +5 | 100 |
| HealthRegen | HealthRegenRate | +0.05 | 100 |
| StaminaRegen | StaminaRegenRate | +0.1 | 100 |
| ReinforcedVest | Armor | +5.75 | 100 |
| FireRate | FireRateMultiplier (new) | +0.05 | 100 |
| WeaponDamage | WeaponDamageMultiplier (new) | +0.05 | 100 |
| ReloadSpeed | ReloadSpeedMultiplier (new) | +0.05 | 100 |
| MeleeDamage | MeleeDamageMultiplier (new) | +0.05 | 100 |

**Legacy magnitudes are superseded.** The old single-unlock values (ThickSkin +25, Endurance +30, ReinforcedVest +10) are replaced by the 5%-per-tier rule, which the user chose.

## Tasks

- [x] **T1 (C++).** `UGDAttributeSetBase` gains `FireRateMultiplier`, `WeaponDamageMultiplier`, `ReloadSpeedMultiplier` and `MeleeDamageMultiplier`. Each is replicated, defaults to 1.0, and is clamped to at least 0.1. `AGDCharacterBase` gets `Get<Name>()` getters that fall back to 1.0.
- [x] **T2, T12, T14, T15 (UI prep).**
  - The shop entry has a tier label.
  - The inventory and deposit slots are resized and wrap at 6 per row (inventory) and 3 per row (deposit).
  - `GE_Perk_HealthRegen` and `GE_Perk_StaminaRegen` are added.
- [x] **T3.** `GE_Perk_FireRate`, `GE_Perk_WeaponDamage`, `GE_Perk_ReloadSpeed` and `GE_Perk_MeleeDamage` (Add, SetByCaller `Data.PerkMagnitude`).
- [x] **T4.** `/Game/Core/Meta/BFL_MetaTiers`: tier math plus safe per-actor multiplier getters.
- [x] **T5.** The `S_MetaPerkEntry.MaxTier` column and 12 `DT_MetaPerks` rows.
- [x] **T6.** `BP_PerkComponent`: tier-aware `SubmitUnlockedPerks`, replicated `SubmittedPerkIDs`, and `GetOwnedPerkTier`.
- [x] **T7.** `BP_InventoryComponent`: `RefreshMaxLootSlots` uses the Deep Pockets tier, and the `RestoreInventory` cap reads `MaxLootSlots`.
- [x] **T8.** `GA_BP_FireWeapon`: fire interval ÷ FireRate multiplier (client cooldown and server check), and damage × WeaponDamage multiplier.
- [x] **T9.** `GA_BP_MeleeAttack`: damage × MeleeDamage multiplier.
- [x] **T10.** `BP_EquipmentComponent.Server_Reload`: reload time ÷ ReloadSpeed multiplier.
- [x] **T11.** `BP_GameInstance_NoBrainers`: `GetOwnedPerkTier`, `GetNextTierPrice` (-1 when maxed), `TryPurchaseNextTier`, and an every-tier `Debug_UnlockAllPerks`.
- [x] **T13.** `WBP_MetaShop`: tiered catalog with "Tier X/9", the next price or MAXED (button disabled), and buy-next-tier through `TryPurchaseNextTier`. It uses the existing `EntriesScrollBox`. See docs/BUGS.md — "Phase 9: tiered perks unverified in PIE."
- [x] **T16/T17.** Automation tests (`Test_Meta_*`) plus a hardened `Test_Inventory_PickupBlockedAtCapAllowedWithPerk`. The final suite was 150 PASS / 1 FAIL; the one failure is the known `Test_CustomerSpawnerMaxConcurrent`, and all 8 `Test_Meta_*` tests pass. The tests caught two product bugs, both now fixed:
  - `TryPurchaseNextTier` had a pinless second Return, so failed purchases didn't return false.
  - `GetNextTierPrice` returned 0 instead of -1 for an unknown track, which allowed a free purchase.

## PIE test checklist

1. **Shop:**
   - Each track shows "Tier X/9" and the next price climbs ×1.5 per tier.
   - A maxed track shows MAXED and can't be bought.
   - The list scrolls.
   - An old save that owned Deep Pockets shows it as 1/9.
2. **Slots:**
   - At Deep Pockets T6 the inventory shows 12 slots (2 rows of 6) and the deposit box shows its 3-wide grid. At T9 both show 18.
   - Slot text is readable (slots are 100 px wide).
   - The tier border colors still show on deposit entries.
3. **Two-player isolation.** Host and client buy different tiers. Each player's slots and stats reflect only their own purchases.
4. **Maxed stats:**
   - Max health and max stamina reach 145.
   - Health regen is visibly faster.
   - Stamina regen is faster. Confirm something actually reads `StaminaRegenRate`.
   - Armor reduces damage taken.
5. **Weapons:**
   - Fire rate is noticeably faster at T9, and the server doesn't reject shots, which would show as dropped hits or log warnings.
   - Weapon and melee damage are higher (shamblers die in fewer hits).
   - Reload is faster.
6. **Respawn.** Die and respawn. Tier effects don't stack: stats are the same as before death.
7. **Failed purchase.** Buying without enough currency does nothing and doesn't deduct currency.

Open issues are tracked in `docs/BUGS.md` under the "Phase 9" entries.
