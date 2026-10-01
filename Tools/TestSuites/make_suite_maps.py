# Regenerates the per-suite test maps by duplicating L_AutomationTestBed.
# Run in the Unreal editor via editor.run_python (execute_file). Does not load any level.
import unreal

SOURCE = "/Game/Tests/Automation/Maps/L_AutomationTestBed"
DEST_DIR = "/Game/Tests/Automation/Maps"
SUITES = ["Data", "Economy", "Defense", "Player", "Retail", "Zombie", "BossNight"]
PREFIX = "/Game/Tests/Automation/Maps/L_Test_"

dests = [f"{DEST_DIR}/L_Test_{s}" for s in SUITES]
for d in dests:
    assert d.startswith(PREFIX), f"bad dest {d}"

for dest in dests:
    if unreal.EditorAssetLibrary.does_asset_exist(dest):
        if not unreal.EditorAssetLibrary.delete_asset(dest):
            raise RuntimeError(f"[SUITEMAPS] could not delete existing {dest} (map open?)")
    ok = bool(unreal.EditorAssetLibrary.duplicate_asset(SOURCE, dest)) and \
        unreal.EditorAssetLibrary.save_asset(dest, only_if_is_dirty=False)
    print(f"[SUITEMAPS] {dest} {'ok' if ok else 'FAILED'}")
