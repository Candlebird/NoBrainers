"""
Import placeholder SFX WAVs into /Game/Audio/SFX/Placeholder/ as SoundWave assets.

Re-run this any time the WAVs in PlaceholderAssets/Audio/ are replaced
(e.g. swapped for Freesound-sourced files) — it will re-import and
replace the existing SoundWave assets in place.

Run via Monolith: editor.run_python with mode=execute_file, command set to
this file's absolute path.
"""
import os
import unreal

SOURCE_DIR = r"C:/Users/brest/source/GameDesignRepos/NoBrainers/NoBrainers/PlaceholderAssets/Audio"
DEST_PACKAGE_PATH = "/Game/Audio/SFX/Placeholder"

SFX_NAMES = [
    "SFX_DryFire",
    "SFX_Hitmarker",
    "SFX_HeadshotDing",
    "SFX_KillConfirm",
    "SFX_ScreamerShriek",
    "SFX_BloaterSwell",
    "SFX_BloaterPop",
    "SFX_SpitterSpit",
    "SFX_AcidSplat",
    "SFX_AcidSizzle",
    "SFX_BruteRoar",
    "SFX_BruteImpact",
    "SFX_SurgeGroan",
    "SFX_ZombieDigOut",
    "SFX_PlayerHurt",
]

LOOPING_NAMES = {"SFX_AcidSizzle", "SFX_BloaterSwell"}

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

imported_paths = []
missing = []

for name in SFX_NAMES:
    wav_path = os.path.join(SOURCE_DIR, name + ".wav")
    if not os.path.isfile(wav_path):
        missing.append(wav_path)
        continue

    task = unreal.AssetImportTask()
    task.filename = wav_path
    task.destination_path = DEST_PACKAGE_PATH
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True

    asset_tools.import_asset_tasks([task])

    asset_path = DEST_PACKAGE_PATH + "/" + name
    imported_paths.append(asset_path)

if missing:
    unreal.log_warning("SFX import: missing source WAVs: {}".format(missing))

# Set looping = true on the wet/atmospheric sustained sounds.
for name in LOOPING_NAMES:
    asset_path = DEST_PACKAGE_PATH + "/" + name
    sound_wave = unreal.EditorAssetLibrary.load_asset(asset_path)
    if sound_wave:
        sound_wave.set_editor_property("looping", True)
        unreal.EditorAssetLibrary.save_loaded_asset(sound_wave, only_if_is_dirty=False)
    else:
        unreal.log_warning("SFX import: could not load {} to set looping".format(asset_path))

unreal.log("SFX import complete. Imported: {}".format(imported_paths))
