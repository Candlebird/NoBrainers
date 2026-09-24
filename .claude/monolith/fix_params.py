"""PreToolUse hook for mcp__monolith__* — silently repairs the parameter-name mistakes that
made ~14% of historical Monolith calls fail (blueprint_path vs asset_path, from_node vs
source_node, search_term vs query, ...).

Schema-driven: a key is only renamed when the action's cached schema (schemas_raw.json)
lists the canonical name, does NOT list the alias, and the canonical name wasn't already
supplied. Unknown actions pass through untouched. Never blocks a call.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

ALIASES = {
    "asset_path": ["blueprint_path", "bp_path", "blueprint", "path", "asset", "widget_path", "blueprint_name"],
    "source_node": ["from_node", "src_node", "source_node_id", "from_node_id"],
    "source_pin": ["from_pin", "src_pin", "source_pin_name", "from_pin_name"],
    "target_node": ["to_node", "dst_node", "target_node_id", "to_node_id"],
    "target_pin": ["to_pin", "dst_pin", "target_pin_name", "to_pin_name"],
    "query": ["search_term", "search", "term", "search_query"],
    "name": ["variable_name", "var_name", "function_name"],
    "save_path": ["asset_path", "path"],
    "interface_class": ["asset_path", "interface", "interface_name"],
    "node_id": ["source_node", "node", "node_name"],
    "pin_name": ["pin_id", "pin", "source_pin"],
    "command": ["code", "script", "python"],
    "defaults": ["pins", "entries", "values"],
    "type": ["variable_type", "var_type", "pin_type"],
    "node_type": ["node_class"],
    "entry_point": ["function_name", "graph_name", "event_name"],
}
PIN_KEYS = ("source_node", "source_pin", "target_node", "target_pin")


def load_schemas():
    try:
        raw = json.load(open(os.path.join(HERE, "schemas_raw.json"), encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for k, v in raw.items():
        try:
            out[k] = set((json.loads(v).get("params") or {}).keys())
        except Exception:
            pass
    return out


def rename(params, allowed, changes, where=""):
    for canon, aliases in ALIASES.items():
        if canon not in allowed or canon in params:
            continue
        for a in aliases:
            if a in params and a not in allowed:
                params[canon] = params.pop(a)
                changes.append(f"{where}{a}->{canon}")
                break


def fix_connection_items(items, changes):
    for i, item in enumerate(items or []):
        if isinstance(item, dict):
            rename(item, set(PIN_KEYS), changes, f"[{i}].")


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    tin = data.get("tool_input") or {}
    ns = tool.replace("mcp__monolith__", "").replace("_query", "")
    action = tin.get("action")
    params = tin.get("params")
    changes = []

    # Params occasionally supplied at the top level instead of under "params".
    stray = {k: v for k, v in tin.items() if k not in ("action", "params")}
    if stray and params is None:
        params = stray
        tin = {"action": action}
        changes.append("top-level->params")

    # Params occasionally arrive as a JSON-encoded string.
    if isinstance(params, str):
        try:
            params = json.loads(params)
            changes.append("params:str->obj")
        except Exception:
            return
    if not isinstance(params, dict) or not action:
        if not changes:
            return
        params = params or {}

    if ns == "describe" and action == "action_schema":
        if "action" in params:  # {namespace, action} is accepted server-side as-is
            params = None
    if params is None:
        pass
    elif ns == "describe" and action == "action_schema":
        t = params.pop("target", None) or params.pop("action_name", None)
        if isinstance(t, str) and "." in t and "target_action" not in params:
            params["target_namespace"], params["target_action"] = t.split(".", 1)
            changes.append("target->ns/action")
        elif t and "target_action" not in params:
            params["target_action"] = t
            changes.append("target->target_action")
        for a in ("namespace", "domain", "tool", "target_domain"):
            if a in params and "target_namespace" not in params:
                params["target_namespace"] = params.pop(a).replace("_query", "")
                changes.append(f"{a}->target_namespace")
        if "target_namespace" not in params and "target_action" in params:
            params["target_namespace"] = "blueprint"  # overwhelmingly the common case
            changes.append("default target_namespace=blueprint")
    else:
        # connect_pins called with a connections list is really connect_pins_bulk.
        if ns == "blueprint" and action == "connect_pins" and isinstance(params.get("connections"), list):
            action = "connect_pins_bulk"
            tin = dict(tin, action=action)
            changes.append("connect_pins->connect_pins_bulk")
        allowed = load_schemas().get(f"{ns}.{action}")
        if allowed:
            rename(params, allowed, changes)
            if "connections" in allowed and isinstance(params.get("connections"), list):
                fix_connection_items(params["connections"], changes)
            # get_node_details takes one node_id; unwrap a single-item node_ids list.
            if "node_id" in allowed and "node_id" not in params and isinstance(params.get("node_ids"), list) \
                    and len(params["node_ids"]) == 1:
                params["node_id"] = params.pop("node_ids")[0]
                changes.append("node_ids[0]->node_id")

    if not changes or params is None:
        return
    new_input = dict(tin, params=params)
    try:
        with open(os.path.join(HERE, "fix_params.log"), "a", encoding="utf-8") as f:
            f.write(f"{ns}.{action}: {', '.join(changes)}\n")
    except Exception:
        pass
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "updatedInput": new_input,
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never break a tool call because of this hook
