Here is the breakdown for Phase 2: Day Phase \& Retail Loop, structured as a standalone technical Markdown document for Phase\_2\_Day\_Phase\_and\_Retail\_Loop.md.



Phase 2: Day Phase \& Retail Loop

Technical Context

Engine Version: Unreal Engine 5.7.4



Perspective: First-Person



Architecture: Server-authoritative inventory, shelf management, and economy system with RPC updates to clients.



Goal: Implement the complete daytime retail gameplay loop, including item data structures, inventory management, interactive shelf stocking with matching-bonus logic, customer AI (with fallback automated selling), and the employee discount shop.



Task Breakdown

1\. Data Architecture \& Inventory System

\[ ] 1.1 Item Data Definition (FItemData Struct \& Data Table)



Create FItemData struct (USTRUCT):



FName ItemID



FText DisplayName



EItemCategory Category (e.g., Food, Ammo, Electronics, Hardware)



int32 BaseSellPrice



int32 DiscountCost (Employee purchase price)



float DropWeight (For zombie death loot tables)



UStaticMesh\* DisplayMesh



UTexture2D\* Icon



Create Data Table DT\_Items populated with initial zombie drops and buyable items.



\[ ] 1.2 Inventory Component (UInventoryComponent)



Create UInventoryComponent attached to ACharacter\_Player:



Replicated array: TArray InventorySlots.



Server RPCs: Server\_AddItem(), Server\_RemoveItem(), Server\_DropItem().



Delegates for UI updates: OnInventoryUpdated.



\[ ] 1.3 World Pickup Actor (AItemPickup)



Create interactable item actor in world space (IInteractableInterface):



Holds FItemData or ItemID.



Outline/highlight shader when targeted by first-person interaction trace.



Server-validated pickup logic transferring item to player inventory.



2\. Shelf Stocking \& Matching Minigame

\[ ] 2.1 First-Person Interaction Raycast



Implement line-trace in ACharacter\_Player mapped to IA\_Interact.



Highlight targeted IInteractableInterface actors (Pickups, Shelves, Cash Registers, Traps).



\[ ] 2.2 Shelf Actor Architecture (AShelfActor)



Create AShelfActor:



Configurable array of FShelfSlot transforms (e.g., Grid of 2x3 or 3x4 slots per shelf).



Replicated array: TArray StockedItems.



Spawn/attach static meshes (DisplayMesh) at designated slot transforms upon item placement.



\[ ] 2.3 Adjacent Matching Logic (UShelfMatchingComponent)



Implement matching evaluation on item placement/removal:



Check if placed item shares ItemID or EItemCategory with adjacent slots on the same shelf.



Apply bonus modifiers:



2 Matched: +25% Sell Price / Customer Buy Probability.



3+ Matched (Full Row): +50% Sell Price / Customer Buy Probability.



Replicate slot bonus multipliers to client UI.



3\. Customer AI \& Economy System

\[ ] 3.1 NPC Customer AI Framework



Create ACustomerCharacter derived from ACharacter.



AI Controller using Behavior Tree (BT\_Customer):



State 1: Walk from Store Entrance to a stocked AShelfActor.



State 2: Evaluate shelf items (higher pick chance for matched sets). Select item and remove from shelf.



State 3: Navigate to Register/Checkout counter, deposit money into AGameState\_ZombieStore::StoreCash, and exit store.



\[ ] 3.2 Customer Spawner Manager (ACustomerSpawner)



Spawns customer waves during DayPhase.



Scales spawn frequency based on StoreAdvertisementLevel.



\[ ] 3.3 Fallback Consignment / Shipping Crate (AShippingCrate)



Create AShippingCrate interactable actor (usable if NPC models/animations are disabled):



Players drop items directly into crate during day phase.



Automatically liquidates items at end of day phase, adding earnings directly to AGameState\_ZombieStore::StoreCash.



4\. Employee Discount Store \& Purchasing System

\[ ] 4.1 Shared Store Money Engine



Replicated variable in AGameState\_ZombieStore: int32 StoreCash.



Thread-safe transaction methods: Server\_AddCash(), Server\_DeductCash().



\[ ] 4.2 Employee Discount Kiosk UI (UUserWidget)



UI Kiosk interface displaying purchasable catalog:



Personal weapons and ammo.



Defense blueprints (Spike Traps, Turrets, Barricades).



Shelf expansion upgrades.



Marketing / Store Advertisements (Increases day foot traffic \& night zombie threat).



\[ ] 4.3 Purchase Execution Logic



Validate player cash reserves on server before completing purchase.



Deduct cost, update inventory or spawn item/blueprint in world.



Acceptance Criteria

Players can pick up physical item drops and manage them in their inventory.



Interacting with a shelf places an item on a designated slot and visually renders the static mesh.



Placing identical/matching category items adjacently correctly calculates and applies a profit/sale chance bonus.



NPC customers navigate to stocked shelves, pick items, deposit cash at checkout, and exit (or items placed in the Shipping Crate convert to cash at day's end).



Players can use the Employee Discount Store UI to spend earned cash on upgrades, gear, and defenses.

