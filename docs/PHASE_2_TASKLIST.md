Phase 2: Day Phase & Retail Loop

Technical Context

Engine Version: Unreal Engine 5.7.4

Perspective: First-Person

Architecture: Server-authoritative inventory, shelf management, customer archetype behavior trees, dynamic customer event manager, and economy system with RPC updates to clients.

Goal: Implement the complete daytime retail gameplay loop, including item data structures, inventory management, interactive shelf stocking with matching-bonus logic, diverse customer archetypes, dynamic customer events, and the employee discount shop.

Status note (autonomous overnight run, unreviewed — check these design calls in the morning):
- Task 3.2 (Customer AI): resolved an ambiguity between 2.3's matching bonus ("+25%/+50% Sell Price / Customer Buy Probability") and 3.2's price-tolerance check. Buy-probability and price-charged are treated as separate axes: a customer's price-tolerance check (`MaxPriceMultiplier`) is evaluated against the item's unmodified `BaseSellPrice`, not the matching-inflated price — so shelf matching bonuses raise both the revenue collected AND (via a separate probability roll) the chance of a sale, without making low-tolerance archetypes (e.g. Cheap) reject well-stocked shelves. Revert this if you intended matching to make items less attractive to price-sensitive customers.
- Task 5.1 (Shared Store Money Engine) landed early/partially as a side effect of 3.2: `BP_GameState_ZombieStore` now has `StoreCash` (replicated int32) and `Server_AddCash()`, named exactly per 5.1's spec, since 3.2's own task text names `StoreCash` as the purchase deposit target. `Server_DeductCash()` and purchase-validation are NOT added yet — that's still open 5.1 work.
- Task 3.2 built: `BP_ShelfActor` gained `GetNumSlots`/`GetSlotOffer`/`Server_PurchaseSlot`+`OnSlotPurchased` dispatcher; new `BP_CheckoutCounter`/`BP_CustomerExitPoint` actors; new `BP_Customer` character, `BB_Customer`/`BT_Customer`/`AIC_Customer`, and BT tasks `BTT_FindBestShelfSlot`/`BTT_TakeItemFromShelf`/`BTT_ClaimCheckoutCounter`/`BTT_CompleteCheckout`/`BTT_LeaveStore` + service `BTS_ValidateTargetShelf` (all under `Content/AI/Customer/`). `lint_behavior_tree`/`validate_behavior_tree` both pass clean (0 issues). Price-tolerance-vs-matching-bonus resolution used the axis-separation approach noted above; shelf-slot price tolerance check uses a flat baseline reference price of 100 (no better per-category anchor existed) — revisit if that skews archetype buying behavior once tested.
- **Needs manual testing before trusting this in-game (not yet done, nav mesh not built, no PIE run):** build navigation over the store level, place a stocked shelf + `BP_CheckoutCounter` + `BP_CustomerExitPoint`, spawn a `BP_Customer` via `AIC_Customer`, and confirm the full loop (shelf pick → walk → purchase → walk to checkout → `StoreCash` increases → walk to exit → despawn), plus the shelf-sniped-mid-walk race case and multiple customers not double-claiming one checkout counter. See the 3.2 builder's full test notes if something looks off.
- Task 4.1 (Customer Spawner Engine) built: new `BP_CustomerSpawnPoint` (placeable marker, `bEnabled` toggle) and `BP_CustomerSpawner` (`Content/AI/Customer/`) driving weighted-random archetype spawning during `DayPhase`, scaling spawn interval/concurrent cap off `StoreAdvertisementLevel` (new placeholder replicated int on `BP_GameState_ZombieStore`, default 1, reserved for 5.2's marketing system), plus a pre-built `Server_SpawnCustomerBurst` for 4.2. Also fixed a real pre-existing bug as a prerequisite: `BP_Customer`'s class defaults had `AIControllerClass` = engine-default `AIController` and `AutoPossessAI` = `PlacedInWorld`, meaning runtime-spawned customers never ran `BT_Customer` — corrected to `AIC_Customer` / `PlacedInWorldOrSpawned`.
  - Three more confirmed Monolith tooling limitations worked around here (matching the pattern already seen in 3.2): `SpawnActorFromClass` doesn't expose "expose on spawn" pins or a correctly-typed return value through Monolith, so `ArchetypeRow` is set post-spawn via cast+`add_property_access` instead of true expose-on-spawn; `AActor::OnDestroyed` still can't be bound via Monolith's delegate APIs, so despawned customers are pruned from `ActiveCustomers` via an `IsValid` self-pruning loop rather than a destroy callback (a correctly-built but unbound `HandleCustomerDestroyed` function was left in place for optional manual wiring in the live editor); and binding to `BP_GameState_ZombieStore::OnPhaseChanged` (a Blueprint-defined dispatcher, not just native ones) also reproducibly fails to compile via Monolith, so day/night phase changes are now detected by a 1-second `PollPhaseChange` timer comparing cached vs. current phase instead of an event bind — sub-second latency, functionally fine for a day/night transition but no longer literally event-driven.
  - `ArchetypeSpawnWeights` (Normal 40/Cheap 15/Scavenger 12/Fighter 10/Nurse 10/TrinketCollector 8/Rich 5) are placeholder tuning values with no design-doc source — confirm/adjust once customers are actually visible in a PIE run.
  - **Needs manual testing (not yet done):** place a `BP_CustomerSpawner` plus several `BP_CustomerSpawnPoint`s and the existing checkout/exit/shelf actors in a level with a built nav mesh, then verify in PIE: spawns only during `DayPhase` and stop on `NightPhase`/`RunOver`, spawn cadence and concurrent cap respond correctly to `StoreAdvertisementLevel`, weighted archetype distribution looks sane, and despawned customers actually drop out of `ActiveCustomers` (no cap lockup from stale entries).
- Task 4.2 (Dynamic Customer Event Manager) built: `CurrentDayNumber`/`ActiveEventRow`/`PendingEventRow`/`PendingEventDay` (replicated) + accessor/mutator functions added to `BP_GameState_ZombieStore`; new `S_CustomerEventData` struct + `DT_CustomerEvents` DataTable (6 preset events — NurseConvention/FighterGuild/ScavengerHunt/TrinketFair/HighRollers/BargainRush — with target archetype, share, spawn-interval multiplier, concurrent-cap bonus, min-day gate, and selection weight); `BP_CustomerSpawner` gained an event-override layer (`EventArchetypeRow`/`Share`/`IntervalMultiplier`/`ConcurrentBonus` + `SetEventOverride`/`ClearEventOverride`/`ReconcileEventOverride`) checked first in `PickWeightedArchetypeRow` and folded into `GetCurrentSpawnInterval`/`GetMaxConcurrent`; `BP_GameMode_ZombieStore` now owns the scheduler (`PickEventRow`/`RollNextEventDay`/`ApplyEventToSpawners`/`EvaluateDailyEvent`/`AnnounceUpcomingEvent`, wired into `StartDayPhase`/`StartNightPhase` without reordering the existing phase/respawn/timer chain) — event cadence is a random 3–6 in-game days, with the next event pre-picked and announced at the start of the preceding night phase. New `WBP_EventBanner` widget (polls GameState every 0.25s, no dispatcher binding, per the confirmed Monolith delegate-bind limitation) shows a "TOMORROW: <event>" banner on announcement and "TODAY: <event>" when it goes live, auto-hiding after 6s; created and added to viewport from `BP_PlayerController_ZombieStore` alongside the existing inventory widget. All pieces compiled clean (0 errors/warnings) and saved. Event preset tuning values (shares, interval multipliers, concurrent bonuses, weights) are unsourced placeholders, same caveat as 4.1's archetype weights — confirm/adjust after seeing it in PIE.
  - **Needs manual testing (not yet done):** run PIE across several day/night cycles and confirm `CurrentDayNumber` increments once per day, an event fires within the 3–6 day window, the spawn mix visibly skews toward the target archetype and density increases during the event, the banner shows both the "tomorrow" preview and "today" live states at the right times, and everything clears cleanly at night (no event bleeding into the next day, no banner stuck visible).

Older status note: none of the checkbox items below changed state this session, but supporting work landed that a later pass should credit once its own checkbox exists — 1.2's `UInventoryComponent` (Blueprint: `BP_InventoryComponent`) now has a player-facing UI (`WBP_Inventory`/`WBP_InventorySlot`), toggled with the `IA_ToggleInventory` Tab binding wired into `BP_PlayerController_ZombieStore`. This isn't tracked as its own line item in this file (nor in `PHASE_6_TASKLIST.md`'s HUD/UI section) — a future task-list edit should add one rather than silently checking an existing box. Also fixed in passing: `BP_InteractionProbe::UpdateInteractionTarget` was throwing a pending-kill access error on `CurrentTarget` when an `AItemPickup` was destroyed mid-frame by pickup; it now uses `IsValid` instead of a null check before un-highlighting the old target. Task 2.1 (First-Person Interaction Raycast) remains unchecked — `BP_InteractionProbe` exists and drives target highlighting via a render-custom-depth stencil, but nothing in the project yet binds `IA_Interact` to an actual interact/confirm call, so 2.1 isn't fully satisfied yet.

Task Breakdown

1. Data Architecture & Inventory System

[x] 1.1 Item Data Definition (FItemData Struct & Data Table)

Create FItemData struct (USTRUCT):

FName ItemID

FText DisplayName

EItemCategory Category (e.g., Food, Ammo, Medical, Hardware, Trinkets)

int32 BaseSellPrice

int32 DiscountCost (Employee purchase price)

float DropWeight (For zombie death loot tables)

UStaticMesh* DisplayMesh

UTexture2D* Icon

Create Data Table DT_Items populated with initial zombie drops and buyable items.

[x] 1.2 Inventory Component (UInventoryComponent)

Create UInventoryComponent attached to ACharacter_Player:

Replicated array: TArray<FItemSlot> InventorySlots.

Server RPCs: Server_AddItem(), Server_RemoveItem(), Server_DropItem().

Delegates for UI updates: OnInventoryUpdated.

[x] 1.3 World Pickup Actor (AItemPickup)

Create interactable item actor in world space (IInteractableInterface):

Holds FItemData or ItemID.

Highlight shader when targeted by first-person interaction trace.

Server-validated pickup logic transferring item to player inventory.

2. Shelf Stocking & Matching Minigame

[ ] 2.1 First-Person Interaction Raycast

Implement line-trace in ACharacter_Player mapped to IA_Interact.

Highlight targeted IInteractableInterface actors (Pickups, Shelves, Cash Registers, Traps).

On hold — deferred until further notice. Current investigation found that pickup already works today via `GA_Interact` (a GAS ability bound to the legacy `Interact` ActionMapping, key F), which does its own independent camera line-trace and doesn't consume `BP_InteractionProbe`'s `CurrentTarget` at all. Do not pick this task back up until explicitly given permission.

[x] 2.2 Shelf Actor Architecture (AShelfActor)

Create AShelfActor:

Configurable array of FShelfSlot transforms (e.g., Grid of 2x3 or 3x4 slots per shelf).

Replicated array: TArray<FItemData> StockedItems.

Spawn/attach static meshes (DisplayMesh) at designated slot transforms upon item placement.

[x] 2.3 Adjacent Matching Logic (UShelfMatchingComponent)

Implement matching evaluation on item placement/removal:

Check if placed item shares ItemID or EItemCategory with adjacent slots on the same shelf.

Apply bonus modifiers:

2 Matched: +25% Sell Price / Customer Buy Probability.

3+ Matched (Full Row): +50% Sell Price / Customer Buy Probability.

Replicate slot bonus multipliers to client UI.

3. Customer Archetypes & Buying Preferences

[x] 3.1 Customer Archetype Enum & Data Structure (ECustomerType)

Define ECustomerType enum:

Normal: Buys all categories equally; standard price tolerance.

Rich: Buys items at higher price thresholds (higher profit margins).

Cheap: Only buys items priced low or heavily discounted.

Fighter: Priority buying logic targeting EItemCategory::Hardware and EItemCategory::Ammo.

Nurse: Priority buying logic targeting EItemCategory::Medical.

Scavenger: Priority buying logic targeting EItemCategory::Food.

TrinketCollector: Priority buying logic targeting EItemCategory::Trinkets.

Define FCustomerArchetypeData struct (Category preferences, Max Price Multiplier, Walk Speed, Mesh Variations).

[x] 3.2 Customer AI Behavior Tree Integration

Extend ACustomerCharacter and Behavior Tree (BT_Customer):

Filter available AShelfActor targets based on ECustomerType category preferences.

Evaluate shelf prices against archetype price tolerance threshold before deciding to purchase.

Purchase selected item, proceed to checkout counter, deposit cash into AGameState_ZombieStore::StoreCash, and exit.

4. Daytime Spawner & Dynamic Customer Events

[x] 4.1 Customer Spawner Engine (ACustomerSpawner)

Spawns customer waves during DayPhase.

Weighted random selection pool for standard daytime customer spawning.

Base spawn rate scales dynamically with StoreAdvertisementLevel.

[x] 4.2 Dynamic Customer Event Manager (UCustomerEventManager)

Interval Trigger: Automatically schedules a CustomerEvent every randomized 3 to 6 days.

Event Execution:

Overrides default random spawn pool with a high-density wave of a specific target archetype (e.g., "Nurse Convention" day spawning 80% Nurses, or "Fighter Guild" day).

Notifies clients via HUD banner/event notification to allow players to pre-stock shelves strategically based on upcoming customer surges.

[x] 4.3 Fallback Consignment / Shipping Crate (AShippingCrate)

Create AShippingCrate interactable actor (usable if NPC models/animations are disabled):

Liquidates items dropped into it at the end of the day phase, adding earnings directly to AGameState_ZombieStore::StoreCash.

- Task 4.3 built as Blueprint `BP_ShippingCrate` (not native `AShippingCrate`, same precedent as GameState/GameMode being Blueprint): parented to `BP_Interaction_Base`, reuses the existing `BPI_Interactable`/`GA_Interact` path (no changes to `BP_InteractionProbe`/`IA_Interact`/`IMC_Default`, task 2.1 stays on hold). Replicated `CrateContents` (`array<S_ItemSlot>`), `MaxSlots` (default 20, 0=unlimited), `LiquidationRate` (default 0.5, placeholder pending tuning), `bAbsorbOverlappingPickups` (default true), replicated `LastLiquidationTotal`. Deposits work two ways: interacting (F) dumps the player's whole inventory into the crate via `BP_InventoryComponent::Server_RemoveItem` + `AddItemToCrate`; overlapping a dropped `BP_ItemPickup` auto-absorbs it and destroys the pickup. `GetCrateValue()` prices contents from `DT_Items`/`S_ItemData.BaseSellPrice` at `LiquidationRate` (deliberately worse than a customer sale, since this is the fallback path). `BP_GameMode_ZombieStore` gained `LiquidateAllCrates()` (finds all crates, calls `Server_LiquidateCrate` on each) appended as the new terminal node in `StartNightPhase` after the existing `Announce Upcoming Event` call — no other StartNightPhase/StartDayPhase wiring touched. All cash flows through the existing `GameState::Server_AddCash`, HasAuthority-guarded throughout. Compiled clean, saved.
  - **Needs manual testing (not yet done):** drop loose items near a crate and confirm overlap auto-absorb; interact with F to deposit full inventory; run a day→night transition and confirm `StoreCash` rises by ~half the deposited items' base sell value, crate empties, and the emptied state replicates to clients.

5. Employee Discount Store & Purchasing System

[x] 5.1 Shared Store Money Engine

Replicated variable in AGameState_ZombieStore: int32 StoreCash.

Thread-safe transaction methods: Server_AddCash(), Server_DeductCash().

- `StoreCash` (replicated, on `BP_GameState_ZombieStore`) and `Server_AddCash()` already existed from task 3.2; this task closed out the remainder. Added `GetStoreCash()` (pure getter, for 5.2's kiosk UI to read cash without a raw VariableGet across classes), `CanAfford(Cost)` (pure, rejects negative costs), and `Server_DeductCash(Cost) -> bSuccess` (HasAuthority-guarded, then CanAfford-guarded, all-or-nothing deduction; `bSuccess` output lets 5.3's purchase logic branch on whether to actually grant the item). Also retrofitted a HasAuthority guard onto the previously-unguarded `Server_AddCash` for consistency with the rest of the money engine. **Important for 5.3:** these are Blueprint functions, not RPCs — `BP_GameState_ZombieStore` isn't client-owned, so a client can't call `Server_DeductCash` remotely. 5.3's purchase flow must route through a `Server_`-prefixed Custom Event on the player's own PlayerController/Character (which *can* carry RPC flags), which then calls into the GameState function server-side. Compiled clean, saved.
  - **Needs manual testing (not yet done):** verify a day-end shipping-crate payout still lands correctly after the `Server_AddCash` guard retrofit (should be unaffected, all existing callers are server-side); no other in-game test surface yet since there's no purchase UI to trigger `Server_DeductCash` until 5.2/5.3 land.

[x] 5.2 Employee Discount Kiosk UI (UUserWidget)

UI Kiosk interface displaying purchasable catalog:

Personal weapons and ammo.

Defense blueprints (Spike Traps, Turrets, Barricades).

Shelf expansion upgrades.

Marketing / Store Advertisements (Increases day foot traffic & night zombie threat).

- New data assets `S_KioskCatalogEntry` (struct) + `DT_KioskCatalog` (DataTable), seeded with placeholder rows across all 5 categories (Ammo/Weapons/Defense/Upgrades/Marketing), costs sourced from `DT_Items.DiscountCost` where applicable, pending tuning. `WBP_KioskEntry` (row widget, click-to-buy via `OnMouseButtonDown` override since Monolith can't wire `UButton::OnClicked`) and `WBP_KioskCatalog` (catalog container: title/cash header, scrollable entry list, footer hint, polls `GameState::GetStoreCash` every 0.25s to refresh cash text and per-entry affordability, Escape-to-close via `OnKeyDown`). `BP_DiscountKiosk` interactable (parented to `BP_Interaction_Base`, mirrors `BP_ShippingCrate`'s pattern) opens the UI only for the locally-controlled interactor (`IsLocalController` guard, NOT `HasAuthority` — opposite case from the crate, since this is client-local UI, not server work). `BP_PlayerController_ZombieStore` gained `KioskWidget` var + `OpenKioskUI()`/`CloseKioskUI()`, additive only, existing interact/input wiring untouched (task 2.1 hold respected). `WBP_KioskCatalog::RequestPurchase(RowName)` is deliberately left as a stub (Print String + TODO) — task 5.3 implements the actual purchase/deduction flow against `Server_DeductCash`. Compiled clean (0 errors/warnings), saved.
- **Needs manual testing (not yet done):** interact with a placed `BP_DiscountKiosk` to confirm the catalog opens with correct input-mode/cursor switch; click a `WBP_KioskEntry` to confirm the purchase click registers (entry hit-test visibility was fixed mid-build) and unaffordable entries don't fire; Escape closes the kiosk and other keys pass through as Unhandled; cash/affordability live-update as `StoreCash` changes, with the poll timer properly cleared on close (no leak).

[ ] 5.3 Purchase Execution Logic

Validate player cash reserves on server before completing purchase.

Deduct cost, update inventory or spawn item/blueprint in world.

6. Persistence & Save System

[ ] 6.1 Save Game Slot Manager (USaveGame_Subsystem)

Create a Game Instance Subsystem handling local file read/write operations (USaveFile).

Define serialization structs for in-run session state (Day count, Store Cash, player inventories) and meta-progression state (unlocked blueprints, meta-currency).

[ ] 6.2 Data Struct Serialization

Ensure all dynamic structures (FItemData, inventory arrays, socket occupancy states, store advertisement level) implement proper serialization interfaces so runs can be safely loaded or resumed if needed.

Acceptance Criteria

Customer spawning uses distinct archetypes (Normal, Rich, Cheap, Fighter, Nurse, Scavenger, Trinket Collector) that filter shelves based on price tolerance and item categories.

Every 3 to 6 days, a CustomerEvent triggers, broadcasting a HUD event and flooding the store with a specific customer type.

Shelf-stocking matching logic applies price and buy-probability multipliers to adjacent identical/category items.

Players can stock shelves manually (or use the Shipping Crate fallback) to turn zombie drops into store revenue.

Store revenue is spent at the Employee Discount Kiosk to buy player gear, store upgrades, and defenses.

