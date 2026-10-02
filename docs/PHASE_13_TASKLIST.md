# Phase 13: Tutorialization & Onboarding

**Goal.** Teach new players the store, defense, kiosk and phase systems in play, without slowing down experienced players. Adds a one-goal HUD checklist, phase banners with explanations, a How to Play codex, first-visit meta-shop hints, tutorial settings, a free first Spike Trap each run, and an interact-prompt audit.

**Status (2026-10-01).** Built. All 19 tasks landed. Data, Economy and Defense suites pass (123/123). PIE checklist below is pending a user playtest.

## Design decisions (confirmed with the user)

1. **Checklist card.** A HUD corner card shows one goal at a time, and only while that goal can be done in the current phase. On completion a checkmark flashes for about 1 s with a quiet confirm sound, then the next goal slides in. Each goal is learned once, ever, per profile. When all goals are learned the card never shows again. The card is hidden at Night.
2. **Checklist scope.** Store: stock a shelf, make a sale, shelf combos, fully matched shelf. Defenses: place a trap in Build Mode, manage a trap with Interact, doors, buy a trap blueprint. Kiosks: buy a weapon, weapon tiers and glow, reroll, buy ammo. Combat is covered by the codex only.
3. **Meta-shop hints.** Two hints show the first time the player opens the meta shop with currency, after their first run has ended.
4. **Co-op.** Each player's checklist is driven only by their own actions and their own saved progress. Progress is stored in the local meta save.
5. **Phase banners.** Every phase change shows the phase name. An explanation line also shows until the player has seen that phase twice (per profile). Banners reuse WBP_EventBanner.
6. **Tone.** Plain instructional text, no jokes.
7. **Codex.** Topic list on the left (Store, Defenses, Kiosks, Phases, Combat, Meta), text on the right. Opens from the pause menu (Options > Tutorial > How to Play) and from How to Play on the main menu. Driven by DT_CodexEntries.
8. **Settings.** Options gets a Tutorial tab with a "Tutorial hints" toggle and a "Reset tutorial progress" button (two-press confirm). Reset clears learned goals, phase-seen counts and meta hints. It keeps the toggle.
9. **Free Spike.** Each player's first Spike Trap placement in a run costs $0. Build Mode shows "FREE" and the HUD shows a "Free Spike Trap x1" pill until it is used. It never expires and can't be transferred. Selling it refunds 50% of the normal Spike price. Per player, server-authoritative, replicated. Usable at Day 1 Dusk.
10. **Interact prompts.** Every interactable shows its prompt with the Interact action's current key. No hard-coded keys.
11. **Done means tested.** Automation tests cover checklist progression, the per-player save, free spike cost and refund, and the hints toggle and reset.
12. **Confirm sound.** SFX_UI_TutorialConfirm: a quiet, single low-mid tone. Not cute.

## Architecture

- **Save.** S_SaveMeta fields LearnedTutorialGoals (Array<Name>), PhaseSeenCounts (Map<Name,int>), bMetaHintsShown, bTutorialHintsDisabled. Every Break→Make S_SaveMeta in BP_GameInstance_NoBrainers must pass these through.
- **GameInstance API.** IsTutorialGoalLearned, MarkTutorialGoalLearned, GetPhaseSeenCount, IncrementPhaseSeen, AreMetaHintsShown, MarkMetaHintsShown, HasCompletedAnyRun, AreTutorialHintsEnabled, SetTutorialHintsEnabled, ResetTutorialProgress. Dispatchers OnTutorialHintsChanged and OnTutorialProgressReset.
- **BP_TutorialComponent** (on the PC, local controller only). Owns WBP_TutorialChecklist, picks the next goal (lowest Order among goals that are unlearned, allowed in the current phase, and have their prerequisite learned), plays the completion, shows phase banners, and polls for the sale goal, the timed goal and the free-spike pill.
- **Goal credit.** Server handlers on the acting player's PC call Client_TutorialGoalCompleted(GoalID) (owning client, reliable). Opening the trap panel credits locally. Store_Sale is credited when TotalCashEarned rises during Day while it is the active goal. Kiosk_Tiers completes after 8 s on screen.
- **Free spike.** BP_PlayerState_ZombieStore.bFreeSpikeAvailable (RepNotify, Owner Only, default true). The server placement handler skips the afford and deduct steps for SpikeTrap while it is set, and keeps TotalSpent at the normal Cost.

## Checklist goals (DT_TutorialGoals)

| Row | Order | Section | Phases | Prereq | Text |
|---|---|---|---|---|---|
| Def_PlaceTrap | 10 | Defenses | Morning, Day, Dusk | none | Press {Key} to open Build Mode and place a Spike Trap on a trap socket. Your first Spike Trap each run is free. |
| Def_ManageTrap | 20 | Defenses | Morning, Day, Dusk | Def_PlaceTrap | Look at one of your traps and press {Key} to upgrade, repair, or sell it. |
| Def_Door | 30 | Defenses | Morning, Day, Dusk | none | Look at a door and press {Key} to open or close it. Hold {Key} to repair a damaged door. |
| Store_Stock | 40 | Store | Morning, Day | none | Look at a shelf and press {Key} to stock it with items from your inventory. |
| Store_Sale | 50 | Store | Day | Store_Stock | Wait for a customer to buy something from your shelves. |
| Store_Combo | 60 | Store | Morning, Day | Store_Stock | Put items of the same category next to each other on a shelf. Groups of 2 or more sell for more. |
| Store_Match | 70 | Store | Morning, Day | Store_Combo | Build a group of 5 same-category items on one shelf to fully match it. Fully matched shelves raise your end-of-run payout. |
| Def_BuyBlueprint | 80 | Defenses | Morning, Day, Dusk | Def_PlaceTrap | Buy a trap blueprint at the Defense kiosk. Owned blueprints can be placed in Build Mode. |
| Kiosk_BuyWeapon | 90 | Kiosks | Morning, Day, Dusk | none | Buy a weapon at the weapon kiosk. Its stock changes every Morning. |
| Kiosk_Tiers | 100 | Kiosks | Morning, Day, Dusk | Kiosk_BuyWeapon | Weapons and traps come in tiers from Junk upward. Common and higher tiers glow, and the glow color shows the tier. (timed, 8 s) |
| Kiosk_Reroll | 110 | Kiosks | Morning, Day, Dusk | Kiosk_BuyWeapon | Reroll a kiosk to get new stock. Each reroll costs more until the next Morning. |
| Kiosk_BuyAmmo | 120 | Kiosks | Morning, Day, Dusk | none | Buy ammo at the ammo kiosk. |

{Key} is replaced with the current binding: Def_PlaceTrap uses IA_ToggleBuildMode; Def_ManageTrap, Def_Door and Store_Stock use IA_Interact. "(timed, 8 s)" is a note and is not part of the text.

## Phase banners (DT_PhaseBanners)

| Row | Title | Explanation |
|---|---|---|
| Morning | Morning | No zombies and no customers. Stock shelves, build traps and repair before the store opens. |
| Day | Day | Customers shop for stocked items. Keep shelves full to earn money. |
| Dusk | Dusk | The store is closed. Last chance to build and repair before Night. |
| Night | Night | Zombies attack until the timer runs out. Defend the store and collect their drops. |

Banners show for 4 s. The explanation shows while the phase-seen count is below 2 and hints are on.

## Codex entries (DT_CodexEntries, in display order)

| Row | Topic | Order | Title | Body |
|---|---|---|---|---|
| Store_01 | Store | 10 | Stocking shelves | Items you loot from zombies go into your inventory. Look at a shelf and press the Interact key to place items on it. Each shelf has a fixed number of slots. |
| Store_02 | Store | 20 | Customers | Customers arrive during the Day phase and buy stocked items. Sales add money to the shared store cash, which the whole team spends. There is no Day phase on Day 1, so the first customers come on Day 2. |
| Store_03 | Store | 30 | Shelf combos | Items of the same category placed next to each other on a shelf form a group. Groups of 2 sell for 25% more, groups of 3 or 4 for 50% more, and groups of 5 or more for 75% more. |
| Store_04 | Store | 40 | Fully matched shelves | A shelf is fully matched when its largest same-category group reaches 5 items, or fills every slot on a shelf with fewer than 5 slots. Fully matched shelves raise your meta currency payout at the end of the run. |
| Def_01 | Defenses | 10 | Trap blueprints | The team must own a trap's blueprint before anyone can place it. Spike and Swinging traps are owned at the start of every run. Buy other blueprints at the Defense kiosk. |
| Def_02 | Defenses | 20 | Placing traps | Open Build Mode with the Build Mode key, aim at a trap socket, and left click to place. Right click exits Build Mode. You cannot fire or aim weapons in Build Mode. Traps can be placed in Morning, Day and Dusk. Each player's first Spike Trap in a run is free. |
| Def_03 | Defenses | 30 | Managing traps | Outside Build Mode, look at a placed trap and press the Interact key to open its panel. Upgrade raises its tier. Repair restores health and works in any phase. Sell refunds 50% of everything spent on the trap. Upgrade and Sell are closed at Night. |
| Def_04 | Defenses | 40 | Doors | Press the Interact key on a door to open or close it in any phase. An open door cannot be damaged, but zombies walk straight through it. Hold the Interact key to repair a damaged door in Morning, Day or Dusk. A broken door cannot be closed until it is repaired. |
| Kiosk_01 | Kiosks | 10 | Weapon kiosk | The weapon kiosk sells 4 weapons each day, rolled every Morning. Stock is shared by the team and paid from store cash. It is closed at Night. |
| Kiosk_02 | Kiosks | 20 | Defense kiosk | The Defense kiosk sells 3 trap blueprints each day, rolled every Morning. Stock is shared and paid from store cash. It is closed at Night. |
| Kiosk_03 | Kiosks | 30 | Rerolls | Both kiosks can be rerolled for new stock. The first reroll costs $50, and the price doubles with each reroll until the next Morning. |
| Kiosk_04 | Kiosks | 40 | Ammo | Buy ammo at the ammo kiosk. |
| Kiosk_05 | Kiosks | 50 | Tiers | Weapons and traps come in 5 tiers: Junk, Common, Uncommon, Rare and Treasure. Higher tiers are stronger. Common and higher tiers glow, and the glow color shows the tier. Everything starts at Junk, and placed traps can be upgraded. |
| Phase_01 | Phases | 10 | The day cycle | Each day runs Night, Morning, Day, Dusk, then Night again. A new run starts at Dusk of Day 1. |
| Phase_02 | Phases | 20 | Night | Zombies attack until the timer runs out. Defend the store and collect their drops. Zombies that survive the night stay in the store. |
| Phase_03 | Phases | 30 | Morning | No zombies and no customers. Stock shelves, build traps and repair before the store opens. |
| Phase_04 | Phases | 40 | Day | Customers shop for stocked items. Keep shelves full to earn money. |
| Phase_05 | Phases | 50 | Dusk | The store is closed. Last chance to build and repair before Night. |
| Phase_06 | Phases | 60 | Winning | Night 9 has no timer. It ends when the team defeats the Final Boss, which wins the run. The host then chooses to cash out or continue into Endless, where each night gets harder. |
| Combat_01 | Combat | 10 | Fighting | Zombies deal damage at the end of their swing, so stepping back can dodge an attack. Your melee hits briefly stagger most zombies. |
| Combat_02 | Combat | 20 | Drops | Killed zombies drop items. Pick them up and stock them on shelves. Elites and bosses can drop weapons. |
| Combat_03 | Combat | 30 | Bosses and defeat | The Swamp boss attacks on Nights 3 and 6, and the Final Boss on Night 9. If every player is down, the run ends, in any phase. |
| Meta_01 | Meta | 10 | Meta currency | At the end of every run, win or lose, you earn meta currency. The amount depends on store cash earned, days survived, zombie kills and shelves fully matched. |
| Meta_02 | Meta | 20 | Unlocks | Spend meta currency in the meta shop on the main menu. Weapons, trap blueprints and perks you unlock are permanent and available in every future run. Most perks have 9 tiers. |

## Meta-shop hints

1. Meta currency is earned at the end of every run, win or lose. Spend it here to unlock new weapons, trap blueprints and perks.
2. Unlocks are permanent and carry over to every future run.

## Tasks

### Data and save
- [x] T1 S_SaveMeta tutorial fields
- [x] T2 Tutorial data: S_TutorialGoal / DT_TutorialGoals, S_PhaseBannerText / DT_PhaseBanners, S_CodexEntry / DT_CodexEntries
- [x] T9 GameInstance tutorial API, with S_SaveMeta pass-through in every Break→Make

### Audio
- [x] T3 SFX_UI_TutorialConfirm (SC_UI, volume 0.35)

### Free Spike
- [x] T4 PlayerState bFreeSpikeAvailable + OnFreeSpikeChanged
- [x] T11 WBP_BuildMenu shows FREE
- [x] T16 PC: server free-spike placement, client afford bypass

### Checklist and banners
- [x] T5 WBP_TutorialChecklist
- [x] T6 WBP_EventBanner ShowPhaseBanner
- [x] T12 BP_TutorialComponent
- [x] T16 PC: TutorialComponent, Client_TutorialGoalCompleted, defense and door hooks
- [x] T17 PC: store and kiosk hooks

### Codex, settings, meta hints
- [x] T10 WBP_Codex
- [x] T13 WBP_OptionsMenu Tutorial tab
- [x] T14 WBP_MainMenu How to Play
- [x] T15 WBP_MetaShop first-visit hints

### Interact prompts
- [x] T7 WBP_HUD "[Key] Verb" for interactables
- [x] T8 Interactable verb audit
- [x] T16 PC door and repair prompts show the key

### Tests
- [x] T18 Test_Tutorial_HintsToggle, Test_Tutorial_ResetProgress, Test_Tutorial_PhaseSeenCount (Data); Test_Tutorial_SaveRoundTrip, Test_Tutorial_GoalProgression (Economy)
- [x] T19 Test_FreeSpike_PlacementCostsZero, Test_FreeSpike_SellRefundsHalfNormal, Test_FreeSpike_OncePerPlayer (Defense); RunSuite clears the free-spike flag at suite start

## Status notes

- Running the automation suites in PIE marks some goals learned in your own meta save. Use Options > Tutorial > Reset tutorial progress before playtesting the tutorial.
- See docs/BUGS.md — "Free Spike re-granted on rejoin or session resume."
- Visual items that could not be verified headlessly; check them in PIE:
  - WBP_TutorialChecklist: the card's Fill slot and the checkmark position.
  - WBP_MetaShop: EntriesScrollBox may have lost its Fill slot when Border_MetaHints was inserted, and the hint border's amber tint is unconfirmed.
  - WBP_OptionsMenu: spacing on the Tutorial tab.
  - WBP_EventBanner: phase banners use white text on dark blue; event and surge banners keep the cream text.
- T16: TryPlaceSelectedDefense has no client-side afford check, so a client afford bypass was not needed. The server free-spike branch is enough.
- T17: Server_BuyBlueprintShopSlot and Server_RerollBlueprintShop had no success branch, so a Branch on bSuccess was added to each before the goal call.
- Ammo refill pickups have no interact prompt by design: they are walk-over pickups.

## PIE test checklist

1. **Fresh start.** Options > Tutorial > Reset tutorial progress (click twice). Start a new run. At Day 1 Dusk, the Dusk banner shows its name and explanation, and the card shows "Defenses" / "Press [your Build Mode key] to open Build Mode and place a Spike Trap...". The "Free Spike Trap x1" pill is visible.
2. **Card look.** The card sits on the right edge, a third of the way down, and never blocks clicks or aiming. It slides in from the right.
3. **Completion.** Place the Spike: no cash is taken, the check flashes for about 1 s, the confirm sound plays (quiet, not cute), and the next goal slides in. Open the trap panel with Interact: Def_ManageTrap completes. Toggle a door: Def_Door completes. Later, verify stock, sale, combo, match, blueprint, weapon, reroll and ammo goals each complete on their action.
4. **Night.** The card hides at Night. The Night banner shows its explanation the first two times you see Night, then only the name. An event banner arriving during a phase banner shows after it.
5. **Build menu.** Before using the free spike, the Spike entry shows "FREE" even with low store cash. After placing it, the normal price returns and the pill disappears.
6. **Sell refund.** Sell the free Spike: you get $30 (50% of 60).
7. **Settings.** Turn Tutorial hints off: the card and phase explanations disappear, the pill stays. Turn them on again: the card returns. Pause > Options > Tutorial > How to Play opens the codex; Tab, Esc or Interact closes it and returns to Options without closing Options.
8. **Main menu codex.** How to Play on the main menu opens the codex. All 6 topics show their text, and close keys work.
9. **Second run.** Start a second run: the free spike is available again.
10. **Reset.** Reset tutorial progress mid-run: the first unlearned goal reappears and phase explanations show again.
11. **Meta-shop hints.** After a run ends with meta currency earned, open the meta shop: both hints show. Reopen it: they don't.
12. **Co-op (2 clients).** Client B placing a trap does not complete Client A's goal. Each player has their own free spike and pill. Each player's progress persists on their own machine.
13. **Prompts.** Every interactable, door, breach point and trap shows "[key] verb". Rebind Interact in Options and every prompt updates.
