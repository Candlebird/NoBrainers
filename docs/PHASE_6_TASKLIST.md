\# Phase 6: Art, UI \& Audio



\## Technical Context



\* \*\*Engine Version:\*\* Unreal Engine 5.7.4

\* \*\*Perspective:\*\* First-Person

\* \*\*Visual Direction:\*\* Stylized, low-poly / cartoonish, light-hearted and silly aesthetic.

\* \*\*Goal:\*\* Implement all user interface overlays, HUD elements, post-processing materials, cartoonish particle effects, and audio transitions between the cozy daytime retail loop and silly horror night phase.



\---



\## Task Breakdown



\### 1. Stylized Visual Pipeline \& Post-Processing



\* \[ ] \*\*1.1 Post-Process Material Setup\*\*

\* Create stylized cel-shader / outline post-process material (`M\_PostProcess\_CelShader`).

\* Add configurable line width and depth-based outline controls for cartoon aesthetic.





\* \[ ] \*\*1.2 Environment \& Store Styling\*\*

\* Light-hearted, vibrant master materials with simple color palettes and toon lighting support.

\* Modular store assets: Cash registers, colorful shelves, neon signs, and humorous posters.





\* \[ ] \*\*1.3 Visual Effects (VFX / Niagara Systems)\*\*

\* Silly cartoon blood/splatter FX (e.g., confetti burst, green goo, or arcade-style pop-ups) on zombie hits.

\* Placement FX: Green dust/sparkle puff when placing shelves or traps.

\* Cash register visual pop-ups ("+$15" floating text over register/shipping crate).







\---



\### 2. User Interface \& HUD Systems (UMG)



\* \[ ] \*\*2.1 First-Person Survival HUD (`UW\_MainHUD`)\*\*

\* Player Health \& Armor bars.

\* Current Store Cash balance display.

\* Day/Night Phase Timer \& Active Phase Indicator (Sun/Moon icon).

\* Alive Teammate status indicators (Name, Health, Down/Dead status).





\* \[ ] \*\*2.2 Reticle \& Interaction Overlay\*\*

\* Dynamic crosshair with hit-marker animations on successful zombie hits.

\* Interaction prompt widget (`E\_To\_Interact`) displaying target actor name (e.g., "Press \[E] to Stock Shelf").





\* \[ ] \*\*2.3 Shelf-Stocking Minigame UI\*\*

\* Visual feedback overlay on shelves showing adjacent match combo bonuses (e.g., "2x Combo! +25% Profit").





\* \[ ] \*\*2.4 In-Game Store \& Kiosk Interfaces\*\*

\* Employee Discount Kiosk menu: Clean grid view for buying weapons, traps, and store advertisements.

\* Build Mode Overlay: First-person HUD indicator showing active defense selected and rotation controls.







\---



\### 3. Audio Architecture \& Dynamic Music Engine



\* \[ ] \*\*3.1 Dynamic Music System (`UAudioManager`)\*\*

\* Interactive music state machine transitioning between phases:

\* \*\*Day Phase:\*\* Upbeat, cozy elevator/retail background music.

\* \*\*Night Phase:\*\* Tense synth-pop / goofy horror music.





\* Dynamic intensity scaling: Music stems layer in extra drums/synths as zombie horde count increases.





\* \[ ] \*\*3.2 Combat \& Interaction Sound Effects (SFX)\*\*

\* Weapon SFX: Punchy, cartoonish gunshots and melee whacks.

\* Retail SFX: Cash register "cha-ching", scanner beeps, and item placement snaps.

\* Trap SFX: Buzzing electric fences, spring trap pops, turret firing loops.





\* \[ ] \*\*3.3 Zombie Audio Design\*\*

\* Comedic zombie vocalizations: Funny groans, silly breach grunts, and arcade-style death squeaks.







\---



\## Acceptance Criteria



1\. The post-process cel-shader material renders cleanly over all gameplay elements, enforcing a distinct cartoon look.

2\. The HUD accurately displays real-time health, cash, day/night timers, and teammate statuses in multiplayer.

3\. Interactive prompts and matching combo overlays give clear visual feedback during the daytime loop.

4\. The audio system seamlessly transitions music tracks between Day and Night phases, complete with comedic zombie voice lines and punchy combat SFX.

