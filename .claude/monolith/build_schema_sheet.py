"""Render .claude/monolith/schemas_raw.json (Monolith action_schema responses keyed "ns.action")
into SCHEMAS.md: one grep-able block per action. Regenerate after a Monolith update.
Usage: python .claude/monolith/build_schema_sheet.py"""
import json, os
here = os.path.dirname(os.path.abspath(__file__))
raw = json.load(open(os.path.join(here, "schemas_raw.json"), encoding="utf-8"))

def short(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"

out = ["# Monolith action schemas (verified, cached)",
       "",
       "Grep this file instead of calling describe_query/monolith_discover:",
       "`Grep pattern=\"^## blueprint.add_node\" path=.claude/monolith/SCHEMAS.md -A 12`",
       "`*` = required. If an action is missing here, fall back to describe_query action_schema",
       "with params {target_namespace, target_action}.", ""]
for key in sorted(raw):
    try:
        s = json.loads(raw[key])
    except Exception:
        continue
    out.append(f"## {key} — {short(s.get('description'), 220)}")
    for name, p in (s.get("params") or {}).items():
        star = "*" if p.get("required") else ""
        extra = ""
        if p.get("enum"):
            extra = " [" + "|".join(map(str, p["enum"]))[:120] + "]"
        if "default" in p:
            extra += f" (default {p['default']})"
        out.append(f"  {name}{star} {p.get('type','?')}{extra} — {short(p.get('description'), 140)}")
    out.append("")
open(os.path.join(here, "SCHEMAS.md"), "w", encoding="utf-8").write("\n".join(out))
print(f"{len(raw)} actions -> SCHEMAS.md")
