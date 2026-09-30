# Fast customer-AI test. Run in the editor while PIE is running on Map_Store_Outdoors:
#   editor_query run_python (or Tools > Execute Python Script).
# Stocks every shelf slot from DT_Items and burst-spawns customers in ANY phase (no waiting for day, no zombies needed).
import unreal
COUNT = 3
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
acts = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
dt = unreal.load_object(None, '/Game/Data/DT_Items.DT_Items')
items = [str(n) for n in unreal.DataTableFunctionLibrary.get_data_table_row_names(dt)]
i = 0
for s in [a for a in acts if a.get_name().startswith('BP_ShelfActor')]:
    for slot in range(s.call_method('GetNumSlots')):
        s.call_method('SetSlotItem', args=(slot, items[i % len(items)], 5)); i += 1
sp = [a for a in acts if a.get_name().startswith('BP_CustomerSpawner')][0]
sp.call_method('Server_SpawnCustomerBurst', args=(COUNT, 'Normal'))
print('stocked', i, 'slots; spawned', COUNT, 'customers in', w.get_name())
