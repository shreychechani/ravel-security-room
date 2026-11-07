#!/usr/bin/env python3
"""Validates switch/security-room.template.yaml against the Switch template format (version 2).

Spec: https://github.com/sandbox-quantum/switch/blob/main/docs/TEMPLATES.md
This is a quick offline check; the real check is the Switch server's own validation.

Checks:
- YAML syntax, version 2, a `params` mapping and a `resources` mapping
- Every {placeholder} is a declared param ({$...} are Switch built-ins)
- Every resource has a known type: agent, group or room
- Agents: name, provider, directory, instructions; addressing is valid
- Rooms: name, bridge; `group` names a group resource
- Group links name room resources
- Resource keys never appear in text fields (Console replaces a key word everywhere)
"""
import re
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "switch" / "security-room.template.yaml"

VALID_ADDRESSING = {"owner", "owner-agents", "anyone"}
RESOURCE_TYPES = {"agent", "group", "room"}
TEXT_FIELDS = ("instructions", "kickoff", "description", "display_name")


def validate_template(path=None):
    template_file = Path(path) if path else TEMPLATE_PATH
    if not template_file.exists():
        print(f"Error: template file not found at {template_file}", file=sys.stderr)
        return False, ["File not found"]

    try:
        content = template_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return False, [f"YAML syntax error: {e}"]
    if not isinstance(data, dict):
        return False, ["Template must be a YAML mapping"]

    errors = []

    # 1. Version
    if data.get("version") != 2:
        errors.append(f"Expected version: 2, got {data.get('version')}")

    # 2. Params and placeholders
    params = data.get("params") or {}
    if not isinstance(params, dict):
        errors.append("'params' must be a mapping")
        params = {}
    for name, spec in params.items():
        if not isinstance(spec, dict) or not spec.get("type"):
            errors.append(f"Param '{name}' needs a 'type'")

    for ph in sorted(set(re.findall(r"\{([a-zA-Z0-9_]+)\}", content))):
        if ph not in params:
            errors.append(f"Undeclared template parameter placeholder: '{{{ph}}}'")

    # 3. Resources
    resources = data.get("resources") or {}
    if not isinstance(resources, dict) or not resources:
        return False, errors + ["Template must define 'resources'"]

    by_type = {t: {} for t in RESOURCE_TYPES}
    for key, res in resources.items():
        rtype = res.get("type") if isinstance(res, dict) else None
        if rtype not in RESOURCE_TYPES:
            errors.append(f"Resource '{key}' has unknown type '{rtype}'. Must be one of {sorted(RESOURCE_TYPES)}")
            continue
        by_type[rtype][key] = res

    if not by_type["agent"]:
        errors.append("Template must define at least one agent resource")
    if not by_type["room"]:
        errors.append("Template must define at least one room resource")

    for key, agent in by_type["agent"].items():
        for req in ("name", "provider", "directory", "instructions"):
            if not agent.get(req):
                errors.append(f"Agent '{key}' missing required field: '{req}'")
        addr = agent.get("addressing")
        if addr and addr not in VALID_ADDRESSING:
            errors.append(f"Agent '{key}' has invalid addressing '{addr}'. Must be one of {sorted(VALID_ADDRESSING)}")

    for key, room in by_type["room"].items():
        for req in ("name", "bridge"):
            if not room.get(req):
                errors.append(f"Room '{key}' missing required field: '{req}'")
        if room.get("group") and room["group"] not in by_type["group"]:
            errors.append(f"Room '{key}' names group '{room['group']}', which is not a group resource")
        if not isinstance(room.get("agents", []), list):
            errors.append(f"Room '{key}' 'agents' must be a list")

    for key, group in by_type["group"].items():
        for link in group.get("links") or []:
            for end in ("from", "to"):
                if link.get(end) not in by_type["room"]:
                    errors.append(f"Group '{key}' link '{end}' room '{link.get(end)}' is not a room resource")

    # 4. Resource keys must not appear in text: Console would replace them there too
    for key, res in resources.items():
        if not isinstance(res, dict):
            continue
        for field in TEXT_FIELDS:
            text = res.get(field)
            if not isinstance(text, str):
                continue
            for other in resources:
                if re.search(rf"\b{re.escape(other)}\b", text):
                    errors.append(f"Resource key '{other}' appears in {key}.{field}; rename the key so it never appears in text")

    return len(errors) == 0, errors


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"Validating Switch template: {path or TEMPLATE_PATH}...")
    ok, errors = validate_template(path)
    if ok:
        print("✅ Template validation passed successfully!")
        sys.exit(0)
    else:
        print(f"❌ Template validation failed with {len(errors)} error(s):")
        for err in errors:
            print(f"  • {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
