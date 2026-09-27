"""
Import K3 (retail/build/defense/breach/pickup) SFX WAVs into Unreal as
SoundWave assets under their category subfolders.

Re-run this any time the WAVs in PlaceholderAssets/Audio/ are replaced
(e.g. swapped for different Freesound-sourced files) -- it will re-import
and replace the existing SoundWave assets in place.

Run via Monolith: editor.run_python with mode=execute_file, command set to
this file absolute path.
"""
import os
import unreal

SOURCE_DIR = r"C:/Users/brest/source/GameDesignRepos/NoBrainers/NoBrainers/PlaceholderAssets/Audio"

SC_SFX_PATH = "/Game/Audio/SoundClasses/SC_SFX"

# name -> (dest_folder, sound_class_path, looping)
K3_SOUNDS = {
    "SFX_ScanBeep":        ("/Game/Audio/SFX/Retail", SC_SFX_PATH, False),
    "SFX_CashRegister":    ("/Game/Audio/SFX/Retail", SC_SFX_PATH, False),
    "SFX_SocketSnap":      ("/Game/Audio/SFX/Build", SC_SFX_PATH, False),
    "SFX_Repair":          ("/Game/Audio/SFX/Build", SC_SFX_PATH, False),
    "SFX_TrapZap":         ("/Game/Audio/SFX/Defense", SC_SFX_PATH, False),
    "SFX_TrapGasHiss":     ("/Game/Audio/SFX/Defense", SC_SFX_PATH, False),
    "SFX_TrapSpringPop":   ("/Game/Audio/SFX/Defense", SC_SFX_PATH, False),
    "SFX_TrapMalletSwing": ("/Game/Audio/SFX/Defense", SC_SFX_PATH, False),
    "SFX_TurretFire":      ("/Game/Audio/SFX/Defense", SC_SFX_PATH, False),
    "SFX_BreachThud":      ("/Game/Audio/SFX/Breach", SC_SFX_PATH, False),
    "SFX_BreachBreak":     ("/Game/Audio/SFX/Breach", SC_SFX_PATH, False),
    "SFX_AmmoPickup":      ("/Game/Audio/SFX/Pickup", SC_SFX_PATH, False),
    "SFX_Simlish_Happy_01":   ("/Game/Audio/SFX/Customer", SC_SFX_PATH, False),
    "SFX_Simlish_Happy_02":   ("/Game/Audio/SFX/Customer", SC_SFX_PATH, False),
    "SFX_Simlish_Happy_03":   ("/Game/Audio/SFX/Customer", SC_SFX_PATH, False),
    "SFX_Simlish_Annoyed_01": ("/Game/Audio/SFX/Customer", SC_SFX_PATH, False),
    "SFX_Simlish_Annoyed_02": ("/Game/Audio/SFX/Customer", SC_SFX_PATH, False),
    "SFX_Simlish_Annoyed_03": ("/Game/Audio/SFX/Customer", SC_SFX_PATH, False),
    "SFX_Simlish_Hmm_01":     ("/Game/Audio/SFX/Customer", SC_SFX_PATH, False),
    "SFX_Simlish_Hmm_02":     ("/Game/Audio/SFX/Customer", SC_SFX_PATH, False),
    "SFX_Simlish_Hmm_03":     ("/Game/Audio/SFX/Customer", SC_SFX_PATH, False),
    "SFX_ArchetypeChime":     ("/Game/Audio/SFX/Customer", SC_SFX_PATH, False),
    "SFX_ZombieGrowl_01":      ("/Game/Audio/SFX/Zombie", SC_SFX_PATH, False),
    "SFX_ZombieGrowl_02":      ("/Game/Audio/SFX/Zombie", SC_SFX_PATH, False),
    "SFX_ZombieGrowl_03":      ("/Game/Audio/SFX/Zombie", SC_SFX_PATH, False),
    "SFX_ZombieIdle_Burp":     ("/Game/Audio/SFX/Zombie", SC_SFX_PATH, False),
    "SFX_ZombieIdle_Gurgle":   ("/Game/Audio/SFX/Zombie", SC_SFX_PATH, False),
    "SFX_ZombieIdle_Moan":     ("/Game/Audio/SFX/Zombie", SC_SFX_PATH, False),
    "SFX_ZombieDeath_Squeak_01": ("/Game/Audio/SFX/Zombie", SC_SFX_PATH, False),
    "SFX_ZombieDeath_Squeak_02": ("/Game/Audio/SFX/Zombie", SC_SFX_PATH, False),
}

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

imported_paths = []
missing = []

for name, (dest_folder, sound_class_path, looping) in K3_SOUNDS.items():
    wav_path = os.path.join(SOURCE_DIR, name + ".wav")
    if not os.path.isfile(wav_path):
        missing.append(wav_path)
        continue

    task = unreal.AssetImportTask()
    task.filename = wav_path
    task.destination_path = dest_folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True

    asset_tools.import_asset_tasks([task])

    asset_path = dest_folder + "/" + name
    imported_paths.append(asset_path)

if missing:
    unreal.log_warning("K3 SFX import: missing source WAVs: {}".format(missing))

for name, (dest_folder, sound_class_path, looping) in K3_SOUNDS.items():
    asset_path = dest_folder + "/" + name
    sound_wave = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not sound_wave:
        continue

    sound_wave.set_editor_property("looping", looping)

    sound_class = unreal.EditorAssetLibrary.load_asset(sound_class_path)
    if sound_class:
        sound_wave.set_editor_property("sound_class_object", sound_class)
    else:
        unreal.log_warning("K3 SFX import: could not load SoundClass {}".format(sound_class_path))

    unreal.EditorAssetLibrary.save_loaded_asset(sound_wave, only_if_is_dirty=False)

unreal.log("K3 SFX import complete. Imported: {}".format(imported_paths))
