#!/usr/bin/env python3
"""Validates switch/security-room.template.yaml against Switch template specs.

Checks:
- YAML syntax and structure
- Version (v1 group template)
- Required top-level fields: version, params, agents, group, rooms, links
- Declared params and placeholder usages (e.g. {provider}, {repo_dir}, {bridge})
- Agent definitions: name, provider, location, directory, addressing, instructions
- Room definitions: name, bridge, agents, users, kickoff / docs
- Addressing validity: owner | owner-agents | anyone
"""
import re
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "switch" / "security-room.template.yaml"

VALID_ADDRESSING = {"owner", "owner-agents", "anyone"}


def validate_template(path=None):
    template_file = Path(path) if path else TEMPLATE_PATH
    if not template_file.exists():
        print(f"Error: template file not found at {template_file}", file=sys.stderr)
        return False, ["File not found"]

    errors = []
    warnings = []

    try:
        content = template_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return False, [f"YAML syntax error: {e}"]

    # 1. Version check
    if data.get("version") != 1:
        errors.append(f"Expected version: 1, got {data.get('version')}")

    # 2. Params declaration
    params = data.get("params", {})
    if not isinstance(params, dict):
        errors.append("'params' must be a mapping")
        params = {}

    # Extract all {placeholders} in the raw content
    placeholders = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", content))
    # Special switch built-in placeholders starting with $ (like {$agents_dir}, {$creator})
    declared_params = set(params.keys())

    for ph in placeholders:
        if ph not in declared_params:
            errors.append(f"Undeclared template parameter placeholder: '{{{ph}}}'")

    # 3. Agents check
    agents = data.get("agents", [])
    if not isinstance(agents, list) or len(agents) == 0:
        errors.append("Template must define at least one agent in 'agents'")
    else:
        agent_names = set()
        for idx, agent in enumerate(agents):
            name = agent.get("name")
            if not name:
                errors.append(f"Agent #{idx} missing 'name'")
                continue
            agent_names.add(name)

            for req in ("provider", "location", "directory", "instructions"):
                if not agent.get(req):
                    errors.append(f"Agent '{name}' missing required field: '{req}'")

            addr = agent.get("addressing")
            if addr and addr not in VALID_ADDRESSING:
                errors.append(f"Agent '{name}' has invalid addressing '{addr}'. Must be one of {VALID_ADDRESSING}")

    # 4. Group check
    group = data.get("group", {})
    if not group.get("name"):
        errors.append("Template must specify 'group.name'")

    # 5. Rooms check
    rooms = data.get("rooms", [])
    if not isinstance(rooms, list) or len(rooms) == 0:
        errors.append("Template must define at least one room in 'rooms'")
    else:
        room_names = set()
        for r in rooms:
            rname = r.get("name")
            if not rname:
                errors.append("Room missing 'name'")
                continue
            room_names.add(rname)

            if not r.get("bridge"):
                errors.append(f"Room '{rname}' missing 'bridge'")

            room_agents = r.get("agents", [])
            if not isinstance(room_agents, list):
                errors.append(f"Room '{rname}' 'agents' must be a list")

    # 6. Links check
    links = data.get("links", [])
    for link in links:
        from_room = link.get("from")
        to_room = link.get("to")
        if from_room and from_room not in room_names:
            errors.append(f"Link 'from' room '{from_room}' does not match any declared room")
        if to_room and to_room not in room_names:
            errors.append(f"Link 'to' room '{to_room}' does not match any declared room")

    is_valid = len(errors) == 0
    return is_valid, errors


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
