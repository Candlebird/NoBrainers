# Carry-One-Item Overhaul: User Decisions (2026-10-01)

These were collected in a 10-round Q&A before an overnight run. The user wrote them; they are authoritative.

## Why
The Day retail loop is the weakest part of the game: there's nothing to do while customers shop, and stocking is tedious. Keep the Day the same length but give it more activity. The overnight work should favor feel and polish.

## Core model
- **No internal inventory.** Players carry **one item at a time, held in their hands**. While carrying, they can't shoot; the weapon is hidden. The item's own pickup mesh is attached to the hands socket, with no new animation.
- **Pickup is press E** (Interact). There's no walk-over pickup.
- **E/Interact while carrying:**
  - Facing a shelf: place the item in that shelf's slot.
  - Anywhere else: set the item down at the player's feet.
- **Night loot drops stay on the floor** as world pickups. Players carry them to storage. Dusk cleanup still deletes loose items, except those inside storage.
- **Storage zone:** a trigger volume around the existing deposit box. Items inside it are safe from dusk cleanup. Don't hand-edit `Map_Store_Outdoors` (the user has made manual edits); give the user placement steps instead.
- **Remove the inventory UI and loot slots. Remove the Deep Pockets perk entirely, with no refund** of spent meta-currency.

## Throwing
- **Hold fire (left mouse) while carrying to charge the throw, and release to throw.** It uses a new Enhanced Input action in IMC_Default, never a hard-coded key.
- **Damage to zombies scales with the item's rarity and price.** Each zombie can be hit at most once per throw.
- **A throw only goes onto a shelf on a direct hit.** It then goes into the nearest empty slot on that shelf, and the shelf UI updates. Otherwise the item drops on the floor as a pickup.

## Shelves and economy
- Shelf slots go **2 / 4 / 6 / 8 / 12** through the **existing shelf upgrade system**, retuned rather than replaced.
- Items are about **1/3 as frequent** as drops, at about **3x the price**.
- **Customer spawn rate scales with the number of items stocked on shelves.**
- Checkout and customer behavior are unchanged.
- **Shelf combos and "fully matched" keep their rules, scaled to the current slot count.** A shelf is matched when all its current slots hold the same category.

## Follow-up decisions
- **Shelf E with empty hands:** tap E takes the item from the slot you're looking at, so players can re-arrange for combos. Hold E opens the existing shelf upgrade panel.
- **Throw damage by rarity:** Junk 10, Common 20, Uncommon 30, Rare 45, Treasure 60.
- **Dusk cleanup is strict:** it deletes every loose item outside the storage zone, indoors included.
- **Death or downed while carrying:** the held item drops at the player's feet as a world pickup.

## Priority if time runs out
1. Carry, place and storage zone, with the inventory removed.
2. Throwing.
3. Economy and rarity retune, plus customer scaling.

## Tests
Delete tests that cover removed features only. Add new tests only for the core new mechanics.
