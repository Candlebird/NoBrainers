# Automation Test Suites

The automation test bed is split into **suites**. Each suite runs in its own map and its own PIE session, so a test that changes shared state (kills the hero, sets a spectator flag, drains cash) can't break tests in other suites.

## Suites

| Suite | Map (`/Game/Tests/Automation/Maps/`) | Tests (top-level + chained) | SettleSeconds | run_pie_smoke `duration` | Covers |
|---|---|---|---|---|---|
| Data | `L_Test_Data` | 44 + 0 | 3 | 20 | Pure data, settings, audio, net-string checks, tutorial hint settings, zombie attack ranges, ammo category mapping; no world interaction |
| Economy | `L_Test_Economy` | 47 + 0 | 5 | 25 | Loot, meta progression, weapon tiers, weapon and blueprint shops, save round-trips, tutorial progress, event min-day gate, heavy-ammo kiosk |
| Defense | `L_Test_Defense` | 33 + 0 | 15 | 35 | Build mode, breach points, repair, doors, traps, trap upgrades, free first Spike |
| Player | `L_Test_Player` | 24 + 2 | 25 | 45 | Hero spawn/move, phases, equipment, bloom, reload chain, ammo refill pickup |
| Retail | `L_Test_Retail` | 24 + 2 | 45 | 65 | Shelves, crates, customers, checkout ready-gate, dusk settle-and-leave, inventory, deposit box |
| Zombie | `L_Test_Zombie` | 21 + 1 | 45 | 65 | Zombie AI, spawner, damage, melee, melee friendly fire / one hit per swing, brute; contains the hero-lethal retarget test |
| BossNight | `L_Test_BossNight` | 13 + 3 | 60 | 80 | Boss, final night, endless, apex dodge and store-interior chain |
| All | `L_AutomationTestBed` | 206 + 8 | 90 | 120 | Legacy full run. Contaminated (tests share one hero); regression use only |

To run only what a change touches, pick the matching suites. For a full check, run every suite except All, one PIE session at a time.

## How it works

- **The suite comes from the map name.** On BeginPlay, `BP_TestController` calls `RunSuite`, which calls `GetSuiteFromMap`. That function turns `L_Test_<Suite>` into `<Suite>`, and any other map name into `All`. If the suite isn't listed in `DT_AutomationSuites`, the run logs `FAIL: Suite_Unknown_<x>`. Renaming a suite map breaks this.
- **Registry.** `/Game/Tests/Automation/Data/DT_AutomationTests` (row struct `S_AutomationTestRow`) lists every test:
  - **Row name** is the exact `Test_*` function name.
  - **`Suite`** is the suite the test runs in.
  - **`Chained`** is true when an async chain invokes the test, not `RunSuite`.
  - **`Notes`** is free text.
  - **Row insertion order is run order.**
  - `RunSuite` calls each non-chained row of the active suite through `UGDBlueprintLibrary::CallFunctionByName`.
- **Suite settings.** `DT_AutomationSuites` (row struct `S_AutomationSuiteRow`) holds `SettleSeconds` per suite. That is how long `RunSuite` waits after the sync calls before it prints the done marker. Tuning a suite's settle time is a data-only change.
- **Registry check.** `Registry_CheckAllRegistered` logs `Registry_AllTestsRegistered` as PASS or FAIL. It FAILs if any `Test_*` function has no row, and prints `[AUTOTEST] REGISTRY_MISSING: <names>`.
- **Hero guard.** `RunSuite` calls `Hero_EnsureAlive` before the first test. That function respawns dead players through `BP_GameMode_ZombieStore.RespawnDeadPlayers` and re-resolves `TargetPlayer`. Call it at the head of any async chain that needs a live hero.

## Log markers

```
[AUTOTEST] SUITE_START:<Suite>
[AUTOTEST] PASS:<TestName> / FAIL:<TestName>
[AUTOTEST] SUITE_DONE:<Suite> pass=<N> fail=<M> ran=<K>
```

- `pass` and `fail` count `LogResult` lines, not tests. Some tests log twice (ZombieDeathTest, CooldownTest, PartialReserve, ApexDodge), so `pass + fail` can be greater than `ran`.
- An `[AUTOTEST]` line logged after `SUITE_DONE` is **LATE**. Its suite's `SettleSeconds` is too short. Raise it in `DT_AutomationSuites`, then raise the run duration in the table above to SettleSeconds + 20, up to 120.

## Rules

- **Never hand-edit an `L_Test_*` map.** Put fixture actors in `L_AutomationTestBed`, then rerun `Tools/TestSuites/make_suite_maps.py` through `editor.run_python` (`mode: execute_file`). The script deletes each `L_Test_*` map and duplicates it again, so hand edits to the suite maps are lost.
- **Every new `Test_*` function needs a `DT_AutomationTests` row** in the right suite. Without one, `Registry_AllTestsRegistered` fails and the test never runs.
- **Hero-lethal tests** (`Test_Zombie_RetargetsAfterTargetDies`) must not share a suite with async tests that need a live hero.
- **`Test_Spectator_SoloEntersFreeCam` must stay the last Data row.** It leaves `bIsSpectating` set.
- **Async tests that share a target actor** chain off each other's events. Mark the chained test `Chained=true` and put it in the parent's suite.
