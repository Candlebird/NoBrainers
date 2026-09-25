# LevelView — level layout & review tools

`Tools/LevelView/` is a small Python toolkit for laying out and reviewing levels without PIE.
The workflow is: define the layout in Python, iterate on it in 2D/3D matplotlib, push it into
the editor, then look at it with in-editor captures. It was built to author `Map_Store_Outdoors`.

Requirements (offline scripts): Python 3 with `numpy`, `scipy`, `matplotlib`.
In-editor scripts run through Monolith: `editor.run_python {command: "<abs path>/<script>.py args", unattended: true}`.
All output goes to `Saved/LevelView/`.

## Coordinate frame

Unreal units (cm). X = 0 at the store's front wall, increasing toward the back. Y spans ±W/2.
Floor top is at Z = 0. Plots draw +X right, +Y **down**, to match the `top` capture.

## Scripts

| Script | Where it runs | What it does |
|---|---|---|
| `store_layout.py` | offline | The `Map_Store_Outdoors` spec (shell, departments, gameplay BPs, defense sockets, lights). Writes `store_layout.json`. **Edit this to change the level.** |
| `lvlib.py` | offline (lib) | Element model, the greybox palette (`MATERIALS`), footprint rasterization, and walkability metrics (open-fight area, narrow corridors, disconnected pockets, breach→checkout distances, turret cover). |
| `plan.py` | offline | `python plan.py <layout.json> --mode plan\|clearance\|defense\|3d\|all [--labels] [--region x0,y0,x1,y1]`. Renders PNGs and prints a `LEVELVIEW_METRICS {...}` line. |
| `capgrid.py` | offline | Draws a world grid (and layout ids) over a `top` capture so you can find coordinates. |
| `ue_make_materials.py` | editor | Creates `/Game/Environment/Greybox/M_LV_Flat` + one `MI_LV_<key>` per palette entry. Idempotent. |
| `ue_apply_layout.py` | editor | Rebuilds the **open** level from a layout JSON: deletes every `LV`-tagged actor, then spawns the layout (primitives, BPs with props and `@id` actor refs, lights, markers, PPV). Add `only=cat1,cat2` to rebuild some categories. Doesn't save. |
| `ue_capture.py` | editor | SceneCapture2D to PNG with no PIE. `top [cx cy width]`, `iso yaw pitch dist` (pitch **negative**), `eye x y yaw [pitch z]`, `cam x y z pitch yaw [fov]`. Flags: `res=WxH name=<stem> roof=1 ev=<bias>`. |
| `ue_dump_level.py` | editor | Dumps every actor in the open level to JSON, which `plan.py` can plot. |

## Iteration loop

1. Edit `store_layout.py`, then `python store_layout.py` and `python plan.py ... --mode all`. Check the metrics and PNGs.
2. With `Map_Store_Outdoors` open in the editor, run `ue_apply_layout.py <abs>/Saved/LevelView/store_layout.json`.
3. Run `ai.build_navigation`, then `editor.save_packages {packages: ["/Game/Levels/Map_Store_Outdoors"]}`.
4. Capture views with `ue_capture.py` and review the PNGs.

Anything you place by hand **without** the `LV` tag survives step 2. Anything tagged `LV` is overwritten.

## Map_Store_Outdoors summary

- 70 × 50 m hall. 7 m eaves, and a 10 m clerestory nave rising to a 13.5 m ridge on log columns.
- Entries: 3 front doors, left and right side exits, and a rear dock. Each is a scaled `BP_BreachPoint` panel, so the store is sealed until a breach opens.
- 3 checkouts front-right, with queues running +X. There's a fireplace lodge front-left and a service desk with discount and shop kiosks.
- A central hub with a pond, rock mountain, waterfall, and pine, plus 4 turret ledges.
- Departments: hunting, archery, and ammo (left front). Camping, food, and medical (left rear). Fishing and hardware (right). Boats, apparel, and the aquarium (back). There's also a stock room with the shipping crate.
- Defense sockets at every entry, the hub, and the checkout. Nine zombie spawn points outside feed `ZombieSpawnerManager`.
- 2D metrics: about 2,780 m² walkable inside, 640 m² of open-fight area, no pockets, and 78% interior turret cover.

## Manual PIE tests (pending)

1. Start Run from the Main Menu and confirm you spawn in `Map_Store_Outdoors` at the front of the nave with the starting pistol.
2. Stock the shelves. After the first night, customers should spawn at the front, shop, queue at the 3 checkouts (queues form along +X), and leave through the front.
3. At night, zombies should spawn outside and attack the 6 breach panels (3 front, 2 side, 1 dock). Check that a broken panel lets them in and that repair works.
4. Build mode: place defenses on the entry, hub, and checkout sockets.
5. General: check that the lighting reads, that there are no invisible walls or stuck spots around the hub rocks, pond, and gondolas, and that the stock room crate is reachable.
