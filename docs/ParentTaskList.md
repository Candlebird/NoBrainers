# No Brainers — Parent Task List

This is the index for the phased build-out of No Brainers. Each phase has its own detailed
task breakdown in `docs/PHASE_<N>_TASKLIST.md`. Read this file first to know which phase is
active before opening a phase file — don't guess from git history or Content/ alone.

## Current Phase

**Phase 4: Defense & Building Systems** — build work complete (tasks 1.1–4.1), untested
in PIE. Sockets/trace (1.1, 1.2), Build Mode toggle/menu with dispatcher binding and
confirm-placement input (2.1), blueprint unlock registry + kiosk integration (2.2), the
placement/repair/sell RPCs now callable end-to-end (2.3, 4.1), `BP_DefenseBase` (3.1), and
all 3.2 defense subclasses (Floor/Wall/TurretBase/Other, including Slow Strip's `GE_Slow`
GameplayEffect) are done and compile clean. Nothing left to build for this phase — next
step is a full PIE playtest pass (see `PHASE_4_TASKLIST.md` section 5 for the checklist).
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

Phases are meant to be tackled roughly in order (1 → 6), since later phases assume earlier
systems exist (e.g. Phase 4's defenses assume Phase 1's Day/Night state loop and Phase 2's
purchasing flow). Within a phase, sub-tasks can be parallelized across agents where they
don't share files.
