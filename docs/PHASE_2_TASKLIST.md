Phase 2: Day Phase & Retail Loop

Technical Context

Engine Version: Unreal Engine 5.7.4

Perspective: First-Person

Architecture: Server-authoritative inventory, shelf management, customer archetype behavior trees, dynamic customer event manager, and economy system with RPC updates to clients.

Goal: Implement the complete daytime retail gameplay loop, including item data structures, inventory management, interactive shelf stocking with matching-bonus logic, diverse customer archetypes, dynamic customer events, and the employee discount shop.

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

[ ] 3.1 Customer Archetype Enum & Data Structure (ECustomerType)

Define ECustomerType enum:

Normal: Buys all categories equally; standard price tolerance.

Rich: Buys items at higher price thresholds (higher profit margins).

Cheap: Only buys items priced low or heavily discounted.

Fighter: Priority buying logic targeting EItemCategory::Hardware and EItemCategory::Ammo.

Nurse: Priority buying logic targeting EItemCategory::Medical.

Scavenger: Priority buying logic targeting EItemCategory::Food.

TrinketCollector: Priority buying logic targeting EItemCategory::Trinkets.

Define FCustomerArchetypeData struct (Category preferences, Max Price Multiplier, Walk Speed, Mesh Variations).

[ ] 3.2 Customer AI Behavior Tree Integration

Extend ACustomerCharacter and Behavior Tree (BT_Customer):

Filter available AShelfActor targets based on ECustomerType category preferences.

Evaluate shelf prices against archetype price tolerance threshold before deciding to purchase.

Purchase selected item, proceed to checkout counter, deposit cash into AGameState_ZombieStore::StoreCash, and exit.

4. Daytime Spawner & Dynamic Customer Events

[ ] 4.1 Customer Spawner Engine (ACustomerSpawner)

Spawns customer waves during DayPhase.

Weighted random selection pool for standard daytime customer spawning.

Base spawn rate scales dynamically with StoreAdvertisementLevel.

[ ] 4.2 Dynamic Customer Event Manager (UCustomerEventManager)

Interval Trigger: Automatically schedules a CustomerEvent every randomized 3 to 6 days.

Event Execution:

Overrides default random spawn pool with a high-density wave of a specific target archetype (e.g., "Nurse Convention" day spawning 80% Nurses, or "Fighter Guild" day).

Notifies clients via HUD banner/event notification to allow players to pre-stock shelves strategically based on upcoming customer surges.

[ ] 4.3 Fallback Consignment / Shipping Crate (AShippingCrate)

Create AShippingCrate interactable actor (usable if NPC models/animations are disabled):

Liquidates items dropped into it at the end of the day phase, adding earnings directly to AGameState_ZombieStore::StoreCash.

5. Employee Discount Store & Purchasing System

[ ] 5.1 Shared Store Money Engine

Replicated variable in AGameState_ZombieStore: int32 StoreCash.

Thread-safe transaction methods: Server_AddCash(), Server_DeductCash().

[ ] 5.2 Employee Discount Kiosk UI (UUserWidget)

UI Kiosk interface displaying purchasable catalog:

Personal weapons and ammo.

Defense blueprints (Spike Traps, Turrets, Barricades).

Shelf expansion upgrades.

Marketing / Store Advertisements (Increases day foot traffic & night zombie threat).

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

