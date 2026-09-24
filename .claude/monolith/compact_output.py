"""PostToolUse hook for mcp__monolith__blueprint_query — rewrites bulky graph dumps
(get_graph_data, get_node_details, export_graph-style node lists) into a compact form
that keeps everything needed to reason about and edit the graph:

  node ids, class, title, function/macro/variable refs, every pin name + type,
  pin defaults, and connections (as "NodeId.PinName").

Dropped: pin GUIDs (edits address pins by name), empty
connected_to arrays, and "direction" (encoded as in/out groups). Set
MONOLITH_RAW=1 in the environment to disable.
"""
import json, os, sys

TARGET_ACTIONS = {"get_graph_data", "get_node_details"}


def compact_pin(p):
    s = f"{p.get('name')}:{p.get('type', '?')}"
    if p.get("default_value") not in (None, "", "None"):
        s += f"={p['default_value']}"
    if p.get("orphaned"):
        s += " (ORPHANED)"
    conns = p.get("connected_to") or []
    if conns:
        s += " -> " + ", ".join(conns)
    return s


def compact_node(n):
    out = {k: v for k, v in n.items() if k not in ("pins", "guid", "node_guid")}
    ins, outs = [], []
    for p in n.get("pins") or []:
        (ins if p.get("direction") == "input" else outs).append(compact_pin(p))
    if ins:
        out["in"] = ins
    if outs:
        out["out"] = outs
    return out


def compact(obj):
    if isinstance(obj, dict):
        if "pins" in obj and ("class" in obj or "id" in obj):
            return compact_node(obj)
        return {k: compact(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [compact(v) for v in obj]
    return obj


def transform_text(text):
    data = json.loads(text)
    return json.dumps(compact(data), separators=(",", ":"), ensure_ascii=False)


def main():
    if os.environ.get("MONOLITH_RAW") == "1":
        return
    data = json.load(sys.stdin)
    if (data.get("tool_input") or {}).get("action") not in TARGET_ACTIONS:
        return
    resp = data.get("tool_response")
    # MCP responses arrive either as a content array or a bare string.
    if isinstance(resp, list):
        new, changed = [], False
        for block in resp:
            if isinstance(block, dict) and block.get("type") == "text":
                try:
                    block = dict(block, text=transform_text(block["text"]))
                    changed = True
                except Exception:
                    pass
            new.append(block)
        if not changed:
            return
        text_out = "\n".join(b.get("text", "") for b in new if isinstance(b, dict))
    elif isinstance(resp, str):
        try:
            text_out = transform_text(resp)
        except Exception:
            return
    else:
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "updatedToolOutput": text_out,
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
