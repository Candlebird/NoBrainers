# Phase 6: Art, UI & Audio

## Technical Context

* **Engine Version:** Unreal Engine 5.7.4
* **Perspective:** First-Person
* **Visual Direction:** Stylized, low-poly / cartoonish, light-hearted and silly aesthetic.
* **Goal:** Implement all user interface overlays, node-building overlays, customer event banners, weapon HUD elements (ammo counters & fast-tracer VFX), cartoonish post-processing/particles, and audio transitions between daytime retail management and night survival.

---

## Task Breakdown

### 1. Stylized Visual Pipeline & Post-Processing

* [ ] **1.1 Post-Process Material Setup**
* Create stylized cel-shader / outline post-process material (`M_PostProcess_CelShader`).
* Add configurable line width and depth-based outline controls for cartoon aesthetic.

* [ ] **1.2 Environment & Store Styling**
* Light-hearted, vibrant master materials with simple color palettes and toon lighting support.
* Modular store assets: Cash registers, colorful shelves, pre-defined defense socket node markers, neon signs, and humorous posters.

* [ ] **1.3 Visual Effects (VFX / Niagara Systems)**
* **Combat VFX:** Fast-moving visual tracer particles for raycast weapons, cartoonish muzzle flashes, hit impacts, and silly death/splatter FX (e.g., confetti burst, green goo).
* **Build Mode VFX:** Node highlight shaders (`Floor`, `Wall`, `TurretBase`, `Other`) visible when Build Mode is active; placement pop FX when installing defenses.
* **Retail VFX:** Floating pop-up text over cash registers/shipping crate ("+$15") and customer archetype indicators (e.g., dollar signs above Rich customers, cross icons above Nurses).

---

### 2. User Interface & HUD Systems (UMG)

* [ ] **2.1 First-Person Survival HUD (`UW_MainHUD`)**
* Player Health & Armor bars.
* Current Store Cash balance display.
* Weapon HUD: Ammo count (`CurrentAmmo / ReserveAmmo`), equipped slot indicator (Primary, Secondary, Melee).
* Day/Night Phase Timer & Active Phase Indicator (Sun/Moon icon).
* Alive Teammate status indicators (Name, Health, Down/Dead status).

* [ ] **2.2 Reticle & Interaction Overlay**
* Dynamic crosshair with hit-marker animations on successful raycast/melee hits.
* Interaction prompt widget (`E_To_Interact`) displaying target actor name (e.g., "Press [E] to Stock Shelf", "Press [E] to Open Kiosk").

* [ ] **2.3 Shelf-Stocking & Customer Event UI**
* Combo feedback overlay on shelves showing matching row bonuses (e.g., "3x Combo! +50% Profit").
* Dynamic event notification banner (e.g., "CUSTOMER EVENT: Nurse Surge Incoming! Stock Medical Items!").

* [ ] **2.4 Build Mode UI & Shop Kiosks**
* Day-Only Build Menu (`UW_BuildMenu`): Carousel/Radial UI triggered by `B` key to select unlocked blueprints (`ADefenseBase`).
* Node interaction UI: Repair/Dismantle options when targeting occupied sockets in Build Mode.
* Employee Discount Kiosk menu: Store upgrades, raycast/melee weapons, and advertisement level controls.

> **STATUS NOTE (2026-09-25, overnight UI restyle pass):**
>
> All 16 UI widgets now use one shared style: dark rounded panels, an Ink outline, gold/red hover states, and outlined Roboto Bold text. That covers WBP_HUD plus the kiosk, inventory, build, event banner, shelf, main menu, and meta shop widgets.
>
> The HUD restructure added:
> - Health/armor/stamina rows in the bottom-left.
> - A phase panel with an M:SS timer (top-center).
> - A cash panel with a pulse animation (top-right).
> - A weapon panel with Primary/Secondary/Melee pips and a red empty-mag color (bottom-right).
> - An `[E] Interact` prompt, driven by a 250 uu trace.
> - A new `WBP_TeammateEntry` list (name, health, DOWN).
>
> Everything compiled clean. The 2.x boxes stay unchecked until PIE confirms the checks below and the gaps are closed.
>
> **Manual PIE checks:**
> - **HUD:**
>   - Taking damage, gaining armor, and sprinting update their bars. The armor row stays hidden while armor is 0.
>   - The phase name, color, and M:SS timer change on each phase change.
>   - Earning cash pulses the cash panel.
>   - Switching slots moves the active pip and changes the weapon name. An empty magazine turns the ammo red.
> - **Interact prompt:** within about 2.5 m of an interactable, `[E] Interact` appears, and it hides when you look away.
> - **Teammates (2-player Listen Server):** a row appears for the other player, its health bar tracks their health, and it shows "DOWN" at reduced opacity on death.
> - **Kiosk, Build (B), Inventory, Shelf:** buttons turn gold on hover. The Sell and Drop buttons turn red on hover. Locked or unaffordable entries still grey out. Shelf slots still tint on drag-over and select. The combo bonus text reads clearly.
> - **Event banner:** it fades in below the phase panel, keeps its event tint, and auto-hides.
> - **Main menu / meta shop:** the "NO BRAINERS" title reads well, Quit turns red on hover, and meta shop entries have good contrast.
>
> **Gaps:** see docs/BUGS.md — "Phase 6 UI pass: known limitations."

---

### 3. Audio Architecture & Dynamic Music Engine

* [ ] **3.1 Dynamic Music System (`UAudioManager`)**
* Interactive music state machine transitioning between phases:
* **Day Phase:** Upbeat, cozy elevator/retail background music (switches intensity during Customer Events).
* **Night Phase:** Tense synth-pop / goofy horror music with dynamic drums layering in as zombie count scales.

* [ ] **3.2 Combat & Interaction Sound Effects (SFX)**
* **Weapon SFX:** Fast raycast tracer audio, punchy cartoonish gunshots, reload clicks, and melee swing/whack sounds.
* **Retail & Build SFX:** Cash register "cha-ching", scanner beeps, socket snap sounds when placing defenses, and node repair audio.
* **Trap SFX:** Buzzing electric fences, mallet swings, spring trap pops, turret firing loops.

* [ ] **3.3 Customer & Zombie Audio Design**
* Unique customer voice lines/reactions (e.g., cheerful rich customer chimes, cheap customer complaints).
* Comedic zombie vocalizations: Funny groans, breach impact thuds, and arcade-style death squeaks.

---

## Acceptance Criteria

1. The post-process cel-shader material renders cleanly over all gameplay elements, enforcing a distinct cartoon look.
2. The HUD accurately tracks health, cash reserves, ammo/reload state for raycast weapons, day/night timers, and teammate statuses in multiplayer.
3. Toggling Build Mode with `B` during the day displays clear node socket highlights (`Floor`, `Wall`, `TurretBase`, `Other`) and opens the blueprint placement carousel.
4. Customer Event HUD banners correctly alert players to incoming archetype waves, matching audio cues and visual customer indicators.
5. The audio system seamlessly transitions music tracks between Day and Night phases, complete with comedic zombie voice lines, punchy combat SFX, and retail interaction audio.
