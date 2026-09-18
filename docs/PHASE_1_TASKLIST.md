Phase 1: Project Setup & Core Multiplayer Architecture
Technical Context
Engine Version: Unreal Engine 5.7.4

Perspective: First-Person

Architecture: Dedicated / Listen Server Model (RPCs, Variable Replication, Owner Relationships)

Goal: Establish a baseline networked framework for up to 4 players with a functional Day/Night state loop and spectating support.

Status: Complete. Verified against the live editor via Monolith — `BP_GameState_ZombieStore` and `BP_GameMode_ZombieStore` are Blueprint classes (extending `GameStateBase` and `BP_GDGameMode_C`/`AGASDocumentationGameMode` respectively) rather than the from-scratch native `AGameState_ZombieStore`/`AGameMode_ZombieStore` C++ classes this task list's task text names below — the project settled on Blueprint-first for this layer, with only the spectator controller (`ASpectatorController_ZombieStore`) implemented in C++. The task text below is left as originally written for traceability; treat "AGameState_ZombieStore"/"AGameMode_ZombieStore" as referring to those Blueprints.

Task Breakdown
0. Cleanup
[x] 0.1 Remove Blueprint Player Prototype

We're standardizing on the existing GASDocumentation `BP_HeroCharacter` (Content/GASDocumentation/Characters/Hero/) as the player character rather than a from-scratch Blueprint. The player character and its controller(s) will be implemented in C++ going forward.

Delete `Content/Characters/BP_Character_Player.uasset` and the now-unused `BP_Character_Player`-only Blueprint scaffolding.

Keep `Content/Characters/Input/` (IMC_Default, IA_Move, IA_Look, IA_Jump, IA_Interact, IA_PrimaryAction, IA_SecondaryAction) — these Enhanced Input assets are reused regardless of Player class implementation.

Search remaining Blueprints/levels for references to `BP_Character_Player` (e.g. GameMode default pawn class, PlayerStarts) and repoint them at `BP_HeroCharacter` before deleting.

1. Project Configuration & Directory Hierarchy
[x] 1.1 Directory Setup

Create folder architecture under /Content:

Core/ (GameModes, GameStates, PlayerControllers, GameInstances)

Characters/ (Player Base, Animations, Inputs)

UI/ (HUD, Widgets)

Environment/ (Store geometry, Master Materials)

Data/ (Data Tables, Structs, Enums)

[x] 1.2 Input System Configuration (Enhanced Input)

Create Input Context Mapping (IMC_Default).

Define Input Actions (IA_Move, IA_Look, IA_Jump, IA_Interact, IA_PrimaryAction, IA_SecondaryAction).

2. Core Game Loop & State Machine
[x] 2.1 Phase State Enum

Create EGamePhase enum: DayPhase, NightPhase, RunOver.

[x] 2.2 Game State Framework (AGameStateBase)

Create AGameState_ZombieStore derived from AGameStateBase.

Add replicated variable: EGamePhase CurrentPhase (Notify: OnRep_CurrentPhase).

Add replicated variable: float PhaseTimeRemaining.

Implement OnRep_CurrentPhase to broadcast event delegates for local client UI updates and world updates (ie Day Night cycle).

[x] 2.3 Game Mode Logic (AGameModeBase)

Create AGameMode_ZombieStore derived from AGameModeBase.

Implement Phase Timer loop:

StartDayPhase(): Sets CurrentPhase = EGamePhase::DayPhase, starts TimerHandle_Phase.

StartNightPhase(): Sets CurrentPhase = EGamePhase::NightPhase, starts TimerHandle_Phase.

Implement CheckRunOverCondition(): Count living players. If living count is 0 during NightPhase, trigger EndRun(bVictory = false).

3. Networked Player Character & Health System
[x] 3.1 Updating player respawn logic

Remove the default respawn timer that respawns players after death after 5 seconds. Set them to respawn only when the Day phase starts.

[x] 3.2 Player Death & Down State Logic

Use existing OnPlayerDeath() on BP_HeroCharacter (Server-side):

Disable collision and character movement.

Set replicated boolean bIsDead = true.

Call AGameMode_ZombieStore::OnPlayerDied(AController* DeadPlayer).

Switch AController view target to spectator logic.

Remove current destruction of player, as later on we will be implementing "picking up downed players" during the night cycle

4. Spectator & Respawn Loop
[x] 4.1 Spectator Controller Logic (APlayerController, C++)

Create ASpectatorController_ZombieStore in C++.

Implement Client RPC Client_EnterSpectatorMode() triggered on death:

Cycle through array of surviving BP_HeroCharacter actors on primary input (IA_PrimaryAction).

Set camera view target (SetViewTargetWithBlend) to active teammate.

[x] 4.2 Day Phase Respawn Cycle

In AGameMode_ZombieStore::StartDayPhase():

Respawn dead players at designated player starts (TargetTransform).

Reset CurrentHealth to MaxHealth and set bIsDead = false.

Re-bind movement inputs and restore default player camera view target.

Acceptance Criteria
Host can launch a listen server and up to 3 clients can join the session.

The server successfully transitions between Day and Night phases on a timer, replicating state changes to all clients.

If a player takes fatal damage, they enter a dead state, lose movement, and can cycle camera targets between surviving players.

Surviving players entering the Day phase automatically triggers dead players to respawn safely at spawn points.

If all players die during the Night phase, the server transitions the state to RunOver.