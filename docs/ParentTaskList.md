# No Brainers — Parent Task List

This is the index for the phased build-out of No Brainers. Each phase has its own detailed
task breakdown in `docs/PHASE_<N>_TASKLIST.md`. Read this file first to know which phase is
active before opening a phase file — don't guess from git history or Content/ alone.

## Current Phase

**Phase 2: Day Phase & Retail Loop** — not yet started. Phase 1 is complete.

Phase 1's Day/Night state loop, player death/respawn cycle, and spectator controller are all
built and verified in the live editor: `BP_GameState_ZombieStore` and `BP_GameMode_ZombieStore`
(Blueprints subclassing `GameStateBase` and the GASDocumentation `BP_GDGameMode_C` respectively)
drive `StartDayPhase`/`StartNightPhase`/`RespawnDeadPlayers`/`CheckRunOverCondition`, and
`ASpectatorController_ZombieStore` (C++) handles spectating a downed player's teammates. Note
the project settled on Blueprint-first for the GameState/GameMode layer rather than the
from-scratch native `AGameState_ZombieStore`/`AGameMode_ZombieStore` classes `PHASE_1_TASKLIST.md`'s
task text originally named — see that file's Status note.

None of `PHASE_2_TASKLIST.md`'s checkboxes are checked yet. The only related asset in the
project so far, `BP_ShopStation_Base`, is prep/scratch work, not credited against Phase 2.

**Before starting work in any phase, check that phase's own file for `[ ]` vs `[x]` status —
this section is a hint, not a substitute for the source of truth.**

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
