# No Brainers — Parent Task List

This is the index for the phased build-out of No Brainers. Each phase has its own detailed
task breakdown in `docs/PHASE_<N>_TASKLIST.md`. Read this file first to know which phase is
active before opening a phase file — don't guess from git history or Content/ alone.

## Current Phase

**Phase 1: Project Setup & Core Multiplayer Architecture** — not yet started.

None of `PHASE_1_TASKLIST.md`'s checkboxes are checked, and the core framework classes it
calls for (`AGameState_ZombieStore`, `AGameMode_ZombieStore`, `ACharacter_Player`,
`UHealthComponent`, `APlayerController_ZombieStore`) don't exist in the project yet — the
project is still running on the stock GASDocumentation `BP_GDGameMode`. Work done so far
(FPS camera conversion, placeholder `BP_Zombie_Base` zombie) is prep/scratch work, not
credited against any phase's task list.

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
