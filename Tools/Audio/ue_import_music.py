"""
Import placeholder music WAVs into /Game/Audio/Music/ as SoundWave assets.

Re-run this any time the WAVs in PlaceholderAssets/Audio/Music are replaced
— it will re-import and replace the existing SoundWave assets in place.

After import, each wave is set to loop and assigned SoundClass SC_Music.

Run via Monolith: editor.run_python with mode=execute_file, command set to
this file's absolute path.
"""
import os
import unreal

SOURCE_DIR = r"C:/Users/brest/source/GameDesignRepos/NoBrainers/NoBrainers/PlaceholderAssets/Audio/Music"
DEST_PACKAGE_PATH = "/Game/Audio/Music"

MUSIC_NAMES = ["MUS_Day", "MUS_Night"]

SC_MUSIC_PATH = "/Game/Audio/SoundClasses/SC_Music"

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

imported_paths = []
missing = []

for name in MUSIC_NAMES:
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
    unreal.log_warning("Music import: missing source WAVs: {}".format(missing))

sc_music = unreal.EditorAssetLibrary.load_asset(SC_MUSIC_PATH)
if not sc_music:
    unreal.log_warning("Music import: could not load SoundClass {}".format(SC_MUSIC_PATH))

for name in MUSIC_NAMES:
    asset_path = DEST_PACKAGE_PATH + "/" + name
    sound_wave = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not sound_wave:
        unreal.log_warning("Music import: could not load {} to set properties".format(asset_path))
        continue
    sound_wave.set_editor_property("looping", True)
    if sc_music:
        sound_wave.set_editor_property("sound_class_object", sc_music)
    unreal.EditorAssetLibrary.save_loaded_asset(sound_wave, only_if_is_dirty=False)

unreal.log("Music import complete. Imported: {}".format(imported_paths))
