# No Brainers — Parent Task List

This is the index for the phased build-out of No Brainers. Each phase has its own detailed
task breakdown in `docs/PHASE_<N>_TASKLIST.md`. Read this file first to know which phase is
active before opening a phase file — don't guess from git history or Content/ alone.

## Current Phase

**UPDATE (2026-09-30, Phase 12): Phase 12 (Combat Feel, Night 9 Victory, Endless & Bug Audit) is planned, waiting on the user's review before the overnight run.** See `docs/PHASE_12_TASKLIST.md`.
- The run is won by killing a 3-phase Final Boss on Night 9 (+300 meta bonus), then the team can cash out or continue into a ramping Endless mode.
- Zombie attacks land at the swing apex and can be dodged. Melee hits stagger zombies and show a goo splat and flash. New one-handed and two-handed player swing animations.
- New Sledgehammer and Katana, a Magnum buff, a Night 1 loot-tier leak fix, a death screen with spectate switching, and a BUGS.md audit.

**Phase 11 (Trap Unlocks, Daily Blueprint Shop & Trap Upgrades) is built.** See `docs/PHASE_11_TASKLIST.md`.
- Traps beyond Spike and Swinging are now meta-shop unlocks.
- In a run, the team buys trap blueprints from a shared 3-card daily shop at the Defense kiosk.
- Placed traps start at Junk and upgrade Junk → Treasure (×1.0 to ×2.0), with a tier glow from Common up. Weapons also start at Junk (Junk-start follow-up, 2026-09-30).
- Outside Build Mode, pressing E on a trap opens one panel for upgrade, repair and sell.
- In Build Mode, LMB places and RMB exits.
- Built unattended, so PIE testing is outstanding. Start with that file's "PIE test checklist".

**Phase 10 is done** (built and committed locally as 7b457f7). Its PIE testing is still outstanding, along with Phases 8 and 9.

**UPDATE (2026-09-30, Phase 10): Phase 10 (Weapon Tiers & Daily Weapon Shop) is built.** See `docs/PHASE_10_TASKLIST.md`. Weapons now use the 5 loot tiers:
- Stats are ×0.9 to ×1.3: damage, fire rate, magazine and reload for guns; damage and swing speed for melee.
- Weapons show a HUD tier label and a replicated tier glow.
- Zombies and elites drop tiered weapons, and the boss always drops one.
- The Weapons kiosk now opens a shared daily shop: 4 tiered weapons rolled each Morning, doubling paid rerolls, and meta-shop weapon unlocks.

Phases 8 and 9 are built and committed locally; their PIE testing is still outstanding.

**UPDATE (2026-09-30, later): Phase 9 (Tiered Meta Progression) is built and waiting on PIE testing.** See `docs/PHASE_9_TASKLIST.md`. Ten per-player tracks now have 9 tiers each at ×1.5 price per tier:
- Deep Pockets: 6 → 18 slots.
- Health, stamina, both regens and armor: +5% per tier.
- New fire-rate, weapon-damage, reload-speed and melee-damage multipliers, backed by 4 new C++ GAS attributes.

Everything is committed locally, not pushed. Start with that file's "PIE test checklist". Phase 8 PIE testing is also still outstanding.

**UPDATE (2026-09-30): Phase 8 (Loot Economy & Inventory) is built and waiting on PIE testing.** See `docs/PHASE_8_TASKLIST.md`. The overnight run built groups A–G: tiered loot with elite shift, soft pity, the Ad nudge and the boss piñata; a 6-slot loot cap with no stacking; the stockroom deposit box; tier glow, beams and prices; and the Deep Pockets and Scavenger perks. Tuning used `Tools/loot_sim.py`. All work is committed locally, not pushed. Start with that file's "Morning test checklist".

**UPDATE (2026-09-25): Phase 7 (Zombie Variety, Combat Depth & Balance) is active.** See `docs/PHASE_7_TASKLIST.md`. It covers reload bug fixes, 5 new zombie types with Blender animation sets, horde surges/flanking, an economy pass and game feel. The design was confirmed with the user in a Q&A; the overnight run works through it in the order A→F.

**UPDATE (2026-09-24):** A new game level, `/Game/Levels/Map_Store_Outdoors`, now exists. It's a Bass Pro-style hunting and outdoor superstore greybox of about 70×50 m. It has a vaulted clerestory nave, 3 checkouts, a central hub display, 6 breach entries, and defense sockets. The layout is authored in Python with the new LevelView toolkit (`Tools/LevelView/`, documented in `docs/LEVELVIEW.md`), then pushed into the editor and reviewed over 3 in-editor passes. The Main Menu's Start Run now opens it. `Test_Level_Zero` is untouched. **Needs in-PIE confirmation.** See the manual test list in `docs/LEVELVIEW.md` and the BUGS.md entry "Map_Store_Outdoors: scaled BP_BreachPoint wall panels unverified in PIE."

**UPDATE (2026-09-22):** Phase 5 work is active alongside Phase 4 (see below) — Tasks
1.1/1.2, 2.1/2.2, 3.x (save/load, meta-unlock gating), and the perk data model/application
pipeline (4.3's mechanical half) are built. **Two regressions surfaced from the user's own
overnight PIE testing, logged in `docs/BUGS.md`:** a starting-pistol spawn regression
(root-caused to this session's `OnASCReady` perk-application edit disconnecting the
pre-existing loadout-grant wire — **fixed**, needs in-PIE confirmation) and a "no zombies
spawn on entering night phase" regression (**fixed, needs in-PIE confirmation** — root cause
was a self-recursive Blueprint Getter/Setter accessor binding on 4 `BP_StoreEscalationComponent`
variables; fixed via a new Monolith action, `blueprint.set_variable_accessor`, that clears the
binding; see BUGS.md for detail). Both regressions are fixed; the Meta-Shop UI (Task 4.3's remaining half, **Option B — a real
Main Menu level**, user-approved) is now also built: `Map_MainMenu`, `BP_GameMode_MainMenu`,
`WBP_MainMenu`, `WBP_MetaShop`, and `WBP_MetaShopEntry` all landed, compile clean, and are
saved; `DefaultEngine.ini`'s default/editor startup maps now point at `Map_MainMenu`. Task 4.3
is checked off in `docs/PHASE_5_TASKLIST.md`. This doubles as the start of Phase 6 (Art, UI &
Audio) scope, since no Main Menu level/widget existed anywhere in the project before this.
Full detail (asset list, a Level Blueprint tooling gotcha worked around via GameMode BeginPlay,
and deliberately deferred scope — weapon/defense-blueprint shop tabs, co-op host/join,
post-run return-to-menu) is in `docs/BUGS.md`'s Meta-Shop UI entry (now RESOLVED) and
`docs/PHASE_5_TASKLIST.md`'s Task 4.3 STATUS NOTE. **Everything built this pass — both
regression fixes and the new Main Menu/Meta-Shop UI — still needs in-PIE confirmation**, which
is currently blocked on the user regaining PC access.

**Phase 4: Defense & Building Systems** — build work complete (tasks 1.1–4.1), untested
in PIE. Sockets/trace (1.1, 1.2), Build Mode toggle/menu with dispatcher binding and
confirm-placement input (2.1), blueprint unlock registry + kiosk integration (2.2), the
placement/repair/sell RPCs now callable end-to-end (2.3, 4.1), `BP_DefenseBase` (3.1), and
all 3.2 defense subclasses (Floor/Wall/TurretBase/Other, including Slow Strip's `GE_Slow`
GameplayEffect) are done and compile clean. An unplanned addition, the project HUD
(`WBP_HUD`, health/stamina/ammo readout — see 4.2), also landed and compiles clean.
After a first playtest pass, 4 more issues were reported and fixed overnight (see
`PHASE_4_TASKLIST.md` section 6): shop terminal interactability, shelf interactability
(shipped as click-to-transfer, not drag-and-drop — see section 6 for why), a 5-tier
upgradable-shelf system, and a zombie-count-based (not fixed-timer) night-phase end
condition. All landed and compile clean but are unverified in PIE.
**UPDATE (2026-09-22, overnight unattended session):** two more playtest-reported bugs
root-caused and fixed — Build Menu placement (`BP_BuildModeComponent`, three exec-pin/logic
fixes) and customers never spawning on Day phase (`BP_CustomerSpawner::GetMaxConcurrent`,
one exec-pin fix). Both are automation-verified (new tests `Test_BuildModePlacementRequest`
and `Test_CustomerSpawnerMaxConcurrent`, added to `Content/Tests/Automation`, both PASSING)
but still need real in-PIE manual confirmation, since the automation drives the underlying
functions directly rather than simulating real mouse/keyboard input or a real elapsed-time
phase loop. Committed locally (`8025153`), not pushed. Full detail in `docs/BUGS.md`. A
third, unrelated bug was discovered incidentally while running the full test-bed suite to
verify these fixes — `Test_Equipment_ReloadReplenishesMagazine` fails on a GAS tag-container
mismatch during reload — logged in `docs/BUGS.md` but deliberately left uninvestigated
(out of scope for this session).
Next step is a full PIE playtest pass (see `PHASE_4_TASKLIST.md` sections 5 and 6 for the checklists).
Read `docs/PHASE_4_TASKLIST.md` for full detail — its Status Notes under each item are the
authoritative record. Phase 3 (all tasks 1.1–6.2) and Phase 1 are complete.

**Stale-index note:** this section previously said "Phase 2: in progress, not yet
started" while Phase 2-shaped work (inventory/equipment foundation, ammo & reload,
save-game slot manager/session persistence, shelf-stock save/restore, `WBP_Inventory` UI)
was actually being built and landed under Phase 3's task list instead of being credited
back to `PHASE_2_TASKLIST.md`. Don't trust this file's phase label alone — cross-check
which `PHASE_<N>_TASKLIST.md` has the most recent `[x]`/Status-Note activity before
assuming where to resume.

Phase 1 (Day/Night state loop, player death/respawn cycle, spectator controller) is
complete and verified in the live editor: `BP_GameState_ZombieStore` and
`BP_GameMode_ZombieStore` (Blueprints subclassing `GameStateBase` and the
GASDocumentation `BP_GDGameMode_C` respectively) drive
`StartDayPhase`/`StartNightPhase`/`RespawnDeadPlayers`/`CheckRunOverCondition`, and
`ASpectatorController_ZombieStore` (C++) handles spectating a downed player's teammates.
Note the project settled on Blueprint-first for the GameState/GameMode layer rather than
the from-scratch native `AGameState_ZombieStore`/`AGameMode_ZombieStore` classes
`PHASE_1_TASKLIST.md`'s task text originally named — see that file's Status note.

Phase 2 (Day Phase & Retail Loop): `PHASE_2_TASKLIST.md`'s own checkboxes are not an
accurate record of what's built — reconcile against Phase 3's Status Notes (inventory,
equipment, ammo/reload, save/load) before treating Phase 2 as not-started.

Phase 3 (`PHASE_3_TASKLIST.md`): all tasks (1.1 through 6.2) are complete — inventory/equipment
foundation, holster/attachment, ammo & reload, fast-tracer raycast weapons, melee weapon
base + server-validated damage, zombie base character (health/navmesh), zombie AI
(behavior tree, spawner manager), the breach-point system (`BP_BreachPoint`; zombies
now path to and breach into the store via BT Priority 2), the zombie loot table
system (`DT_ZombieLoot`, drop-roll + spawn + body despawn wired into `BP_ZombieBase`
death), and weapon acquisition (6.2, resolved as starting loadout + weapon pickup:
`BP_EquipmentComponent` grants a starting loadout on spawn/respawn, and `BP_ItemPickup`
now routes `DT_Weapons`-rowed items to `Server_EquipItem` instead of the Phase 2
inventory path). Verified in PIE. Phase 3 is done; Phase 4 (Defense & Building Systems)
has not yet been started — see `PHASE_4_TASKLIST.md` if/when it exists, otherwise this
index should be updated first when picking up Phase 4.

**Before starting work in any phase, check that phase's own file for `[ ]` vs `[x]`
status and its Status Notes — they are the real source of truth; this index is a hint
that can go stale (as it just did).**

## Phase Overview

| Phase | Title | Goal |
|---|---|---|
| 1 | Project Setup & Core Multiplayer Architecture | Establish a baseline networked framework for up to 4 players with a functional Day/Night state loop and spectating support. |
| 2 | Day Phase & Retail Loop | Implement the complete daytime retail gameplay loop: item data structures, inventory management, interactive shelf stocking with matching-bonus logic, customer AI (with fallback automated selling), and the employee discount shop. |
| 3 | Night Phase & Zombie Horde | Implement the night-time survival gameplay loop: horde spawning scaled by store advertisements, breachable entry points, first-person gunplay/melee combat, and zombie loot drops. |
| 4 | Defense & Building Systems | Let players purchase defense blueprints during the day, preview placement in first-person with a snapping ghost mesh, build automated traps/turrets/barricades, and maintain/repair them as zombies attack. |
| 5 | Meta-Progression & Run Loop | Implement the end-to-end run loop (15–45 min target duration), escalation mechanics driven by store advertisements, victory/defeat scoring, and persistent meta-currency logic across playthroughs. |
| 6 | Art, UI & Audio | Implement all UI overlays and HUD elements, post-processing materials, cartoonish particle effects, and audio transitions between the cozy daytime retail loop and the silly horror night phase. |
| 7 | Zombie Variety, Combat Depth & Balance | Distinct zombie types with full animation sets, horde surges/flanking, weapon fixes and feel, and an economy/balance pass to stop kiting from being dominant. |
| 8 | Loot Economy & Inventory | Day-scaled tiered loot tables (elite shift, boss loot piñata, soft pity), visible item tiers and prices, no inventory stacking, a 6-slot loot cap, and a stockroom deposit box. Built 2026-09-30, needs PIE testing. |
| 9 | Tiered Meta Progression | 9-tier per-player meta perk tracks (Deep Pockets slots, health/stamina/regen/armor, fire rate, weapon/melee damage, reload speed) with ×1.5 per-tier pricing. Built 2026-09-30, needs PIE testing. |
| 10 | Weapon Tiers & Daily Weapon Shop | Weapons use the loot tiers (Junk ×0.9 to Treasure ×1.3 stats, HUD label, glow), tiered weapon drops, and a shared daily weapon shop: 1 primary, 2 secondary and 1 melee rolled each Morning from the players' meta weapon unlocks, with doubling paid rerolls. Built 2026-09-30, needs PIE testing. |
| 11 | Trap Unlocks, Daily Blueprint Shop & Trap Upgrades | Meta-shop trap unlocks, a shared 3-card daily blueprint shop for in-run ownership, per-trap tier upgrades (Junk → Treasure, ×1.0 to ×2.0, glow), an E trap panel for upgrade, repair and sell, and LMB-place / RMB-exit in Build Mode. Built 2026-09-30, needs PIE testing. |
| 12 | Combat Feel, Night 9 Victory, Endless & Bug Audit | Night 9 Final Boss victory (+300 meta), Continue/Cash Out into a ramping Endless mode, run summary screen, apex-timed zombie attacks, melee stagger and hit VFX, Blender 1H/2H swing animations, Sledgehammer and Katana, Magnum buff, Night 1 loot leak fix, death screen with spectate switching, and a BUGS.md audit. Planned 2026-09-30. |

Phases are meant to be tackled roughly in order (1 → 6), since later phases assume earlier
systems exist (e.g. Phase 4's defenses assume Phase 1's Day/Night state loop and Phase 2's
purchasing flow). Within a phase, sub-tasks can be parallelized across agents where they
don't share files.
