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
- **Status update (overnight session):** the asset claims above were all accurate, but a live re-verification found the shopping loop was actually completely non-functional despite every asset existing and compiling clean. Root cause: `BT_Customer`'s `BlackboardAsset` was mistakenly set to `/Game/GASDocumentation/Characters/Minions/BB_Minion` (only `SelfActor`/`TargetActor` keys) instead of a dedicated customer blackboard — every task resolves its keys (`TargetShelf`, `TargetSlotIndex`, `TargetItemID`, `PurchaseEffectivePrice`, `HasPurchasedItem`, `AssignedCounter`, `ExitPoint`) by literal name at runtime, so none of them ever resolved and the whole tree silently no-op'd. Additionally, all three `BTTask_MoveTo` nodes ("Move To Shelf", "Move To Counter", "Move To Exit") had no/incorrect `BlackboardKey` targets (two unset, one pointing at `SelfActor`), so even with keys resolving, customers would never actually walk anywhere. Fixed in three steps: (1) created `/Game/AI/Customer/BB_Customer` with the correct 8 keys and repointed `BT_Customer`'s root to it; (2) wired the three MoveTo nodes to `TargetShelf`/`AssignedCounter`/`ExitPoint` respectively via `BlackboardKey.SelectedKeyName`; (3) restructured the tree root from a bare Sequence into a Selector with the original shop/checkout Sequence as the first branch and a new fallback branch (`Wait 3s` → `BTT_LeaveStore`) as the second, so a customer that finds no stocked shelf idles briefly and leaves instead of busy-looping `GetAllActorsOfClass` every frame and permanently occupying a `BP_CustomerSpawner` concurrency slot. `validate_behavior_tree`/`lint_behavior_tree` pass clean (0 issues, lint score 100) after all three steps. Cash-awarding (`BTT_CompleteCheckout` → `BP_GameState_ZombieStore::Server_AddCash`, which also increments `TotalCashEarned` per `PHASE_5_TASKLIST.md` §3.2) needed no changes — it was always correct, just unreachable until the blackboard/key fixes landed. **Still needs manual PIE verification** — nothing above has been run in-game: confirm customers spawn, path to a stocked shelf, purchase (StoreCash increases), path to checkout, path to exit, despawn; confirm a customer with no valid shelf idles ~3s then leaves instead of freezing; and confirm the shelf-sniped-mid-walk race and multi-customer checkout-counter contention noted above.
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

- **STATUS NOTE (2026-09-23):** extended beyond this task's originally-written single-item flow into a full multi-shelf browsing loop, per user request. `BT_Customer` rebuilt as a 4-branch root Selector (Checkout And Leave / Leave Empty Handed / Browse Shelf / Shelf Attempt Failed): a customer browses up to `MaxShelfVisits` (5) shelves, rolling ~40% done-shopping after each successful purchase, with a bounded 3-attempt retry (`MaxFindAttempts`) before leaving empty-handed if no matching item is ever found. Checkout now gates on player interaction — `BTT_WaitForCheckoutInteraction` waits for an F-keypress on `BP_CheckoutCounter` (now `BPI_Interactable`-driven) rather than auto-completing, and pays out the customer's full `CartTotal` (accumulated across all purchased shelf visits) in one lump sum via `BP_GameState_ZombieStore::Server_AddCash`, fixing what would otherwise have been a last-item-only payout bug once multi-shelf shopping was added. New/changed assets: `BB_Customer` (+`ShelvesVisited`/`ReadyToCheckout`/`WaitingForPlayer`/`MaxShelfVisits`/`CartTotal`/`FailedFindAttempts`/`MaxFindAttempts`), `BTT_RollShoppingDone`, `BTT_RegisterFailedShelfAttempt`, `BTT_WaitForCheckoutInteraction` (new tasks), `BTT_CompleteCheckout` (payout logic moved out to the wait task), `BTT_TakeItemFromShelf` (cart accumulation), `BTT_LeaveStore` (releases a claimed checkout counter on exit to prevent a permanent-lock leak), `AIC_Customer` (blackboard defaults now explicitly initialized in `OnPossess`, since this project's BB-key tooling has no stored-default support). Landed and compiled clean; **not yet confirmed in PIE** — see chat/session log for the full build trail. One known minor risk not yet fixed: `BP_CheckoutCounter::CanInteract` is technically true from the moment a counter is claimed (before the customer physically arrives), mitigated by clearing `bServed` at the start of `BTT_WaitForCheckoutInteraction`, but a fuller fix (gating interactability on customer arrival) was deliberately deferred — flag to user if it proves noticeable in testing.

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
  - **Core liquidation math automation-verified (2026-09-24):** `Test_ShippingCrate_LiquidatesToStoreCash` in `BP_TestController` adds an item via `AddItemToCrate`, calls `Server_LiquidateCrate` directly, and asserts `StoreCash` rose by exactly the crate's pre-liquidation `GetCrateValue()` and the crate's contents array is empty afterward. Confirmed passing in a clean 24/24 PIE run (`pie_smoke_44_054057`). This only exercises the direct-call liquidation math, not the surrounding player-facing paths — **still needs manual testing:** drop a loose item near a crate and confirm overlap auto-absorb; interact with F to deposit full inventory; and confirm the emptied/updated crate state replicates to clients, plus that `LiquidateAllCrates`/the real day→night transition actually calls `Server_LiquidateCrate` on every crate in the level.

- **STATUS NOTE (2026-09-24, overnight session — checkout loop hardening):** the customer checkout loop is now automation-verified end to end. Root-caused and fixed the checkout counter stand-location bug (see `docs/BUGS.md` — "Checkout counter stand-location bug — customer permanently loops between claim/queue (RESOLVED)"): `BTT_MoveToCounter` was keyed on the counter actor's own (non-navigable) transform instead of a NavMesh-projected stand point, causing every checkout attempt to fail its move and fall back into re-queuing forever. Added `BP_CheckoutCounter::GetCustomerStandLocation()` + a `CounterStandLocation` Blackboard key, retargeted the MoveTo task, and added a guard against a counter's own occupant re-joining its own queue. Added/confirmed passing in `BP_TestController`: `Test_CustomerCheckout_PaysAndDespawns` (full shelf-stock → browse → pick up → checkout → pay → despawn loop) and `Test_CheckoutCounter_TryClaimReturnsTrue`, alongside the pre-existing `Test_CheckoutQueueOrdering`/`Test_CheckoutQueueSpotLocation`/`Test_DayEndAutoSellCustomerItems`. All verified in a correctly session-scoped, 75-second PIE automation run (13/14 sync tests pass; only the unrelated pre-existing `Test_Equipment_ReloadReplenishesMagazine` GAS bug fails). Vision-keeper gate 2: ALIGNED. Committed (`40c8a41`), not pushed. This closes out the "day-end auto-sell + core checkout loop" portion of Task 3.2's original scope with real test coverage backing it, superseding this task's earlier "not yet confirmed in PIE" caveat above for the checkout-and-payout path specifically (multi-shelf browsing UX itself is unchanged and still not manually PIE-tested).

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

[x] 5.3 Purchase Execution Logic — complete

Validate player cash reserves on server before completing purchase.

- **Unblocked and completed.** The prior blocker (Monolith v0.22.0 unable to add typed pins to an existing `K2Node_CustomEvent`) turned out to be moot: `Server_RequestKioskPurchase`/`OnServerRequestKioskPurchase` is a real C++ Server RPC already declared on `AGDPlayerController` (`Source/GASDocumentation/Public/Player/GDPlayerController.h`), not a Blueprint Custom Event — its `OnServerRequestKioskPurchase(EntryID)` BlueprintImplementableEvent hook was already overridden in `BP_PlayerController_ZombieStore` and wired to `ExecuteKioskPurchase`, and `WBP_KioskCatalog::RequestPurchase` already called the RPC correctly. Also found (separately) that Monolith's blueprint namespace now exposes `set_custom_event_params`, so the originally-reported tool gap no longer exists regardless.
- Remaining real gap was that `ExecuteKioskPurchase`'s single shared `Client_KioskPurchaseResult` call always fired with `bSuccess=false`/`Message=""` regardless of which exit branch was taken. Fixed by adding two function-local variables (`Result_bSuccess`, `Result_Message`) set immediately before each of the 7 exit branches (row-not-found, cast-failed, can't-fulfill, can't-afford, deduct-failed, fulfill-failed, success), then read into the shared `Client_KioskPurchaseResult` call via Get nodes.
- Added `ShowPurchaseResult(bSuccess, Message)` function to `WBP_KioskCatalog` (PrintString screen feedback, green on success/red on failure, plus `RefreshAffordability`/`RebuildCatalog` refresh on success) and wired `Client_KioskPurchaseResult`'s body on `BP_PlayerController_ZombieStore` to call it via an `IsValid(KioskWidget)`-guarded branch. Note: no dedicated status TextBlock exists in the kiosk widget tree yet — the result surfaces as a transient on-screen PrintString rather than a persistent UI label; adding a permanent status widget is `ue-ui-builder` scope (widget-tree edit) if that polish is wanted later.
- Compiled clean (0 errors/warnings) on `BP_PlayerController_ZombieStore` and `WBP_KioskCatalog`, vesper-laid-out, saved.
- **Needs manual testing (not yet done):** interact with `BP_DiscountKiosk`, purchase an affordable entry and confirm cash deducts, item/blueprint grants, and a green "Purchase successful." message appears; attempt an unaffordable/invalid entry and confirm a red failure message with no cash deduction; confirm `KioskPurchaseCounts`/`MaxPurchases` capping still blocks repeat buys via `CanFulfillKioskEntry`.

Deduct cost, update inventory or spawn item/blueprint in world.

6. Persistence & Save System

[x] 6.1 Save Game Slot Manager (USaveGame_Subsystem)

- **Deviation from title (justified, documented by the architect):** `UGameInstanceSubsystem` cannot be a Blueprint (`Abstract, Within=GameInstance`, no `Blueprintable`), and the save payload is typed in UserDefinedStructs (`S_ItemSlot`, catalog rows) a C++ subsystem couldn't reference without duplicating shapes. Built as `BP_GameInstance_NoBrainers` (Blueprint `GameInstance` subclass) instead — same lifetime/singleton semantics, stays Blueprint-first per project preference. Wired as the project's `GameInstanceClass` in `Config/DefaultEngine.ini`.
- New structs in `/Game/Data/Save/`: `S_SaveNameCount`, `S_SavePlayerInventory`, `S_SaveShelfState` (declared now, populated by 6.2), `S_SaveSession` (day/phase/cash/ad level/event state/kiosk purchase counts/player inventories/shelf states, versioned), `S_SaveMeta` (meta-currency, unlocked blueprint IDs, run stats, versioned). `S_ItemData` (holds mesh/texture object refs) is deliberately never serialized — only `ItemID` FName tokens via `S_ItemSlot`.
- New SaveGame Blueprints `/Game/Core/Save/BP_SaveGame_Session` and `BP_SaveGame_Meta`.
- Additive accessors: `BP_GameState_ZombieStore::GetSaveSnapshot`/`RestoreSavedState` (server-only), `BP_InventoryComponent::GetInventorySlots`/`RestoreInventory` (server-only). Existing logic on both untouched otherwise.
- `BP_GameInstance_NoBrainers`: gather/save/load/apply/delete session, meta load-or-create/save/add-currency/unlock-blueprint, all gated on host authority (`GetGameMode()` validity check). `SaveVersion` mismatch on session load deletes the stale slot rather than applying it. Meta persists across a version bump (added/removed struct fields tolerate tagged serialization). Player-inventory restore keyed by join-order slot index — no stable cross-session player identity exists yet in the project (documented assumption, revisit when online identity lands).
- Hooked into `BP_GameMode_ZombieStore`: `StartDayPhase` now calls `SaveSession` each day transition; `EndRun` calls `DeleteSessionSave` (roguelite runs reset) then `RecordRunEnded` (increments `TotalRunsCompleted`/`BestDayReached` only — does **not** award meta-currency, that's Phase 5's job); `RespawnDeadPlayers` restores each respawning pawn's pre-death inventory via `TakeNextPlayerInventory`/`RestoreInventory`, tracked by a new `NextJoiningPlayerIndex` counter var.
- Task 2.1 hold respected (no changes to `BP_InteractionProbe`/`IA_Interact`/`IMC_Default`/interact binding). Compiled clean (0 errors/warnings) on all touched Blueprints, vesper-laid-out, saved.
- **Needs manual testing (not yet done):** confirm `GameInstanceClass` override actually takes effect in PIE (log/print in `ReceiveInit`); full day-cycle save→restart→load round trip (day number/phase/cash/ad level restore correctly, meta currency/unlocks persist across PIE sessions); `EndRun` both victory/defeat paths (session slot actually deleted, `RecordRunEnded` logs correct final day); death/respawn inventory restore with 2+ simultaneous deaths (join-order indexing assumption not yet validated under real multiplayer timing).

[x] 6.2 Data Struct Serialization

Ensure all dynamic structures (FItemData, inventory arrays, socket occupancy states, store advertisement level) implement proper serialization interfaces so runs can be safely loaded or resumed if needed.

- `BP_ShelfActor`: new `ShelfSaveID` Name var (server-only, not replicated; authorable, falls back to a deterministic rounded-world-location string like `Shelf_<X>_<Y>_<Z>` when unset) plus `GetShelfSaveID`, `GetShelfSaveState` (packs `StockedItems` into `S_SaveShelfState`), and `RestoreShelfState` (HasAuthority-gated; sanitizes each `S_ItemSlot` against `DT_Items` row validity/`Quantity>0`, resizes to `SlotTransforms.Length`, rebuilds display meshes). Duplicate `ShelfSaveID`s across shelves are detected and the second occurrence is dropped with a warning rather than silently colliding.
- `BP_GameInstance_NoBrainers`: new `GatherShelfStates`/`ApplyShelfStates` functions wired into the existing `GatherSessionState`/`ApplySessionState` so `S_SaveSession.ShelfStates` is now actually populated and restored (was declared-but-unused after 6.1).
- Payload audit: confirmed zero object references (`UStaticMesh*`/`UTexture2D*`) are reachable anywhere in the save chain — the `S_ItemData`-never-serialized rule from 6.1 already covers everything; no further item-serialization work needed. `BP_ShippingCrate` deliberately excluded (crates are always empty at every save point, nothing to persist).
- `BP_GameMode_ZombieStore`: new default-off `bResumeSessionOnStart` opt-in bool; if true and a session save exists, `BeginPlay` loads it after a 1-frame delay instead of always starting fresh. Off by default, so current PIE behavior is unchanged unless explicitly enabled.
- Task 2.1 hold respected. Compiled clean (0 errors; 1 pre-existing unrelated cosmetic warning on `BP_ShelfActor`'s `GetShelfSaveID`, a generic Break Vector node), vesper-laid-out, all touched assets saved.
- **Needs manual testing (not yet done):** place a few `BP_ShelfActor`s, stock them, save/reload and confirm stock restores (incl. fallback-ID stability if a shelf is moved between save and load); force two shelves to share a `ShelfSaveID` and confirm the duplicate-warning/drop path; toggle `bResumeSessionOnStart` true vs. false and confirm the load-on-start behavior differs as expected; confirm `RestoreShelfState`'s authority gate (no-op on clients).

Acceptance Criteria

Customer spawning uses distinct archetypes (Normal, Rich, Cheap, Fighter, Nurse, Scavenger, Trinket Collector) that filter shelves based on price tolerance and item categories.

Every 3 to 6 days, a CustomerEvent triggers, broadcasting a HUD event and flooding the store with a specific customer type.

Shelf-stocking matching logic applies price and buy-probability multipliers to adjacent identical/category items.

Players can stock shelves manually (or use the Shipping Crate fallback) to turn zombie drops into store revenue.

Store revenue is spent at the Employee Discount Kiosk to buy player gear, store upgrades, and defenses.

