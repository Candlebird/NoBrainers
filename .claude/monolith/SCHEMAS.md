# Monolith action schemas (verified, cached)

Grep this file instead of calling describe_query/monolith_discover:
`Grep pattern="^## blueprint.add_node" path=.claude/monolith/SCHEMAS.md -A 12`
`*` = required. If an action is missing here, fall back to describe_query action_schema
with params {target_namespace, target_action}.

## None.None — Place multiple nodes in one transaction. Returns a temp_id -> node_id mapping so callers can immediately reference created nodes in connect_pins_bulk. Each entry: { temp_id, node_type, function_name?, target_class?, var…
  asset_path* string — Blueprint asset path
  nodes* array — Array of node descriptors: { temp_id, node_type, function_name?, target_class?, variable_name?, position? }
  graph_name string — Graph name (defaults to EventGraph)
  auto_layout boolean — Auto-position nodes in a 5-column grid (200px horizontal, 100px vertical spacing). Ignored if position is set per node. Default: false.

## ai.add_bb_key — Add a key to a Blackboard (Bool/Int/Float/String/Name/Vector/Rotator/Object/Class/Enum/NativeEnum)
  asset_path* string — Blackboard asset path
  key_name* string — Name for the new key
  key_type* string — Key type: Bool, Int, Float, String, Name, Vector, Rotator, Object, Class, Enum, NativeEnum
  description string — Optional description for the key
  base_class string — Base class filter for Object/Class key types
  enum_type string — Enum type name for Enum/NativeEnum key types
  instance_synced boolean (default false) — If true, key is synced across all blackboard instances

## ai.add_bt_decorator — Add a decorator as a sub-node on a target BT node
  asset_path* string — Behavior Tree asset path
  node_id* string — GUID of the target node
  decorator_class* string — Decorator class name (e.g. BTDecorator_Blackboard)
  properties object — JSON object of property_name→value pairs to set

## ai.add_bt_node — Add a composite or task node to a Behavior Tree. parent_id=null adds under root.
  asset_path* string — Behavior Tree asset path
  parent_id string — GUID of parent composite node (null = root)
  node_class* string — BT node class name (e.g. BTTask_Wait, BTComposite_Sequence)
  index number — Child index under parent (-1 or omit = append)
  properties object — JSON object of property_name→value pairs to set

## ai.add_bt_service — Add a service as a sub-node on a composite or task node
  asset_path* string — Behavior Tree asset path
  node_id* string — GUID of the target node
  service_class* string — Service class name (e.g. BTService_DefaultFocus)
  properties object — JSON object of property_name→value pairs to set

## ai.add_nav_bounds_volume — Spawn ANavMeshBoundsVolume at a location with given extents
  location* object — World position {x, y, z} or [x, y, z]
  extent* object — Half-extents {x, y, z} or [x, y, z]
  folder_path string — Outliner folder path (default: AI/Navigation)

## ai.analyze_navigation_coverage — Grid-sample the level and project points to navmesh — reports coverage percentage, gaps, and stats
  sample_spacing number — Distance between sample points (cm, default: 200)
  bounds object — Custom bounds {min: [x,y,z], max: [x,y,z]} — defaults to nav bounds

## ai.batch_add_bb_keys — Add multiple keys to a Blackboard at once
  asset_path* string — Blackboard asset path
  keys* array — Array of key objects, each with: name (string), type (string), description? (string), base_class? (string), enum_type? (string)

## ai.build_behavior_tree_from_spec — Create a complete Behavior Tree from a declarative JSON spec — the crown jewel
  save_path* string — Asset save path (e.g. /Game/AI/BT_Enemy)
  spec* object — Full tree spec with root, children, decorators, services, properties
  strict_mode boolean (default false) — If true, abort with error (no save) when any node fails to resolve

## ai.create_behavior_tree — Create a new Behavior Tree asset, optionally linking a Blackboard
  save_path* string — Asset save path (e.g. /Game/AI/BT_Enemy)
  name string — Asset name (derived from save_path if omitted)
  blackboard_path string — Blackboard asset path to link

## ai.create_blackboard — Create a new Blackboard Data asset
  save_path* string — Asset save path (e.g. /Game/AI/BB_Enemy)
  name string — Asset name (derived from save_path if omitted)
  parent_bb string — Parent blackboard asset path for key inheritance

## ai.create_bt_decorator_blueprint — Create a BTDecorator Blueprint (parent defaults to BTDecorator_BlueprintBase)
  save_path* string — Asset save path
  name* string — Blueprint name
  parent_class string — Parent class name (default: BTDecorator_BlueprintBase)

## ai.create_bt_service_blueprint — Create a BTService Blueprint (parent defaults to BTService_BlueprintBase)
  save_path* string — Asset save path
  name* string — Blueprint name
  parent_class string — Parent class name (default: BTService_BlueprintBase)

## ai.create_bt_task_blueprint — Create a BTTask Blueprint (parent defaults to BTTaskNode)
  save_path* string — Asset save path (e.g. /Game/AI/Tasks/BTTask_MyTask)
  name* string — Blueprint name
  parent_class string — Parent class name (default: BTTask_BlueprintBase)

## ai.export_bt_spec — Export an existing Behavior Tree as a JSON spec (inverse of build_behavior_tree_from_spec)
  asset_path* string — Behavior Tree asset path

## ai.get_bt_node_properties — Read all UPROPERTYs from a BT node instance
  asset_path* string — Behavior Tree asset path
  node_id* string — GUID of the node

## ai.import_bt_spec — Recreate a Behavior Tree from an exported spec (overwrites existing tree structure)
  asset_path* string — Behavior Tree asset path (must exist)
  spec* object — Full tree spec in export format

## ai.remove_bt_node — Remove a node and its children from a Behavior Tree
  asset_path* string — Behavior Tree asset path
  node_id* string — GUID of the node to remove

## ai.remove_bt_service — Remove a service from a BT node by index
  asset_path* string — Behavior Tree asset path
  node_id* string — GUID of the node that owns the service
  service_index* number — Index of the service to remove

## ai.reorder_bt_children — Reorder child nodes under a composite by specifying new GUID order
  asset_path* string — Behavior Tree asset path
  parent_id* string — GUID of the parent composite node
  new_order* array — Array of child node GUIDs in desired order

## ai.set_bt_node_property — Set a UPROPERTY on a BT node instance. Special handling for FBlackboardKeySelector.
  asset_path* string — Behavior Tree asset path
  node_id* string — GUID of the node
  property_name* string — UPROPERTY name to set
  value* any — Value to set (type depends on property)

## animation.add_socket — Add a socket to a skeleton
  asset_path* string — Skeleton asset path
  bone_name* string — Parent bone name
  socket_name* string — Name for the new socket
  location array — [x, y, z] relative location
  rotation array — [pitch, yaw, roll] relative rotation
  scale array — [x, y, z] relative scale

## animation.batch_retarget_animations — Duplicate and retarget a list of animation assets cross-skeleton using an IK Retargeter. Outputs new clips bound to the target skeleton into output_folder.
  retargeter_path* string — IK Retargeter asset path
  source_anims* array — Array of source animation asset paths to retarget
  output_folder* string — Destination folder for retargeted clips (e.g. /Game/Path/Retargeted)
  source_mesh string — Source skeletal mesh (defaults to the retargeter's source preview mesh)
  target_mesh string — Target skeletal mesh (defaults to the retargeter's target preview mesh)
  name_prefix string — Prefix added to each output asset name
  name_suffix string — Suffix added to each output asset name
  search string — Substring to search for in source names (replaced with 'replace')
  replace string — Replacement for the 'search' substring
  include_referenced bool (default false) — Also retarget assets referenced by the inputs (default: false)
  overwrite bool (default false) — Overwrite existing output files instead of creating uniquely-named copies (default: false)
  auto_map string (default fuzzy) — Chain auto-map mode if ops must be seeded on run: 'fuzzy' (default) or 'exact'

## animation.build_state_machine — Declarative state-machine builder: creates the SM then adds states, transitions, and rules in one transaction
  asset_path* string — Animation Blueprint asset path
  state_machine_name string — Name for the state machine (default: 'New State Machine')
  graph_name string — Target anim graph name for layered ABPs (default: first AnimationGraphSchema graph)
  states* array — Array of {name, animation?} state specs
  transitions array — Array of {from, to, rule?} transition specs. rule may be a bool variable name, 'auto'/'automatic' for the sequence-player auto rule, or a s…
  entry_state string — State to wire as the initial/entry state

## animation.create_anim_blueprint — Create a new Animation Blueprint asset with skeleton
  asset_path* string — Asset path for the new ABP (e.g. /Game/ABP/ABP_Character)
  skeleton_path* string — Skeleton asset path
  parent_class string — Parent class name (default: AnimInstance)

## animation.get_animated_bone_transform — Evaluate one bone's FK-composed transform on an AnimSequence at a specific frame or time (extends get_bone_ref_pose's bind-pose compose to an animated frame). Provide exactly one of frame (integer) / time (seconds); fra…
  asset_path* string — AnimSequence asset path
  bone_name* string — Bone to evaluate
  frame integer — Frame index to evaluate at (mutually exclusive with time; takes precedence if both supplied)
  time number — Time in seconds to evaluate at (used when frame is absent)
  space string (default component) — component (default) / world (both = FAnimPose World/component space) or local (parent-relative)

## animation.get_skeleton_info — Get skeleton bone hierarchy and virtual bones
  asset_path* string — Skeleton asset path

## animation.get_skeleton_sockets — Get sockets from a skeleton or skeletal mesh
  asset_path* string — Skeleton or SkeletalMesh asset path

## animation.set_bone_track_keys — Set position, rotation, and scale keys on a bone track
  asset_path* string — Animation sequence asset path
  bone_name* string — Bone name
  positions_json* string — JSON array of position keys
  rotations_json* string — JSON array of rotation keys
  scales_json* string — JSON array of scale keys

## animation.set_retargeter_rigs — Set the source and target IK Rigs (and optional preview meshes) on an existing IK Retargeter.
  asset_path* string — IK Retargeter asset path
  source_ik_rig_path* string — Source IK Rig asset path
  target_ik_rig_path* string — Target IK Rig asset path
  source_preview_mesh string — Source preview skeletal mesh path
  target_preview_mesh string — Target preview skeletal mesh path
  auto_map string (default fuzzy) — Chain auto-map mode for seeded ops: 'fuzzy' (default) or 'exact'

## blueprint.None — Add input/output parameters to a Blueprint function
  asset_path* string — Blueprint asset path
  function_name* string — Function graph name
  inputs array — Array of {name, type} objects for inputs
  outputs array — Array of {name, type} objects for outputs

## blueprint.add_component — Add a new component to a Blueprint's construction script. Returns variable_name, class, and parent.
  asset_path* string — Blueprint asset path
  component_class* string — Component class name (e.g. 'StaticMeshComponent')
  component_name string — Variable name for the new component
  parent string — Parent component variable name (attach as child)
  attach_socket string — Socket name on parent to attach to

## blueprint.add_data_table_row — Add a row to an existing DataTable. Values are a JSON object mapping column names to values (uses ImportText per field).
  asset_path* string — DataTable asset path, e.g. /Game/Data/DT_Weapons
  row_name* string — Row name / key
  values* object — JSON object of {column_name: value, ...}. Values are converted via ImportText.

## blueprint.add_event_dispatcher — Add a new event dispatcher (multicast delegate) to a Blueprint
  asset_path* string — Blueprint asset path
  name* string — Event dispatcher name

## blueprint.add_event_node — Add a native override event node (BeginPlay, Tick, EndPlay, etc.) or custom event to a Blueprint event graph. Alias table: BeginPlay->ReceiveBeginPlay, Tick->ReceiveTick, EndPlay->ReceiveEndPlay, BeginOverlap->ReceiveAc…
  asset_path* string — Blueprint asset path
  event_name* string — Event name: BeginPlay, Tick, EndPlay, BeginOverlap, EndOverlap, Hit, Destroyed, AnyDamage, PointDamage, RadialDamage, or a custom event name
  graph_name string — Event graph name (defaults to EventGraph)
  position array — Node position as [x, y] (default: [0, 0])
  replication string — Replication mode for custom events: none, multicast, server, client (default: none). Ignored for native override events.
  reliable bool — Use reliable replication for custom events (default: false). Ignored for native override events.

## blueprint.add_function — Add a new function graph to a Blueprint
  asset_path* string — Blueprint asset path
  name* string — Function name
  is_pure bool (default false) — Mark as pure (no exec pins)
  is_const bool (default false) — Mark as const
  is_static bool (default false) — Mark as static
  call_in_editor bool (default false) — Show 'Call In Editor' button
  category string — Function category
  description string — Function tooltip/description
  access string (default Public) — Access specifier: Public, Protected, or Private
  replication string — Replication mode: none, multicast, server, client (default: none)
  reliable bool — Use reliable replication (default: false)

## blueprint.add_local_variable — Add a local variable to a Blueprint function graph.
  asset_path* string — Blueprint asset path
  function_name* string — Function graph name
  name* string — Local variable name
  type* string — Pin type string
  default_value string — Default value as string

## blueprint.add_node — Add a new node to a Blueprint graph. Supports CallFunction, VariableGet, VariableSet, CustomEvent, Branch, Sequence, MacroInstance, SpawnActorFromClass, DynamicCast, Self, Return, MakeStruct, BreakStruct, SwitchOnEnum, …
  asset_path* string — Blueprint asset path
  node_type* string — Node type: CallFunction (or 'function'/'call'), VariableGet (or 'get'), VariableSet (or 'set'), CustomEvent (or 'event'), Branch (or 'if'),…
  graph_name string — Graph name (defaults to EventGraph)
  position array — Node position as [x, y] (default: [0, 0])
  function_name string — Function name for CallFunction nodes (e.g. PrintString) or CreateDelegate nodes (the function bound as the delegate handle — resolved on th…
  target_class string — Name of the class to search for the function being called (CallFunction) or the multicast delegate being bound (AddDelegate / RemoveDelegat…
  variable_name string — Variable name for VariableGet/VariableSet nodes
  event_name string — Custom event name for CustomEvent nodes
  macro_name string — Macro graph name for MacroInstance nodes
  macro_blueprint string — Blueprint asset path containing the macro (optional for MacroInstance)
  cast_class string — Class name for DynamicCast nodes (e.g. 'MyPawn'). Accepts A/U prefix or bare name.
  actor_class string — Actor class name for SpawnActorFromClass nodes
  struct_type string — Struct type for MakeStruct/BreakStruct nodes (e.g. 'Vector', 'Transform', 'FHitResult'). Accepts F prefix or bare name.
  enum_type string — Enum type for SwitchOnEnum nodes. Accepts a bare/E-prefixed short name (e.g. 'ECollisionChannel'), a /Script path (e.g. '/Script/Engine.ECo…
  format string — Format string for FormatText nodes (e.g. 'Hello {Name}, you have {Count} items'). Argument pins are auto-created from {ArgName} patterns.
  num_entries integer — Number of input entries for MakeArray nodes (default: 1)
  replication string — Replication mode for CustomEvent nodes: none, multicast, server, client (default: none)
  reliable bool — Use reliable replication for CustomEvent nodes (default: false)
  component_name string — Component variable name (SCS/native subobject) for ComponentBoundEvent nodes
  delegate_property_name string — Multicast delegate property name. Required for ComponentBoundEvent (resolved on component class) and AddDelegate / RemoveDelegate / ClearDe…

## blueprint.add_nodes_bulk — Place multiple nodes in one transaction. Returns a temp_id -> node_id mapping so callers can immediately reference created nodes in connect_pins_bulk. Each entry: { temp_id, node_type, function_name?, target_class?, var…
  asset_path* string — Blueprint asset path
  nodes* array — Array of node descriptors: { temp_id, node_type, function_name?, target_class?, variable_name?, position? }
  graph_name string — Graph name (defaults to EventGraph)
  auto_layout boolean — Auto-position nodes in a 5-column grid (200px horizontal, 100px vertical spacing). Ignored if position is set per node. Default: false.

## blueprint.add_property_access — Author a VariableGet (or VariableSet if is_setter) node that reads/writes a UPROPERTY on an ARBITRARY foreign class — not just the Blueprint's own variables. member_class is resolved by string (FindFirstObject, native-f…
  asset_path* string — Blueprint asset path
  member_class* string — Class that owns the property (e.g. 'Item', 'UItem', 'AActor'). Resolved by string, native-first; accepts U/A prefix or bare name.
  member_name* string — Name of the UPROPERTY to read/write (e.g. 'Icon')
  graph_name string — Graph name (defaults to EventGraph)
  is_setter bool — If true, creates a VariableSet (write) node; otherwise a VariableGet (read) node. Default: false.
  position array — Node position as [x, y] (default: [0, 0])

## blueprint.add_property_access_node — Author a GENUINE thread-safe Property Access node (UK2Node_PropertyAccess) into a Blueprint/AnimBP graph. Unlike add_property_access (which emits a foreign-member VariableGet with a 'self' object pin — itself NON-thread…
  asset_path* string — Blueprint / Animation Blueprint asset path
  path* array — Verbatim resolution chain (array of strings). Element 0 = member/function on the access root (e.g. 'CharacterProperties' or 'GetDeltaSecond…
  graph_name string — Target graph/function name. Defaults to the first ubergraph if omitted; pass a function name (e.g. 'BlueprintThreadSafeUpdateAnimation' or …
  context_id string — Optional Property Access ContextId (FName). Leave empty for the default unbatched worker-thread context (matches the Game Animation Sample).
  position array — Node position as [x, y] (default: [0, 0])

## blueprint.add_replicated_variable — Add a replicated member variable to a Blueprint with full network replication settings. Optionally creates an OnRep_ notification function. Requires the Blueprint's parent class to support replication.
  asset_path* string — Blueprint asset path
  variable_name* string — Variable name
  type* string — Pin type string (e.g. bool, int, float, object:Actor)
  replication_condition string (default None) — ELifetimeCondition: None, InitialOnly, OwnerOnly, SkipOwner, SimulatedOnly, AutonomousOnly, SimulatedOrPhysics, InitialOrOwner, Custom (def…
  create_on_rep boolean (default false) — Create an OnRep_<VarName> function stub and link it to the variable (default: false)
  default_value string — Default value as string
  category string — Category for organization in the Blueprint editor

## blueprint.add_variable — Add a new member variable to a Blueprint. Supports all primitive types, structs, enums, objects, and container types (array:, set:, map:).
  asset_path* string — Blueprint asset path
  name* string — Variable name
  type* string — Pin type string (e.g. bool, int, float, string, struct:Vector, object:Actor, array:float)
  default_value string — Default value as string
  category string — Category for organization in the Blueprint editor
  instance_editable boolean (default true) — Whether the variable is editable on instances (default: true)
  blueprint_read_only boolean (default false) — Whether the variable is read-only in Blueprints (default: false)
  expose_on_spawn boolean (default false) — Expose as a spawn parameter (default: false)
  replicated boolean (default false) — Replicate this variable over the network (default: false)
  transient boolean (default false) — Mark as transient — not serialized (default: false)

## blueprint.batch_execute — Execute multiple Blueprint write operations on a single asset in one transaction. Each operation is { "op": "action_name", ...action_params_minus_asset_path }. Supported ops: add_node, remove_node, connect_pins, disconn…
  asset_path* string — Blueprint asset path
  operations* array — Array of operation objects: { op, ...params }
  compile_on_complete boolean — Compile the Blueprint after all operations complete (default: false)
  stop_on_error boolean — Stop processing on first failed operation (default: false)
  graph_name string — Default graph for all operations; an op's own graph_name overrides it (default: the EventGraph)

## blueprint.batch_spawn_blueprint_actors — Spawn multiple Blueprint actors in a grid or linear pattern. Continues on per-actor failure.
  blueprint* string — Blueprint asset path
  count* integer — Number of actors to spawn (1-1000)
  pattern string (default grid) — Layout: grid or linear
  origin array|object (default [0,0,0]) — Origin point [x,y,z]
  spacing number (default 200) — Center-to-center spacing in cm
  columns integer (default 10) — Columns per row (grid only)
  direction array|object (default [1,0,0]) — Direction vector for linear pattern
  rotation array|object (default [0,0,0]) — Rotation for all actors
  scale array|object (default [1,1,1]) — Scale for all actors
  label_prefix string — Label prefix; actors get prefix_0, prefix_1, etc.
  folder string (default Blueprints) — Outliner folder
  properties object — Properties set on every actor
  tags array — Tags added to every actor
  sublevel string — Target streaming sublevel name
  mobility string — Root component mobility: static, stationary, movable
  select boolean (default false) — Select spawned actors

## blueprint.build_blueprint_from_spec — Declarative one-shot Blueprint graph builder. Takes a JSON spec and creates variables, components, nodes, connections, and pin defaults in a single transaction. Modeled after build_material_graph. Nodes use caller-defin…
  asset_path* string — Blueprint asset path (must already exist)
  graph_name string — Target graph name (defaults to EventGraph)
  variables array — Array of variable descriptors: [{name, type, default_value?, category?, instance_editable?, blueprint_read_only?, expose_on_spawn?, replica…
  components array — Array of component descriptors: [{name, class, parent?}]
  nodes array — Array of node descriptors: [{id, type, position?, function_name?, target_class?, variable_name?, event_name?, macro_name?, macro_blueprint?…
  connections array — Array of connection descriptors: [{source, source_pin, target, target_pin}] — source/target use the 'id' from nodes array
  pin_defaults array — Array of pin default descriptors: [{node_id, pin_name, value}] — node_id uses the 'id' from nodes array
  auto_compile boolean — Compile the Blueprint after building (default: false)

## blueprint.compile_blueprint — Compile a Blueprint asset and return errors, warnings, and compile status.
  asset_path* string — Blueprint asset path

## blueprint.connect_pins — Connect two pins in a Blueprint graph. Source pin must be an output, target pin must be an input (or vice versa — the schema will sort it out).
  asset_path* string — Blueprint asset path
  source_node* string — Source node ID
  source_pin* string — Source pin name
  target_node* string — Target node ID
  target_pin* string — Target pin name
  graph_name string — Graph name (searches all graphs if omitted)

## blueprint.connect_pins_bulk — Wire multiple pin connections in one transaction. Each entry: { source_node, source_pin, target_node, target_pin }. Returns per-connection success/error.
  asset_path* string — Blueprint asset path
  connections* array — Array of connection descriptors: { source_node, source_pin, target_node, target_pin }
  graph_name string — Graph name (searches all graphs if omitted)

## blueprint.copy_nodes — Copy nodes from one graph to another using UE native T3D export/import. Internal connections are preserved; external connections are silently dropped. Node IDs change on copy.
  source_asset* string — Source Blueprint asset path
  source_graph string — Source graph name (defaults to first event graph)
  node_ids* array — Array of node ID strings to copy
  target_asset* string — Target Blueprint asset path
  target_graph string — Target graph name (defaults to first event graph)

## blueprint.create_blueprint — Create a new Blueprint asset at the given save path with the specified parent class and blueprint type.
  save_path* string — Asset save path, e.g. /Game/Test/BP_MyActor
  parent_class* string — Parent class name, e.g. Actor, Pawn, Character
  blueprint_type string (default Normal) — Blueprint type: Normal, Const, MacroLibrary, Interface, FunctionLibrary (default: Normal)
  skip_save boolean (default false) — Skip the synchronous package save — Blueprint exists in-memory and can be saved later (default: false)

## blueprint.create_data_asset — Create a raw UObject asset (NOT a Blueprint). Use for DataAssets, MaterialParameterCollections, PhysicalMaterials, CurveFloats, and any UObject-derived class that needs to exist as a direct instance rather than a Bluepr…
  save_path* string — Asset save path, e.g. /Game/Data/DA_ResponseMap
  class_name* string — UObject class name, e.g. CarnageFXResponseMap, MaterialParameterCollection, PhysicalMaterial, CurveFloat. Can also use full path /Script/Mo…
  skip_save boolean (default false) — Skip synchronous package save (default: false)

## blueprint.create_data_table — Create a new DataTable asset backed by the specified row struct (UScriptStruct). The struct must already exist (native or user-defined).
  save_path* string — Asset save path, e.g. /Game/Data/DT_Weapons
  row_struct* string — Name of the row struct, e.g. FMyRowStruct, MyRowStruct, or a full path like /Script/MyModule.MyRowStruct

## blueprint.create_user_defined_enum — Create a new User Defined Enum asset with the specified enumerator values.
  save_path* string — Asset save path, e.g. /Game/Data/E_MyEnum
  values* array — Array of enumerator display name strings, e.g. ["Idle", "Running", "Jumping"]

## blueprint.create_user_defined_struct — Create a new User Defined Struct asset with the specified fields. Each field has a name, type (same type strings as add_variable), and optional default_value.
  save_path* string — Asset save path, e.g. /Game/Data/S_MyStruct
  fields* array — Array of field objects: [{name, type, default_value?}]. Type uses same strings as add_variable (bool, int, float, string, name, text, Vecto…

## blueprint.describe_data_table_schema — Return ONLY a DataTable's row schema (no row data). Useful for planning edits to a large table. Returns row_struct, row_struct_path, and an FSchemaDescriptor-shaped 'schema' array.
  asset_path* string — DataTable asset path, e.g. /Game/Data/DT_Weapons

## blueprint.disconnect_pins — Disconnect a pin on a Blueprint node. If target_node and target_pin are omitted, all connections on the pin are broken.
  asset_path* string — Blueprint asset path
  node_id* string — Node ID containing the pin to disconnect
  pin_name* string — Pin name to disconnect
  target_node string — Target node ID — if provided, only breaks the connection to this specific node
  target_pin string — Target pin name — required if target_node is specified
  graph_name string — Graph name (searches all graphs if omitted)

## blueprint.export_data_table — Export an entire DataTable as a JSON or CSV text blob for token-efficient round-trip editing. Returns row_struct, row_struct_path, total_rows, format, and 'text'. By default nested structs export as clean JSON objects (…
  asset_path* string — DataTable asset path
  format string (default json) — "json" (default) or "csv".
  use_json_objects boolean (default true) — Export nested structs as JSON objects rather than ExportText blobs (JSON only). Default true.
  simple_text boolean (default false) — Export text properties as display strings rather than lossless form. Default false.

## blueprint.finalize_create_delegate — Run the engine's own resolution logic (UK2Node_CreateDelegate::HandleAnyChangeWithoutNotifying) on an already-wired CreateDelegate node. Required after blueprint.add_node(CreateDelegate) + connect_pins wire the node's s…
  asset_path* string — Blueprint asset path
  graph_name string — Graph to search (narrows node lookup when node_id is omitted, or disambiguates multiple CreateDelegate nodes)
  node_id string — CreateDelegate node ID (from add_node's response node_id field). Preferred/reliable lookup. If omitted, all CreateDelegate nodes in the Blu…
  function_name string — The function/event this delegate should bind to (e.g. 'OnBuildMenuBlueprintSelected_Handler'). Always pass this — it is re-applied to the n…

## blueprint.get_blueprint_info — Comprehensive Blueprint overview in one call: parent class, graph names, tick/construction script presence, variable/function/component/interface counts, and compile status. component_count is SCS-added components only;…
  asset_path* string — Blueprint asset path

## blueprint.get_cdo_properties — Read all CDO (Class Default Object) properties from a Blueprint or any UObject asset. Essential for GameplayEffects (Duration, Modifiers, Tags, Stacking), AbilitySets, InputActions, and any asset whose config is stored …
  asset_path* string — Asset path (e.g. /Game/Blueprints/BP_MyActor or /Game/Data/DA_MyData)
  category_filter string — Only include properties whose category contains this string
  include_parent_defaults boolean — If true, include properties inherited from native parent class (default: true)
  owner_class_filter string — Only include properties whose owner_class name contains this string (case-insensitive). Lets you skip everything inherited from AActor/APaw…
  name_pattern string — Only include properties whose name contains this substring (case-insensitive)
  exclude_categories array — List of category names to skip entirely (case-insensitive exact match — e.g. ["Replication", "Cooking", "HLOD", "Lighting"])

## blueprint.get_component_details — Get full property dump for a specific component in a Blueprint. Resolves Blueprint-added (SCS) components, inherited native components declared in the C++ parent class, and components inherited from a parent Blueprint; …
  asset_path* string — Blueprint asset path
  component_name* string — Component variable name

## blueprint.get_components — Get component hierarchy for a Blueprint — names, classes, parent-child tree, attach sockets. Also returns inherited_native_components (native subobjects read off THIS Blueprint's own CDO, so they carry this Blueprint's …
  asset_path* string — Blueprint asset path

## blueprint.get_data_table_rows — Read rows from a DataTable. Returns all rows, or a single row if row_name is specified.
  asset_path* string — DataTable asset path, e.g. /Game/Data/DT_Weapons
  row_name string — If provided, return only this row. Otherwise return all rows.

## blueprint.get_execution_flow — Get linearized execution flow from an entry point
  asset_path* string — Blueprint asset path
  entry_point* string — Event or function entry point name

## blueprint.get_function_signature — Get full signature for a single named function: inputs, outputs, flags, local variables, and source (blueprint/native/interface). Use include_inherited to also search parent class native functions.
  asset_path* string — Blueprint asset path
  function_name* string — Function name to look up
  include_inherited boolean — Also search inherited native functions on the parent class (default: false)

## blueprint.get_functions — Get all Blueprint-defined functions with inputs, outputs, metadata, and flags
  asset_path* string — Blueprint asset path

## blueprint.get_graph_data — Get full graph data with all nodes, pins, and connections. Optional node_class_filter to include only matching node classes.
  asset_path* string — Blueprint asset path
  graph_name string — Graph name (defaults to first event graph)
  node_class_filter string — Only include nodes whose class contains this substring

## blueprint.get_graph_summary — Get lightweight graph summary with node id/class/title and exec-only connections. Returns all graphs when graph_name is empty.
  asset_path* string — Blueprint asset path
  graph_name string — Graph name (returns all graphs when empty)

## blueprint.get_inherited_component_override — READ-ONLY: report the effective value(s) of a component override on a child Blueprint. Resolves the effective component template (this Blueprint's own CDO subobject for an inherited native component like a Character's m…
  bp_path* string — Child Blueprint asset path
  component* string — Component variable name or alias (Mesh/SkeletalMesh, StaticMesh, CharacterMovement/Movement, Capsule/CapsuleComponent, Root/RootComponent)
  property_name string — Single property to read; if omitted, a default set is reported (AnimClass, SkeletalMesh, AnimationMode)

## blueprint.get_interface_functions — Query the function signatures required by a Blueprint interface. Works for both C++ and Blueprint interfaces.
  interface_class* string — Interface class name (e.g. BPI_Interactable or IInteractable)

## blueprint.get_node_details — Get full pin dump for a single node by node_id. Returns same data as get_graph_data for one node, including orphaned pin flag.
  asset_path* string — Blueprint asset path
  node_id* string — Node ID (from get_graph_data or add_node response)
  graph_name string — Graph name to narrow search (searches all graphs if omitted)

## blueprint.get_parent_class — Get parent class info, Blueprint type, and class flags for a Blueprint
  asset_path* string — Blueprint asset path

## blueprint.get_variables — Get all variables defined in a Blueprint. Set include_bind_widgets=true on a Widget Blueprint to also enumerate, under a 'bind_widgets' array, both C++ BindWidget/BindWidgetOptional references (source=bind_widget_meta) …
  asset_path* string — Blueprint asset path
  include_bind_widgets boolean — Widget Blueprints only: also list designer-bound widgets in 'bind_widgets' -- C++ BindWidget refs (source=bind_widget_meta) and bIsVariable…

## blueprint.import_data_table — Import a JSON or CSV text blob into a DataTable. REPLACES the entire row set (rows not present in the blob are deleted by design). The DataTable must already have a RowStruct set. mode must be "replace". Refreshes any o…
  asset_path* string — DataTable asset path
  text* string — The JSON or CSV blob to import. REPLACES all existing rows.
  format string (default json) — "json" (default) or "csv".
  mode string (default replace) — Only "replace" is supported (import wipes existing rows first). Must be passed explicitly.
  save boolean (default false) — If true, save the package after importing.

## blueprint.list_graphs — List all graphs in a Blueprint asset
  asset_path* string — Blueprint asset path

## blueprint.override_parent_function — Author a Blueprint override of an overridable parent function (BlueprintImplementableEvent / BlueprintNativeEvent), including those that RETURN a value (e.g. UCommonActivatableWidget::BP_GetDesiredFocusTarget -> UWidget…
  asset_path* string — Blueprint asset path
  parent_function_name* string — Name of the overridable parent function

## blueprint.read_data_table — Read a DataTable's full contents plus its inline row schema. Returns the row struct, total_rows, an FSchemaDescriptor-shaped 'schema' array (field type_name, import_text_form, enum_values, range, nested children), and a…
  asset_path* string — DataTable asset path, e.g. /Game/Data/DT_Weapons
  include_schema boolean (default true) — Include the inline row-field schema array (default true).
  row_name string — If provided, return only this row. Otherwise return all rows.

## blueprint.remove_function — Remove a function graph from a Blueprint by name
  asset_path* string — Blueprint asset path
  name* string — Function name to remove

## blueprint.remove_interface — Remove an interface from a Blueprint
  asset_path* string — Blueprint asset path
  interface_class* string — Interface class name to remove
  preserve_functions bool (default false) — Keep stub functions after removal

## blueprint.remove_node — Remove a node from a Blueprint graph by node ID.
  asset_path* string — Blueprint asset path
  node_id* string — Node ID (from get_nodes or add_node response)
  graph_name string — Graph name (searches all graphs if omitted)

## blueprint.rename_function — Rename an existing function graph in a Blueprint
  asset_path* string — Blueprint asset path
  old_name* string — Current function name
  new_name* string — New function name

## blueprint.rename_variable — Rename a member variable in a Blueprint, updating all references in graphs.
  asset_path* string — Blueprint asset path
  old_name* string — Current variable name
  new_name* string — New variable name

## blueprint.reparent_component — Change the parent of a component in a Blueprint. Pass empty string for new_parent to make it a root component.
  asset_path* string — Blueprint asset path
  component_name* string — Component variable name to reparent
  new_parent* string — New parent component variable name, or empty string to attach to root
  attach_socket string — Socket name on new parent to attach to

## blueprint.resolve_node — Dry-run node creation — returns resolved type, class, function, and all pins with types/defaults/direction without modifying any asset. Useful for discovering what pins a node will have before adding it.
  node_type* string — Node type: CallFunction, VariableGet, VariableSet, Branch, CustomEvent, SwitchOnEnum, ComponentBoundEvent, AddDelegate, RemoveDelegate, Cle…
  function_name string — Function name for CallFunction nodes
  target_class string — Class to search for the function (CallFunction) or delegate (AddDelegate / RemoveDelegate / ClearDelegate / CallDelegate). For CallFunction…
  enum_type string — Enum type for SwitchOnEnum dry-run. Accepts a bare/E-prefixed short name, a /Script path, or a UserDefinedEnum asset path (loaded on demand…
  variable_name string — Variable name hint for VariableGet/VariableSet (uses wildcard if omitted)
  replication string — Replication mode for CustomEvent: none, multicast, server, client
  reliable bool — Use reliable replication for CustomEvent
  asset_path string — Blueprint asset path (required for ComponentBoundEvent and AddDelegate / RemoveDelegate / ClearDelegate / CallDelegate self-context dry-run…
  component_name string — Component variable name for ComponentBoundEvent dry-run
  delegate_property_name string — Multicast delegate name for ComponentBoundEvent / AddDelegate / RemoveDelegate / ClearDelegate / CallDelegate dry-run

## blueprint.scaffold_interface_implementation — Add an interface to a Blueprint AND create all stub function graphs in one call. Returns the interface name and list of created graphs. Much more useful than implement_interface alone — this one actually wires up the st…
  asset_path* string — Blueprint asset path
  interface_class* string — Interface class name (e.g. BPI_Interactable or IBpi_Interactable)

## blueprint.scaffold_locomotion_anim_values — COMPOSITE: ensure a thread-safe update/function graph exists, create the locomotion anim variables (Velocity vector, GroundSpeed float, Acceleration vector, bIsMoving bool, bIsCrouched bool), then author a FULLY WIRED n…
  abp_path* string — Animation Blueprint asset path
  target_graph string — Thread-safe graph/function to author into (default 'BlueprintThreadSafeUpdateAnimation'). Pass a function name like 'UpdateEssentialValues'…
  velocity_var string (default Velocity) — Name override for the Velocity vector var (default 'Velocity')
  ground_speed_var string (default GroundSpeed) — Name override for the GroundSpeed float var (default 'GroundSpeed')
  acceleration_var string (default Acceleration) — Name override for the Acceleration vector var (default 'Acceleration')
  is_moving_var string (default bIsMoving) — Name override for the bIsMoving bool var (default 'bIsMoving')
  is_crouched_var string (default bIsCrouched) — Name override for the bIsCrouched bool var (default 'bIsCrouched')
  velocity_path array — Property Access path (array of strings) for Velocity. Default: ['CharacterProperties','Velocity'] (Game Animation Sample). For a UserDefine…
  acceleration_path array — Property Access path for Acceleration. Default: ['CharacterProperties','InputAcceleration'].
  crouch_path array — Property Access path for the crouch SOURCE (must resolve to a BOOL to feed the bIsCrouched var cleanly). NO default — the Game Animation Sa…

## blueprint.scaffold_locomotion_input — Create a UInputMappingContext asset + one UInputAction asset per 'actions' entry, then add event-graph nodes binding each action to AddMovementInput. Reuses add_event_node / add_nodes_bulk / connect_pins_bulk. Marks the…
  bp_path* string — Character Blueprint asset path
  imc_path* string — Asset path for the new InputMappingContext
  actions* array — Array of {name, value_type} — value_type one of Digital(bool)/Axis1D/Axis2D/Axis3D. One UInputAction asset created per entry.

## blueprint.search_nodes — Search for nodes in a Blueprint by title, function name, or input-pin default value (finds string-bound callers like SetTimerByFunctionName targets). Searches ALL graphs recursively, including collapsed-graph composites…
  asset_path* string — Blueprint asset path
  query* string — Search string matched (case-insensitive contains) against node titles, function names, and input-pin default values

## blueprint.seed_data_asset — Create AND populate a UObject DataAsset in one call: create_data_asset's body plus a reflection-walker fill of the supplied property 'tree'. Supports dry_run (validate before creating) and strict. Returns asset_path, ac…
  save_path* string — Asset save path, e.g. /Game/Data/DA_HealingPotion
  class_name* string — UObject class name (same resolution as create_data_asset).
  tree* object — Nested JSON object of properties to walk against the new asset's reflection schema.
  dry_run boolean (default false) — If true, validate the tree against the class WITHOUT creating the asset.
  strict boolean (default false) — If true, promote silent drops / unknown fields / enum misses to hard errors.
  skip_save boolean (default false) — Skip synchronous package save (default: false).
  read_back_values boolean (default false) — If true, after the write succeeds re-read the written top-level fields' live values and attach them as 'values': { field: <json> }. Pure re…

## blueprint.set_cdo_properties — Bulk-fill multiple CDO properties from a JSON tree in a single transaction. Supports nested structs, arrays, maps, sets, enums, and soft-object refs. Supports dry_run + strict. Phase 1 pilot of the bulk_fill framework.
  asset_path* string — Blueprint or UObject asset path (e.g. /Game/Data/DA_MyData)
  properties* object — Nested JSON object — keys are property names, values are scalars / structs / arrays / maps / sets per UPROPERTY layout.
  dry_run boolean (default false) — If true, validate only — emit the would-be writes but do not persist.
  strict boolean (default false) — If true, promote silent drops / clamps / unknown-fields to hard errors.

## blueprint.set_cdo_property — Set a property value on a Blueprint CDO or UObject asset (DataAsset, GameplayEffect, etc.). Write counterpart to get_cdo_properties. Supports numeric, boolean, string, enum, struct, and any type that supports ImportText.
  asset_path* string — Blueprint or UObject asset path (e.g. /Game/Data/DA_MyData)
  property_name* string — Property name to set (case-insensitive fallback)
  value* any — New value — string, number, bool, or ImportText format for structs (e.g. "(X=1.0,Y=2.0,Z=3.0)")
  dry_run boolean (default false) — If true, validate only — emit the would-be write but do not persist. Phase 1.
  strict boolean (default false) — If true, promote silent drops / clamps / unknown-fields to hard errors. Phase 1.

## blueprint.set_component_property — Set a property on a component template in a Blueprint via text import. Writes to Blueprint-added (SCS) components, inherited native components, and components inherited from a parent Blueprint — the last get an Inherita…
  asset_path* string — Blueprint asset path
  component_name* string — Component variable name or alias (Mesh, StaticMesh, CharacterMovement, Capsule, Root)
  property_name* string — Property name on the component
  value* string — Value as text (same format as copy/paste in Details panel)

## blueprint.set_custom_event_params — Add input parameters to a Blueprint Custom Event node (K2Node_CustomEvent) in the event graph. Unlike set_function_params, this targets event nodes, not function graphs.
  asset_path* string — Blueprint asset path
  event_name* string — Custom Event node name
  inputs array — Array of {name, type} objects for inputs

## blueprint.set_data_table_rows — Bulk add/update DataTable rows in one call. Each row is {row_name, values:{field:value}, mode?}. Mode is upsert (default), add, or update. Supports dry_run (validate only) and strict (promote coercion/unknown-field/enum…
  asset_path* string — DataTable asset path, e.g. /Game/Data/DT_Weapons
  rows* array — Array of {row_name, values:{field:value}, mode?:"upsert"|"add"|"update"}. Default mode upsert.
  dry_run boolean (default false) — If true, validate only — emit would-be writes but do not persist.
  strict boolean (default false) — If true, promote silent drops / unknown fields / enum misses to hard errors.
  save boolean (default false) — If true, save the package after applying.

## blueprint.set_event_dispatcher_params — Set (replace) the signature parameters on an event dispatcher. Existing params are cleared and replaced with the new list.
  asset_path* string — Blueprint asset path
  dispatcher_name* string — Event dispatcher name (without _Signature suffix)
  params* array — Array of {name, type} objects for the new signature

## blueprint.set_function_params — Add input/output parameters to a Blueprint function
  asset_path* string — Blueprint asset path
  function_name* string — Function graph name
  inputs array — Array of {name, type} objects for inputs
  outputs array — Array of {name, type} objects for outputs

## blueprint.set_function_thread_safe — Set (or clear) the 'Thread Safe' flag on an existing Blueprint function graph. Sets FKismetUserDeclaredFunctionMetadata::bThreadSafe on the function's entry node and recompiles. Required for functions called from Bluepr…
  asset_path* string — Blueprint asset path
  function_name* string — Function graph name
  thread_safe bool (default true) — Set the Thread Safe flag (true) or clear it (false)

## blueprint.set_node_position — Move a Blueprint graph node to a new position.
  asset_path* string — Blueprint asset path
  node_id* string — Node ID
  position* array — New position as [x, y]
  graph_name string — Graph name (searches all graphs if omitted)

## blueprint.set_pin_default — Set the default value of a pin on a Blueprint node.
  asset_path* string — Blueprint asset path
  node_id* string — Node ID
  pin_name* string — Pin name
  value* string — Default value as string. For class-typed (PC_Class) and object-typed (PC_Object) pins, accepts native class names ('APawn'), object/class p…
  graph_name string — Graph name (searches all graphs if omitted)

## blueprint.set_pin_defaults_bulk — Set multiple pin default values in one transaction. Each entry: { node_id, pin_name, value }. Returns per-entry success/error.
  asset_path* string — Blueprint asset path
  defaults* array — Array of pin default descriptors: { node_id, pin_name, value }
  graph_name string — Graph name (searches all graphs if omitted)

## blueprint.set_property_at_path — Set a SINGLE value at a nested property path on a Blueprint CDO or UObject asset (DataAsset, GameplayEffect, etc.) via generic reflection. Path is dotted + bracket: '.' descends into struct members, '[N]' indexes an arr…
  asset_path* string — Blueprint or UObject asset path (e.g. /Game/Data/DA_MyData)
  path* string — Dotted+bracket property path, e.g. 'Standing.Gaits[Jog].Starts.Forward'. '.'=struct member, '[N]'=array index, '[Key]'=map key.
  value* any — New leaf value — string / number / bool, an enum name, a soft/hard object asset path, or ImportText / JSON for a struct leaf.
  dry_run boolean (default false) — If true, resolve the path and validate the leaf write but do not persist.
  strict boolean (default false) — If true, promote silent drops / clamps to hard errors.
  create_missing_keys boolean (default false) — If true, a '[Key]' segment whose map key is absent is added with a default-initialised value before writing the leaf. Default: error on a m…
  save boolean (default false) — If true, save the asset package to disk after the write (UPackage::SavePackage). Default: MarkPackageDirty only.

## blueprint.set_variable_defaults — Update metadata and flags on an existing Blueprint variable. Only provided fields are changed.
  asset_path* string — Blueprint asset path
  name* string — Variable name
  default_value string — New default value as string
  category string — New category
  instance_editable boolean — Whether editable on instances
  blueprint_read_only boolean — Whether read-only in Blueprints
  expose_on_spawn boolean — Expose as spawn parameter
  replicated boolean — Replicate over network
  transient boolean — Mark as transient (not serialized)
  save_game boolean — Include in save game serialization

## blueprint.set_variable_type — Change the type of an existing member variable. All graph nodes referencing the variable will be refreshed.
  asset_path* string — Blueprint asset path
  name* string — Variable name
  type* string — New pin type string (e.g. bool, float, struct:Vector, array:int)

## blueprint.spawn_blueprint_actor — Spawn a Blueprint actor into the editor world with transform, properties, tags, sublevel, and mobility control.
  blueprint* string — Blueprint asset path (e.g. /Game/Blueprints/BP_Lamp)
  location array|object (default [0,0,0]) — Spawn location [x,y,z] or {x,y,z}
  rotation array|object (default [0,0,0]) — Spawn rotation [pitch,yaw,roll]
  scale array|object (default [1,1,1]) — Spawn scale [x,y,z]
  label string — Actor label (display name)
  folder string (default Blueprints) — Outliner folder path
  properties object — Properties to set via reflection {name: value}
  tags array — Array of string tags to add to actor
  sublevel string — Target streaming sublevel name
  mobility string — Root component mobility: static, stationary, movable
  select boolean (default true) — Select actor after spawn

## blueprint.validate_blueprint — Validate a Blueprint without compiling — returns unused variables, disconnected nodes, and compiler messages already stored on nodes.
  asset_path* string — Blueprint asset path

## bulk_fill.apply — Apply a JSON-tree fill to an asset via the target namespace's adapter. Supports dry_run + strict.
  target_namespace* string — Adapter namespace ('blueprint', 'gas', 'inventory', 'ui', 'ai', 'niagara', 'material', 'audio', 'mesh', 'animation', 'logicdriver', 'combog…
  target* string — Asset path or adapter-defined target identifier (e.g. '/Game/Items/DA_HealingPotion').
  tree* object — Nested JSON object of properties to walk against the target's reflection schema.
  dry_run boolean (default false) — If true, validate only — emit the would-be writes but do not persist.
  strict boolean (default false) — If true, promote silent drops / clamps / unknown-fields to hard errors.

## cppreflect.get_uclass — Return one UCLASS row plus all UPROPERTYs, all UFUNCTIONs, and the parent-class chain. `class_name` is the C++ symbol with prefix (e.g. "ALeviathanCharacterBase"). Returns null when the class is not in the reflection in…
  class_name* string — C++ class symbol (e.g. ALeviathanCharacterBase)
  module_name string — Optional module filter when the class exists in multiple modules

## editor.None — Execute a Python command, statement, or file via IPythonScriptPlugin::ExecPythonCommandEx. Returns success, stdout/stderr captured by Python, and (for evaluate_statement mode) the evaluated result.
  command* string — Python source. May be inline code, a single statement, or a file path with optional space-separated args (when mode=execute_file).
  mode string (default execute_file) — Execution mode: execute_file (default — multi-statement script or file with args), execute_statement (single stmt, prints result), evaluate…
  unattended bool (default false) — Set GIsRunningUnattendedScript=true to suppress UI dialogs.
  file_scope string (default private) — Scope for execute_file: private (isolated locals/globals — default), public (shared with REPL console).

## editor.author_map_settings — Author map-level settings on the currently-open (or a specified) editor map: set the WorldSettings GameMode Override (AWorldSettings::DefaultGameMode), spawn APlayerStart actors at given transforms, and optionally spawn…
  path string — UWorld to author. Omitted = the currently-open editor world. If provided, the map is loaded as the active editor world first.
  game_mode_override string — Class path for the GameMode Override (AWorldSettings::DefaultGameMode). Blueprint paths are `_C` normalized; native paths (/Script/...) wor…
  player_starts array — [{location:[x,y,z], rotation:[p,y,r], name:"Start_0"}, ...] spawned as APlayerStart actors.
  actors array — [{class:"/Game/.../BP_Foo.BP_Foo_C" or /Script/Engine.PointLight, location:[x,y,z], rotation:[p,y,r], folder:"...", properties:{...}}, ...]…
  save bool (default false) — Save the authored map package after applying. Default false.

## editor.create_empty_map — Create a fully blank UWorld asset at the given /Game/... path. Saves immediately. Default template is 'blank' (zero actors).
  path* string — Asset path under /Game/... where the new UWorld is saved (e.g. /Game/Tests/Monolith/Audio/Map_Test)
  map_template string (default blank) — Template variant: 'blank' (default). Reserved: 'vr_basic', 'thirdperson_basic' — return error in v1; UE 5.7 templates are populated client-…

## editor.pie_call_function — Call a BlueprintCallable function/event on a resolved live PIE object, marshalling JSON args into the UFunction parameter frame and invoking via ProcessEvent. MUTATES LIVE PIE STATE — this executes real gameplay code, i…
  actor_label string — Exact editor label of the target actor.
  object_name string — Exact object name of the target actor.
  class_name string — Substring of the target actor's class name. One of actor_label/object_name/class_name is required.
  component_name string — Component on the resolved actor to call the function on.
  anim_instance bool (default false) — If true, call on the skeletal mesh component's active anim instance.
  function* string — UFunction name to call (FindFunctionByName).
  args object — JSON object of arguments keyed by parameter name. Struct params take a nested JSON object keyed by friendly field names. v1: top-level + on…
  allow_non_callable bool (default false) — If true, allow functions that are not flagged FUNC_BlueprintCallable. Net/latent functions are still rejected. Default false.

## editor.pie_get_object_properties — Read live UPROPERTY values off a resolved Play-In-Editor object by dotted member path. Resolve the target with actor_label / object_name / class_name (substring); optionally hop to a named component_name, or set anim_in…
  actor_label string — Exact editor (Outliner) label of the target actor.
  object_name string — Exact object name of the target actor.
  class_name string — Substring of the target actor's class name (first match wins). One of actor_label/object_name/class_name is required.
  component_name string — Name of a component on the resolved actor to read from instead of the actor itself.
  anim_instance bool (default false) — If true, read from the (named or first) skeletal mesh component's active anim instance.
  properties* array — Dotted member paths to read (e.g. ['Movement.Speed','CharacterProperties.OrientationIntent']). Struct-member traversal only; array/map inde…

## editor.pie_inject_input_action — Inject a value for an Enhanced Input action into a live PIE local player (UEnhancedInputLocalPlayerSubsystem::InjectInputForAction), running that action's modifiers and triggers as if real input arrived. MUTATES LIVE PI…
  input_action* string — UInputAction asset path (/Game/...) or short asset name.
  value* any — Value to inject: bool (Boolean), number (Axis1D), array[2] (Axis2D), or array[3] (Axis3D).
  player_index number (default 0) — Local player index (default 0).
  repeat_frames number (default 1) — Inject the value each frame for this many frames (default 1 = single injection).

## editor.run_pie_smoke — Start an ASYNC PIE smoke session on a map and RETURN IMMEDIATELY. Loads the map, starts PIE (synchronously), emits a UE_LOG marker, and registers a session that the editor's REAL frame loop advances over real frames (sa…
  map string — Level asset path to load before PIE (e.g. /Game/Tests/Monolith/Maps/M_Harness). Omit to use the current editor level.
  marker string (default MONOLITH_SMOKE) — Marker token emitted to the log; post-marker pattern matching counts only lines after it. Default MONOLITH_SMOKE.
  duration number (default 5) — Seconds the editor loop advances PIE before the session auto-completes (clamped 0-120). Default 5.
  sample_vars array — AnimInstance variable names sampled each frame. Default [GroundSpeed, bShouldMove, DesiredYawDelta].
  pawn_class string — Substring of the target pawn's class name to sample (resolves a matching pawn). Omit to use the first player controller's pawn.
  console_script array — Console command strings run on the PIE world at start (e.g. ["WalkLoop"]).
  python_script string — Python source run via IPythonScriptPlugin at start.
  log_patterns array|object — Post-marker patterns. FLAT ARRAY (legacy) = must_absent substrings. OBJECT (grouped) = {must_absent:[...], must_present:[...], observe_only…
  ignore_after_pattern string (default BeginTearingDown) — Substring marking the teardown boundary; post-marker entries split into active-runtime (before, ok-bearing) + teardown buckets. Default "Be…
  teardown_allowed bool (default true) — If true (default), must_absent hits in the teardown bucket NEVER affect ok (e.g. RecastNavMesh teardown warnings). Set false to also fail o…
  probe_scripts array — Delayed in-session probes: [{at_seconds:number, python?:string, console?:[string]}]. Each fires ONCE against the LIVE PIE world from the fr…
  stages object — Staged startup hooks fired at lifecycle moments: {pre_pie:{python?,console?:[...]} (runs synchronously BEFORE PIE start, against the editor…
  on_compile_errors string (default refuse) — Policy when loaded Blueprints have unresolved compile errors: "refuse" (default, safe) returns an error + the offending {name,path} list an…
  actor_setup array — Declarative spawn/apply/move block executed ONCE against the live PIE world on the first ready tick (after BeginPlay). [{class:"/Game/.../B…
  csv_profile bool (default false) — If true, start the engine CSV profiler on session start (first post-BeginPlay tick) and stop it on completion, bracketing the capture to EX…
  trace_channels array — Channel names (e.g. ["cpu","frame","gpu"]) for an Unreal Insights trace started on session start and stopped on completion, bracketing the …

## editor.run_python — Execute a Python command, statement, or file via IPythonScriptPlugin::ExecPythonCommandEx. Returns success, stdout/stderr captured by Python, and (for evaluate_statement mode) the evaluated result.
  command* string — Python source. May be inline code, a single statement, or a file path with optional space-separated args (when mode=execute_file).
  mode string (default execute_file) — Execution mode: execute_file (default — multi-statement script or file with args), execute_statement (single stmt, prints result), evaluate…
  unattended bool (default false) — Set GIsRunningUnattendedScript=true to suppress UI dialogs.
  file_scope string (default private) — Scope for execute_file: private (isolated locals/globals — default), public (shared with REPL console).

## editor.search_logs — Search log entries by category, verbosity, and text pattern
  pattern string — Text pattern to search for
  category string — Log category filter
  verbosity string — Max verbosity level (error, warning, log, verbose)
  limit integer (default 100) — Max results to return

## editor.start_pie — Start a Play-In-Editor session (equivalent to pressing Cmd+P in the editor).

## gas.add_ability_task_node — Place a UK2Node_LatentAbilityCall in an ability Blueprint graph
  asset_path* string — GameplayAbility Blueprint asset path
  task_class* string — UAbilityTask subclass name (e.g. UAbilityTask_WaitGameplayEvent)
  factory_function string — Static factory function name (auto-detected if omitted)
  position object — { x, y } node position

## gas.add_execution — Add a UGameplayEffectExecutionCalculation to a GameplayEffect with optional scoped modifiers.
  asset_path* string — GameplayEffect Blueprint asset path
  calculation_class* string — Execution calculation class name or path
  scoped_modifiers array — Array of {attribute, operation, magnitude} captured for the execution calc

## gas.add_gameplay_tags — Batch-add gameplay tags. Adds to DefaultGameplayTags.ini by default, or to a DataTable if table_path is provided. Auto-creates parent hierarchy.
  tags* array — Array of tag strings (e.g. ["Ability.Combat.Melee", "State.Dead"])
  table_path string — Path to a GameplayTagTableRow DataTable. If omitted, tags go to DefaultGameplayTags.ini

## gas.add_ge_component — Add a GE component (asset_tags, target_tags, block_abilities, etc.) to a GameplayEffect
  asset_path* string — GameplayEffect Blueprint asset path
  component_type* string — Component type: asset_tags, target_tags, block_abilities, cancel_abilities, target_tag_requirements, additional_effects, immunity, remove_o…
  config* object — Type-specific configuration (e.g. {tags: [...]} for tag components)

## gas.add_modifier — Add an attribute modifier to a GameplayEffect
  asset_path* string — GameplayEffect Blueprint asset path
  attribute* string — Attribute as ClassName.PropertyName
  operation* string — Modifier op: Add, Multiply, MultiplyCompound, Divide, Override, AddFinal
  magnitude* object — Magnitude config: {type, value?, tag?, source_attribute?, calculation_class?}

## gas.create_gameplay_effect — Create a new GameplayEffect Blueprint asset with the specified duration policy
  save_path* string — Asset path, e.g. /Game/GAS/Effects/GE_Damage
  duration_policy* string — Duration type: instant, has_duration, infinite
  parent_class string — Parent class (default: GameplayEffect)

## gas.set_duration — Set the duration policy and optional duration magnitude of a GameplayEffect
  asset_path* string — GameplayEffect Blueprint asset path
  duration_policy* string — instant, has_duration, infinite
  duration_magnitude number — Duration in seconds (for has_duration)

## gas.set_effect_stacking — Configure stacking behavior for a GameplayEffect
  asset_path* string — GameplayEffect Blueprint asset path
  stacking_type* string — none, aggregate_by_source, aggregate_by_target
  stack_limit integer — Maximum stack count (0 or -1 for unlimited)
  stack_duration_refresh_policy string — RefreshOnSuccessfulApplication or NeverRefresh
  stack_period_reset_policy string — ResetOnSuccessfulApplication or NeverReset
  stack_expiration_policy string — ClearEntireStack, RemoveSingleStackAndRefreshDuration, RefreshDuration

## gas.wire_ability_task_delegate — Connect a task delegate output pin to a target exec pin
  asset_path* string — GameplayAbility Blueprint asset path
  node_id* string — Task node ID (from add_ability_task_node response)
  delegate_name* string — Delegate output pin name (e.g. OnCompleted, OnCancelled)
  target_node_id* string — Target node ID to wire the delegate exec to
  target_pin string (default execute) — Target exec input pin name (default: execute)

## material.build_material_graph — Build entire material graph from JSON spec in a single undo transaction
  asset_path* string — Material asset path
  graph_spec* object — JSON specification of the material graph
  clear_existing bool (default true) — Clear existing expressions before building (default: true)

## material.create_custom_hlsl_node — Create a Custom HLSL expression node with inputs, outputs, and code
  asset_path* string — Material asset path
  code* string — HLSL code for the custom node
  description string — Node description
  output_type string — Output type (float, float2, float3, float4)
  pos_x integer — Node X position in graph
  pos_y integer — Node Y position in graph
  inputs array — Array of input pin definitions
  additional_outputs array — Array of additional output pin definitions

## material.get_expression_pin_info — Get input and output pin info for a material expression class (without needing a material asset)
  class_name* string — Expression class name (e.g. MaterialExpressionMultiply or Multiply)

## mesh.spawn_actor — Spawn an actor in the editor world. Path starting with '/' spawns StaticMeshActor with that mesh; otherwise spawns by class name.
  class_or_mesh* string — Asset path for mesh (starts with '/') or class name
  location* array — World location [x, y, z]
  rotation array (default [0,0,0]) — Rotation [pitch, yaw, roll]
  scale array (default [1,1,1]) — Scale [x, y, z]
  name string — Optional label for the spawned actor
  folder string — Actor folder path in the outliner

## project.export_asset_text — Universal escape hatch: export an asset to its native T3D text dump (or grepped excerpts) and return it directly. PREFER the typed read actions first -- get_node_details for Blueprint/AnimGraph nodes, inspect_chooser fo…
  asset_path* string — Package path of the asset to export (e.g. /Game/Path/MyAsset)
  object_filter string — Optional name/class substring (case-insensitive) scoping the export to a single matching sub-object instead of the whole asset
  grep_pattern string — Optional case-insensitive substring; returns only matching lines plus a few lines of surrounding context
  max_bytes number — Optional byte budget for the returned text (default 262144). Hard error if the payload exceeds it -- narrow with grep_pattern/object_filter…

## project.find_by_type — Find all assets of a given type (e.g. Blueprint, Material, StaticMesh)
  asset_type* string — Asset class name (e.g. Blueprint, Material, StaticMesh, Texture2D)
  module string — Filter by plugin/module name (e.g. ExampleInventory)
  limit integer (default 100) — Maximum results
  offset integer (default 0) — Pagination offset

## project.get_asset_details — Get deep details for a specific asset -- nodes, variables, parameters, dependencies
  asset_path* string — Package path of the asset (e.g. /Game/Characters/BP_Hero)

## project.search — Full-text search across indexed project assets (name, class, description, path, module) and graph nodes (name, class, type)
  query* string — FTS5 search query (supports AND, OR, NOT, quoted phrases, prefix*, NEAR(a b, N)); max 4096 characters
  limit integer (default 50) — Maximum results to return (clamped to 1-1000)

## ui.add_custom_widget — Add an instance of a project-authored custom UserWidget Blueprint (e.g. WB_EquipSlot) as a child in a Widget Blueprint's tree. Same parent/slot/positioning surface as add_widget, but resolves widget_blueprint_path via L…
  asset_path* string — Widget Blueprint asset path to add the child into
  widget_blueprint_path* string — Asset path of the custom WidgetBlueprint to instantiate, e.g. /Game/INVENTORY/UI/Widgets/InventoryScreen/WB_EquipSlot. A trailing '.WB_Equi…
  widget_name string — Name for the new widget instance (auto-generated if omitted)
  parent_name string — Parent widget name (default: root widget). Alias: parent
  anchor_preset string — Anchor preset: center, top_left, stretch_fill, etc.
  position object — Canvas position: {"x": 0, "y": 0}
  size object — Canvas size: {"x": 200, "y": 50}
  padding object — Slot padding: {"left":0,"top":0,"right":0,"bottom":0}
  h_align string — Horizontal alignment: Left, Center, Right, Fill
  v_align string — Vertical alignment: Top, Center, Bottom, Fill
  auto_size boolean (default false) — Auto-size in canvas slot
  compile boolean (default true) — Compile after adding

## ui.add_widget — Add a widget to a parent panel in a Widget Blueprint
  asset_path* string — Widget Blueprint asset path
  widget_class* string — Widget class: TextBlock, Image, Button, VerticalBox, etc.
  widget_name string — Name for the new widget (auto-generated if omitted)
  parent_name string — Parent widget name (default: root widget). Alias: parent
  anchor_preset string — Anchor preset: center, top_left, stretch_fill, etc.
  position object — Canvas position: {"x": 0, "y": 0}
  size object — Canvas size: {"x": 200, "y": 50}
  padding object — Slot padding: {"left":0,"top":0,"right":0,"bottom":0}
  h_align string — Horizontal alignment: Left, Center, Right, Fill
  v_align string — Vertical alignment: Top, Center, Bottom, Fill
  auto_size boolean (default false) — Auto-size in canvas slot
  compile boolean (default true) — Compile after adding

## ui.add_widget_variable — Add a member variable to a Widget Blueprint via FBlueprintEditorUtils::AddMemberVariable. var_type accepts MCP-token grammar: bool|int|int64|float|double|string|name|text|byte|object:Class|class:Class|struct:Name|enum:N…
  wbp_path* string — Widget Blueprint path (alias: asset_path)
  var_name* string — New variable FName (uniqueness enforced by AddMemberVariable)
  var_type* string — Type token. See action description for grammar.
  default_value string — Default value as UE text format (engine ImportText grammar)
  var_category string — Details-panel grouping label

## ui.create_hud_element — Create a pre-built HUD element widget hierarchy (crosshair, health bar, ammo counter, etc.)
  asset_path* string — Widget Blueprint asset path to modify
  element_type* string — Element type: crosshair, health_bar, ammo_counter, stamina_bar, interaction_prompt, damage_indicator, compass, subtitles, flashlight_battery
  widget_name_prefix string — Prefix for generated widget names (default: element type)
  compile boolean (default true) — Compile after creating

## ui.create_widget_blueprint — Create a UWidgetBlueprint at save_path. parent_class accepts /Script/Module.Class form OR short name ('TokenforgeActivatableWidget', 'CommonActivatableWidget', 'UserWidget') — short name resolves via UClass::FindClassBy…
  save_path* string — Asset path, e.g. /Game/UI/WBP_MyWidget
  parent_class string (default UserWidget) — Parent class name (default: UserWidget)
  root_widget string (default CanvasPanel) — Root widget type (default: CanvasPanel)
  skip_save boolean (default false) — Skip saving to disk

## ui.get_widget_tree — Get the full widget hierarchy of a Widget Blueprint as JSON
  asset_path* string — Widget Blueprint asset path

## ui.move_widget — Move a widget to a different parent panel
  asset_path* string — Widget Blueprint asset path
  widget_name* string — Widget to move
  new_parent_name* string — New parent panel name
  compile boolean (default true) — Compile after moving

## ui.reparent_widget_root — Replace a WBP's root widget with a new UPanelWidget-derived class (resolved by string: /Script/Module.ClassName, a /Game/... _C path, or a loaded class name), migrating the old root's children onto the new root. new_cla…
  wbp_path* string — Widget Blueprint path (alias: asset_path)
  new_class* string — New root class (UPanelWidget subclass) resolved by string

## ui.set_anchor_preset — Set anchor to a named preset (center, top_left, stretch_fill, etc.)
  asset_path* string — Widget Blueprint asset path
  widget_name* string — Target widget name
  preset* string — Preset name: top_left, top_center, top_right, center_left, center, center_right, bottom_left, bottom_center, bottom_right, stretch_horizont…
  compile boolean (default false) — Compile after setting

## ui.set_font — Set font properties on a text widget (TextBlock, RichTextBlock, EditableText, etc.)
  asset_path* string — Widget Blueprint asset path
  widget_name* string — Target widget name (must be a text widget)
  font_size integer — Font size in points
  font_family string — Font asset path
  typeface string (default Regular) — Typeface: Regular, Bold, Italic, Light
  letter_spacing integer — Letter spacing in design units
  outline_size integer — Font outline size
  outline_color string — Font outline color as hex or r,g,b,a
  compile boolean (default false) — Compile after setting

## ui.set_slot_property — Set a slot property on a widget (anchors, offsets, padding, alignment, z-order)
  asset_path* string — Widget Blueprint asset path
  widget_name* string — Target widget name
  anchors object — Canvas anchors: {"min_x":0, "min_y":0, "max_x":1, "max_y":1}
  offsets object — Canvas offsets: {"left":0, "top":0, "right":0, "bottom":0}
  position object — Canvas position: {"x":0, "y":0}
  size object — Canvas size: {"x":200, "y":50}
  alignment object — Canvas alignment: {"x":0.5, "y":0.5}
  z_order integer — Canvas z-order
  auto_size boolean — Canvas auto-size
  h_align string — Horizontal alignment: Left, Center, Right, Fill
  v_align string — Vertical alignment: Top, Center, Bottom, Fill
  padding object — Slot padding: {"left":0, "top":0, "right":0, "bottom":0}
  row integer — Grid slot row index (UniformGrid/Grid slots)
  column integer — Grid slot column index (UniformGrid/Grid slots)
  row_span integer — Grid slot row span (Grid slots only)
  column_span integer — Grid slot column span (Grid slots only)
  compile boolean (default false) — Compile after setting

## ui.set_text — Convenience: set text, color, size, justification on a TextBlock or RichTextBlock
  asset_path* string — Widget Blueprint asset path
  widget_name* string — Target TextBlock or RichTextBlock name
  text string — Text content to set
  text_color string — Text color as hex (#RRGGBB) or r,g,b,a
  font_size integer — Font size in points
  justification string — Text justification: Left, Center, Right
  compile boolean (default false) — Compile after setting

## ui.set_widget_is_variable — Set a UWidget's bIsVariable flag. When true the widget is exposed as a named variable on the WBP's generated class (visible to get_variables, accessible from the graph); when false it becomes an anonymous tree-only widg…
  wbp_path* string — Widget Blueprint path
  widget_name* string — Name of the widget in the WBP's WidgetTree
  is_variable* bool — New bIsVariable value (true = expose as named variable)

## ui.set_widget_property — Set a property on a widget (text, color, opacity, visibility, etc.). Default mode gates writes through the per-type curated allowlist; pass raw_mode=true to bypass the gate (legacy compat). The new value can be supplied…
  asset_path* string — Widget Blueprint asset path
  widget_name* string — Target widget name
  property_name* string — Property path. Dotted segments allowed (e.g. 'Padding.Left'). Allowlist-gated unless raw_mode=true.
  value* any — Property value (alias: 'property_value'). Strings, numbers, booleans, JSON arrays/objects all accepted; struct types (Vector2D/LinearColor/…
  compile boolean (default false) — Compile after setting
  raw_mode boolean (default false) — Bypass the allowlist gate (legacy unconditional ImportText_Direct path). Default false.
