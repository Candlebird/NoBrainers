# No Brainers — Project Reference

Quick-lookup index for the codebase. See `docs/GDD.md` for design intent. This
doc covers *what actually exists in the repo* as of 2026-09-16 — verify
against source before relying on specifics, since the project is actively
being converted from its GASDocumentation starting point into No Brainers.

## Implementation Preference

New gameplay content should default to **Blueprint**, subclassing the existing
C++ base classes (`AGDMinionCharacter`, `AGDCharacterBase`, etc.) rather than
adding new C++ classes. Reach for C++ only when there's a concrete technical
need (perf, engine-level hook, etc.) that Blueprint can't cover. See
`docs/GDD.md` §5.

## Origin & Identity

- The project is built directly on top of **Dan Kestranek's GASDocumentation**
  sample (Unreal's Gameplay Ability System reference project). The `.uproject`
  is still literally named `GASDocumentation.uproject`, the C++ module is
  `GASDocumentation`, and most class prefixes are still `GD*` (GASDocumentation).
  This is intentional per `docs/GDD.md` §5 — GAS's built-in replication support
  is why the project started here.
- Engine: **UE 5.7** (`EngineAssociation` in the `.uproject`).
- Recent history (see `git log`): started as the stock GAS sample/TPS →
  "Initial game files" → shop fixes + placeholder zombie → "Converting to FPS
  and adding test zombie" (current HEAD). The game is mid-conversion from the
  sample's third-person shooter to No Brainers' intended over-the-shoulder/FPS
  survival-horde-shooter + store-sim.

## Directory Map

```
Source/GASDocumentation/
  Public|Private/
    Characters/                  AGDCharacterBase and shared character code
      Abilities/                 GAS: AbilitySystemComponent, AttributeSet,
                                  GameplayAbility base, AbilityTasks, async tasks
      Heroes/                    AGDHeroCharacter (player/AI-controlled hero)
        Abilities/                GDGA_FireGun (C++ ability)
      Minions/                   AGDMinionCharacter (AI-controlled enemies)
    AI/                          GDHeroAIController
    Player/                      GDPlayerController, GDPlayerState
    UI/                          HUD/status-bar/damage-text widget C++
    GDBlueprintLibrary, GDEngineSubsystem, GSStatics   (project-wide statics)
    GASDocumentationGameMode

Content/
  GASDocumentation/
    Blueprints/                  BP-side gameplay (AnimNotifies, etc.)
    Characters/
      Hero/Abilities/            GA_* / GE_* / GC_* Blueprints per ability
                                  (AimDownSight, Dash, FireGun, Interact,
                                   Meteor, PassiveArmor, Sprint)
      Minions/                   BlueMinion, RedMinion (sample enemies),
                                  Zombie (mesh/material only so far — see below)
      Shared/                    GameplayCues, GE templates, targeting
    Environment/                 level meshes
    Maps/                        Map_Startup.umap (only map in the project)
    UI/                          HUD/menu textures
  FPWeapon/                      First-person gun mesh/materials/textures
                                  (added for the FPS conversion)
  Interactable/                  BP_Interaction_Base, BP_ShopStation_Base
                                  (the store-sim shop interaction system)
  AnimStarterPack/                UE4 mannequin anims + zombie skeletal mesh
                                  assets (Zombie_Standard, ZombieTest, etc.)
  ParagonMinions/                 FX assets carried over from the sample
```

## C++ Class Hierarchy (gameplay-relevant)

- `ACharacter` → **`AGDCharacterBase`** (`Characters/GDCharacterBase.h`)
  Base for every character with an AbilitySystemComponent. Not meant to be
  spawned directly — always subclassed. Owns:
  - `ShowHitReact` / `OnCharacterDied` multicast delegates
  - `IAbilitySystemInterface::GetAbilitySystemComponent()`
  - Attribute accessors (`GetHealth`, `GetMana`, `GetStamina`, `GetMoveSpeed`, …)
  - `CharacterAbilities` (default abilities granted/removed on
    death/respawn), `DefaultAttributes` GE, `StartupEffects`
  - `Die()` / `FinishDying()` death flow, `PlayHitReact` (NetMulticast)
  - `TWeakObjectPtr<UGDAbilitySystemComponent>` / `TWeakObjectPtr<UGDAttributeSetBase>`
    cached on the base rather than re-fetched — deliberate perf choice per
    the header's own comment.
  - `AGDCharacterBase` → **`AGDHeroCharacter`** (`Characters/Heroes/GDHeroCharacter.h`)
    Player/AI-controlled hero. Owns `CameraBoom` (SpringArm), `FollowCamera`,
    `GunComponent` (SkeletalMeshComponent — this is where `Content/FPWeapon`
    hooks in), floating status bar widget component, and the
    `BindASCInput()` / `OnRep_PlayerState()` dance needed because GAS input
    binding races against PlayerState replication (see the header comment on
    that race for context before touching player input setup).
    **Move/Look/Jump are no longer bound in C++.** The old
    `MoveAction`/`LookAction`/`JumpAction` properties and the
    `Move()`/`Look()` implementations (Enhanced Input bound in
    `SetupPlayerInputComponent`) were removed because that binding kept
    breaking; the equivalent logic (yaw-relative `AddMovementInput`,
    `AddControllerYawInput`/`AddControllerPitchInput` with mouse-look at 70%
    of raw sensitivity and both move-strafe and look-pitch axes inverted
    relative to the raw `IA_Move`/`IA_Look` values, `Jump()`/`StopJumping()`)
    now lives entirely in `BP_HeroCharacter`'s EventGraph via
    `IA_Move`/`IA_Look`/`IA_Jump` Enhanced Input event nodes.
    `SetupPlayerInputComponent` in C++ now only calls
    `Super::SetupPlayerInputComponent()` and `BindASCInput()` — GAS ability
    input binding is untouched. If movement/look ever needs to move back to
    C++, rebuild it from the BP graph in `BP_HeroCharacter`, not from git
    history, since the old C++ implementation is gone.
  - `AGDCharacterBase` → **`AGDMinionCharacter`** (`Characters/Minions/GDMinionCharacter.h`)
    AI-controlled enemy base. `BP_RedMinion` / `BP_BlueMinion` are the sample's
    concrete enemies; the zombie is intended to be a sibling of these (per GDD
    §4: "single shared base zombie class") but as of HEAD there is **no
    Zombie Blueprint yet** — only raw mesh/texture/material assets exist
    under `Content/GASDocumentation/Characters/Minions/Zombie/` and
    `Content/AnimStarterPack/UE4_Mannequin/Mesh/`. The "test zombie" commit
    added assets, not a wired-up character class — confirm current state with
    `project_query find_by_type Blueprint` / `search "Zombie"` before assuming
    otherwise.

- **GAS plumbing** (`Characters/Abilities/`):
  - `UGDAbilitySystemComponent` — project's ASC subclass
  - `UGDAttributeSetBase` — Health/Mana/Stamina/MoveSpeed etc.
  - `UGDGameplayAbility` — base ability class; `GDGA_CharacterJump`,
    `Heroes/Abilities/GDGA_FireGun` are C++ concrete abilities
  - `GDDamageExecCalculation` — damage MMC
  - `AbilityTasks/GDAT_PlayMontageAndWaitForEvent`, `GDAT_WaitReceiveDamage`
  - `AsyncTaskAttributeChanged` / `AsyncTaskCooldownChanged` /
    `AsyncTaskEffectStackChanged` — BP-facing async listeners for
    attribute/cooldown/effect-stack changes

- **Player:** `GDPlayerController`, `GDPlayerState` (`Source/.../Player/`)
- **AI:** `GDHeroAIController` (`Source/.../AI/`) — drives AI-controlled heroes/minions
- **UI (C++ side):** `GDHUDWidget`, `GDFloatingStatusBarWidget`,
  `GDDamageTextWidgetComponent` (`Source/.../UI/`)
- **Misc statics:** `GDBlueprintLibrary`, `GSStatics`, `GDEngineSubsystem`

## Blueprint-side Gameplay Abilities

Each ability generally has a `GA_*` (GameplayAbility BP), optional `GE_*`
(GameplayEffect, cost/cooldown/damage), and optional `GC_*` (GameplayCue),
all under `Content/GASDocumentation/Characters/Hero/Abilities/<AbilityName>/`:

| Ability | Assets |
|---|---|
| AimDownSight | `GA_AimDownSight_BP` |
| Dash | `GA_Dash_BP`, `GE_DashCost` |
| FireGun | `GA_FireGun`, `GA_FireRifle`, `BP_GunProjectile`, `BP_RifleProjectile`, `GE_GunDamage`, `GC_FireGunImpact` |
| Interact | `GA_Interact` — this is the hook into the store-sim shop system |
| Meteor | `GA_Meteor_BP`, `BP_Meteor`, `BP_MeteorTargetActor`, `GE_MeteorCooldown/Cost/Damage/Stun` — sample-game leftover, likely not part of No Brainers' final kit |
| PassiveArmor | `GA_PassiveArmor_BP`, `GE_PassiveArmor` |
| Sprint | `GA_Sprint_BP`, `GE_SprintCost`, `GC_Sprint` |
| Other | `GE_StartingStats` — the initial-attributes GE applied on spawn |

## Store-Sim / Interactable System

- `Content/Interactable/BP_Interaction_Base` — generic interactable base,
  driven by `GA_Interact`.
- **Interaction input already works via legacy input, not Enhanced Input —
  check this before building anything new.** `GA_Interact` is activated by
  the classic Action Mapping `"Interact"` (key **F**, defined in
  `Config/DefaultInput.ini`), routed through `EGDAbilityInputID::Interact`
  (`Source/GASDocumentation/GASDocumentation.h`) and
  `AGDHeroCharacter::BindASCInput()`'s `BindAbilityActivationToInputComponent`
  call (`Source/GASDocumentation/Private/Characters/Heroes/GDHeroCharacter.cpp`).
  This is the mechanism the player already uses today to pick up items /
  interact with the world — it predates and has nothing to do with Enhanced
  Input. An `IA_Interact` Enhanced Input action asset exists but, as of this
  writing, nothing consumes it — don't assume interaction is unbuilt just
  because `IA_Interact`/`IMC_Default` isn't wired to anything. Before adding
  new interaction (or any ability-trigger) input, check
  `Config/DefaultInput.ini` ActionMappings, `EGDAbilityInputID`
  (`GASDocumentation.h`), and `AGDCharacterBase`/`AGDHeroCharacter`'s
  GAS input-binding first — it's likely already wired via the legacy path.
- `Content/Interactable/BP_ShopStation_Base` — the shop/restock interaction
  from the GDD's day-loop ("Customers buy items → money → buy weapons/ammo/
  defenses"). This is the only shop-specific Blueprint that exists so far;
  no separate customer AI, shelf, or economy Blueprints were found as of
  this writing — check `project_query search "Shop"` for anything newer.

## Maps

- `Content/GASDocumentation/Maps/Map_Startup.umap` is the **only** map in
  the project. There is no separate "store" level yet — day/night wave
  structure from the GDD is not yet reflected in level layout.

## Plugins

- **GameplayAbilities** (engine plugin, enabled) — the GAS foundation.
- **Monolith** (`Plugins/Monolith/`) — the MCP automation bridge used by
  Claude Code tooling in this repo (see root `CLAUDE.md`). Not a gameplay
  plugin.
- **VesperNodeCleaner** (`Plugins/VesperNodeCleaner/`) — paid Blueprint
  auto-layout plugin, used via `blueprint.auto_layout formatter: 'vesper'`.
- Engine plugins `Bridge` and `VisualStudioTools` are enabled; `MagicLeap*`
  and `AndroidFileServer` are present but disabled.

## Where to Look for Common Questions

- **"How does damage/health work?"** → `GDDamageExecCalculation` (MMC) +
  `UGDAttributeSetBase` + `GE_GunDamage`/`GE_MeteorDamage` as examples.
- **"How do I add a new ability?"** → copy the pattern of an existing
  `GA_*`/`GE_*`/`GC_*` triplet under `Characters/Hero/Abilities/`, grant it
  via `AGDCharacterBase::CharacterAbilities` or the character's default GE list.
- **"Where's the FPS camera/gun setup?"** → `AGDHeroCharacter` (`CameraBoom`,
  `FollowCamera`, `GunComponent`) + `Content/FPWeapon/`.
- **"Where's the zombie?"** → Not yet a real character class — only art
  assets exist (`Content/GASDocumentation/Characters/Minions/Zombie/`,
  `Content/AnimStarterPack/.../Zombie_Standard*`). Building it should likely
  subclass `AGDMinionCharacter` alongside `BP_RedMinion`/`BP_BlueMinion`.
- **"Where's the shop/store-sim logic?"** → `Content/Interactable/`
  (`BP_Interaction_Base`, `BP_ShopStation_Base`) + `GA_Interact`.
- **Stats/asset counts, dependency lookups, etc.** → use Monolith's
  `project_query` (`get_stats`, `search`, `find_by_type`, `find_references`)
  instead of manual file globbing — it's indexed and faster (287 assets, 57
  Blueprints as of this writing).

## Verifying This Doc

This snapshot was built from a live index (`project_query get_stats` /
`search` / `find_by_type`) plus reading the relevant headers directly. Since
the project is under active, rapid restructuring (FPS conversion, zombie
work in progress), re-run those Monolith queries rather than trusting counts
or "doesn't exist yet" claims here once significant time has passed.
