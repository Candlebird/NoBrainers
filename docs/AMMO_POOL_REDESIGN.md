# Ammo-Pool Redesign — Design Note

## Problem

Reserve ammo currently lives per-weapon-slot: `S_EquipmentSlot::ReserveAmmo`, seeded once
at equip time in `BP_EquipmentComponent::Server_EquipItem` from `DT_Weapons`'
`DefaultReserveAmmo` (see `Make S_EquipmentSlot` node wiring `MagazineSize` →
`CurrentAmmo` and `DefaultReserveAmmo` → `ReserveAmmo`). Each weapon slot tracks its own
reserve in isolation — picking up or buying "Rifle Ammo" has no way to refill a
Rifle *and* a Long Rifle carried in different slots from one shared pool, even though
both consume the same ammo type.

## What's already built (untracked this session)

- `DT_Weapons`' `AmmoItemID` field is now populated per row, grouping weapons into three
  shared ammo categories: `PistolAmmo` (Pistol, SMG, Magnum), `RifleAmmo` (Rifle, Long
  Rifle), `ShotgunShells` (Shotgun only). Previously this field was unset on every row
  (see `PHASE_3_TASKLIST.md` line 65's now-stale flag).
- `DT_AmmoCatalog` (new, `S_KioskCatalogEntry` rows) lists the three ammo categories as
  purchasable kiosk entries (`FulfillmentType: Ammo`), for `BP_AmmoKiosk`.
- `BP_AmmoKiosk` and `BP_AmmoPickup` (new actors) exist as the two acquisition paths
  (day-phase purchase, night-phase world pickup) but neither has an ammo-pool target to
  write into yet — `BP_AmmoPickup`'s variables are just `ItemID`/`Quantity`/`bConsumed`.
- `GA_BP_FirePistol/SMG/Magnum/Rifle/LongRifle/Shotgun` — new per-weapon fire abilities
  (previously a single shared fire ability, per git status this replaces it).

## What's missing

`BP_EquipmentComponent` has no pooled-ammo storage at all — no map/array keyed by ammo
category. The per-slot `ReserveAmmo` field is still the only reserve-ammo state that
exists.

**Correction (post-architect-review):** `BP_AmmoKiosk`/`BP_AmmoPickup` do NOT need
changes — both already route into `BP_EquipmentComponent::Server_AddAmmo`, which is the
single server-side ammo-grant chokepoint; it just needs its body repointed at the pool.
Likewise `WBP_HUD` needs no change — it reads ammo exclusively via
`BP_EquipmentComponent::GetActiveAmmo`, so repointing that function's `Reserve` output
at the pool updates the HUD (and `CanReload`/`RefreshAmmoTags`/`Server_ConsumeAmmo`,
which all read through the same function) for free.

## Proposed model

- Add a replicated array of `S_AmmoPoolEntry { AmmoItemID: Name; Amount: int;
  MaxStockpile: int }` on `BP_EquipmentComponent` (`AmmoPool`, with `OnRep_AmmoPool`
  mirroring the existing `OnRep_EquipmentSlots` → `OnEquipmentUpdated`/
  `RefreshAmmoTags` pattern).
- New `DT_AmmoTypes` (`S_AmmoTypeData` rows: `AmmoItemID`, `DisplayName`,
  `DefaultStockpile`, `MaxStockpile`) is the source of truth for starting stockpile and
  cap per category — kept separate from `DT_AmmoCatalog` since that struct
  (`S_KioskCatalogEntry`) is shared with non-ammo catalog rows.
- `Server_EquipItem` stops seeding `ReserveAmmo` from `DefaultReserveAmmo` per-slot;
  instead, on first-ever equip of a weapon whose `AmmoItemID` has no pool entry yet,
  seed that category's pool from `DT_AmmoTypes.DefaultStockpile` once (not from
  `DT_Weapons.DefaultReserveAmmo`, which is order-dependent when multiple weapons share
  a category).
- Reload (`FinishReload`) draws from the pool entry matching the reloading slot's
  `AmmoItemID` instead of decrementing that slot's own `ReserveAmmo`.
  `S_EquipmentSlot::ReserveAmmo` is deprecated in place (pinned to `0`, not physically
  removed yet — four `Make`/`Break S_EquipmentSlot` nodes reference it and removing the
  field risks silently dropping those pins).
- `Server_AddAmmo`'s existing two `TryAddAmmoToSlot` calls are replaced with a single
  `AddToAmmoPool(AmmoItemID, Amount)` call, clamped to `MaxStockpile`. No changes needed
  to `BP_AmmoKiosk`, `BP_AmmoPickup`, or `FulfillKioskEntry`.

## Stockpile caps (decided)

Reserve ammo per category is capped, two tiers:

| Category | Tier | Cap | Starting stockpile | Kiosk purchase quantity |
|---|---|---|---|---|
| `PistolAmmo` | Light | 500 | 500 | 30 |
| `RifleAmmo` | Heavy | 250 | 250 | 20 |
| `ShotgunShells` | Heavy | 250 | 100 | 12 |

Starting stockpile and purchase quantity live on `DT_AmmoTypes` (`DefaultStockpile`) and
`DT_AmmoCatalog` (`Quantity`, currently `1` on all three rows and needs updating to the
values above) respectively — not derived from `DT_Weapons.DefaultReserveAmmo`, since
that column is order-dependent when multiple weapons share a category (Pistol=48 vs
SMG=100 vs Magnum=24 all map to `PistolAmmo`).

(Pistol/SMG/Magnum rounds are the lighter tier; rifle and shotgun rounds are the
heavier tier — assumed from real-world round weight since no other tiering signal
exists in `DT_Weapons`/`DT_AmmoCatalog`. Flag to design if `RifleAmmo` was meant to be
light instead.)

Cap should live as a field on the ammo-pool struct/lookup (not hardcoded per-category
in Blueprint logic), so future ammo categories just need a value, not new branches.
`S_AmmoPoolEntry` should carry `Cap: int` (or the cap should come from `DT_AmmoCatalog`
if that table adds a `MaxStockpile` column) so `Server_AddAmmoToPool`-style logic can
clamp uniformly. Kiosk purchases and pickup consumption should silently clamp (excess
buy is a no-op waste, not an error) rather than blocking the purchase.

## Known bug (reported, not yet root-caused)

Firing a weapon and then reloading leaves the player unable to fire again afterward.
Reported after the `GetActiveAmmo`/`FinishReload` pool wiring above landed, so the pool
read/consume path is the prime suspect (e.g. `bIsReloading` or the fire ability's ammo
gate not resetting cleanly once `ConsumeFromAmmoPool` runs), but this has not been
diagnosed yet — needs a PIE repro (fire a few rounds, reload, try to fire again) and a
trace through `BP_EquipmentComponent`'s reload/fire-ability-gating logic before a fix
lands.
