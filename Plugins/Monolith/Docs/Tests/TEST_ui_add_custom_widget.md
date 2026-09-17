# Monolith Tooling Test — `ui.add_custom_widget`

**Scope:** This is a test of a **Monolith MCP tool's behavior**, not of Steel Caravan gameplay Blueprint
logic. It intentionally lives outside `Content/Tests/Automation/` (the `BP_TestController` gameplay test
bed — see `docs/13-automation-test-bed.md`), because that harness only exercises in-game Blueprint graphs
via PIE, and `ui.add_custom_widget` is editor-tooling: there's no gameplay behavior to run, just an
asset-authoring call to verify. See `docs/13-automation-test-bed.md`'s intro for a pointer back to this
file.

**What's being verified:** `ui.add_custom_widget` (namespace `ui`, handler
`MonolithUIActionsCustomWidget::HandleAddCustomWidget` in
`Plugins/Monolith/Source/MonolithUI/Private/MonolithUIActions.cpp`) adds an instance of a
project-authored custom `UserWidget` Blueprint into another WidgetBlueprint's tree — unlike `ui.add_widget`,
which only supports native widget types (TextBlock, Image, Button, etc.) via a fixed token allowlist.
`add_custom_widget` instead resolves `widget_blueprint_path` via `LoadObject<UWidgetBlueprint>` +
`GeneratedClass`.

**Reproduction:** all calls below were made with `monolith_status` reporting `server_running: true`,
engine `++UE5+Release-5.8-CL-56702186`, project `TheSteelCaravan`.

## Setup — throwaway parent WidgetBlueprint

Created a disposable target so no real production UMG asset (e.g. `WB_InventoryPart1`) was touched:

```
ui.create_widget_blueprint
  save_path: /Game/Tests/Automation/UI/WBP_MonolithCustomWidgetTest
  parent_class: UserWidget
  root_widget: CanvasPanel
```

Result: created + compiled + saved, root `CanvasPanel`.

## Positive case — add a real custom widget

Used `WB_EquipSlot` (`/Game/INVENTORY/UI/Widgets/WB_EquipSlot`) — a known small custom `UserWidget`
Blueprint already used in `WB_InventoryPart1` — as the widget to instantiate. Path confirmed via direct
filesystem lookup (`Content/INVENTORY/UI/Widgets/WB_EquipSlot.uasset`) before use.

```
ui.add_custom_widget
  asset_path: /Game/Tests/Automation/UI/WBP_MonolithCustomWidgetTest
  widget_blueprint_path: /Game/INVENTORY/UI/Widgets/WB_EquipSlot
  widget_name: TestEquipSlotInstance
  compile: true
```

Result:
```json
{"widget_name":"TestEquipSlotInstance","widget_class":"WB_EquipSlot_C","widget_blueprint_path":"/Game/INVENTORY/UI/Widgets/WB_EquipSlot","parent_name":"CanvasPanel","slot_type":"CanvasPanelSlot","compiled":true}
```

Verified via `ui.get_widget_tree` on the throwaway asset:
```json
{"root":{"name":"CanvasPanel","class":"CanvasPanel","children":[
  {"name":"TestEquipSlotInstance","class":"WB_EquipSlot_C","is_variable":true,
   "slot":{"slot_type":"CanvasPanelSlot", "...":"..."}}
]},"widget_count":2}
```

**PASS** — child node `TestEquipSlotInstance` exists, is class `WB_EquipSlot_C` (the correct generated
class of the custom Blueprint), and is parented directly under the root `CanvasPanel` in a
`CanvasPanelSlot`.

## Negative case — invalid `widget_blueprint_path`

```
ui.add_custom_widget
  asset_path: /Game/Tests/Automation/UI/WBP_MonolithCustomWidgetTest
  widget_blueprint_path: /Game/INVENTORY/UI/Widgets/WB_DoesNotExist_Bogus
  widget_name: ShouldFail
```

Result — a structured error, no crash, no silent no-op:
```
category: Asset
severity: error
json_path: /widget_blueprint_path
message: Could not load a UWidgetBlueprint at '/Game/INVENTORY/UI/Widgets/WB_DoesNotExist_Bogus'.
suggested_fix: Verify the asset path and that it points at a WidgetBlueprint asset (not a regular Actor/Object Blueprint, and not a non-Blueprint asset).
```

**PASS** — invalid path is rejected with a clear, structured error (category/severity/json_path/message/
suggested_fix), matching the shape of other Monolith asset-resolution errors. The parent WidgetBlueprint's
tree was left unmodified by the failed call (re-confirmed via `get_widget_tree`: only the one child from
the positive case is present).

## Cleanup

`/Game/Tests/Automation/UI/WBP_MonolithCustomWidgetTest` was deleted after verification
(`editor_query delete_assets`) — it was a throwaway fixture only, not kept as a permanent regression
asset. Re-run this doc's steps verbatim to reproduce.

## Result summary

| Case | Result |
|---|---|
| Positive: add custom widget (`WB_EquipSlot`) into a fresh WidgetBlueprint | PASS — correct class, correct parent, compiled |
| Negative: invalid `widget_blueprint_path` | PASS — structured error, no crash, tree unmodified |

## Known limitation (confirmed on a real-asset follow-up, Sept 2026)

`add_custom_widget` correctly creates and parents the new widget instance and is safe/functional for actual
gameplay use, but its `size`/`position` params don't reliably land the instance where you'd expect — on the
`WB_InventoryPart1` / `EquipSlotWEAPON3` follow-up (see `docs/11-implementation-roadmap.md`), the new slot's
size and placement needed manual correction to actually match its sibling `EquipSlotWEAPON2` rather than
coming out right from the tool call alone. Treat the action as reliable for getting the right widget
instance into the right parent/tree location, but always re-check (and likely hand-adjust via
`list_widget_properties`/`set_widget_property`) the resulting size and canvas position afterward rather than
trusting the initial placement.
