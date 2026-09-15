#!/usr/bin/env python3
"""Query the Copilot Resource Registry (YAML)."""
import argparse, os, sys, re

REGISTRY = os.path.join(os.path.dirname(__file__), "..", "copilot-registry.yml")

def parse_registry():
    with open(REGISTRY, "r", encoding="utf-8") as f:
        content = f.read()
    sections = {}
    current_section = None
    current_item = None
    for line in content.splitlines():
        line = line.rstrip('\r')
        sec_match = re.match(r'^(agents|skills|tools|plugins|models):\s*$', line)
        sec_match = re.match(r"^(agents|skills|tools|plugins|models):\s*$", line)
        if sec_match:
            current_section = sec_match.group(1)
            sections[current_section] = []
            continue
        if current_section is None:
            continue
        name_match = re.match(r"^  - name:\s*(.+)$", line)
        if name_match:
            current_item = {"name": name_match.group(1).strip(), "type": current_section}
            sections[current_section].append(current_item)
            continue
        if current_item is not None:
            kv = re.match(r"^\s+(\w+):\s*(.+)$", line)
            if kv:
                k, v = kv.group(1).strip(), kv.group(2).strip()
                if k == "tags":
                    v = [t.strip() for t in v.strip("[]").split(",") if t.strip()]
                current_item[k] = v
    items = []
    for sec, objs in sections.items():
        items.extend(objs)
    return items

def main():
    parser = argparse.ArgumentParser(description="Query Copilot Registry")
    parser.add_argument("--type", choices=["agent","skill","tool","plugin","model"])
    parser.add_argument("--tag")
    parser.add_argument("--keyword")
    parser.add_argument("--list-tags", action="store_true")
    args = parser.parse_args()

    items = parse_registry()

    if args.list_tags:
        tags = sorted({t for it in items for t in it.get("tags", [])})
        for t in tags:
            print(t)
        return

    filtered = items
    if args.type:
        type_map = {"agent": "agents", "skill": "skills", "tool": "tools", "plugin": "plugins", "model": "models"}
        t = type_map.get(args.type, args.type)
        filtered = [it for it in filtered if it.get("type") == t]
    if args.tag:
        filtered = [it for it in filtered if args.tag in it.get("tags", [])]
    if args.keyword:
        kw = args.keyword.lower()
        filtered = [it for it in filtered if (
            kw in it.get("name","").lower() or
            kw in it.get("description","").lower() or
            any(kw in t.lower() for t in it.get("tags",[]))
        )]

    print(f"{'Name':<40} {'Type':<10} {'Source':<18} {'Tags'}")
    print("-" * 100)
    for it in filtered:
        tags = ", ".join(it.get("tags", []))[:40]
        print(f"{it.get('name','')[:38]:<40} {it.get('type',''):<10} {it.get('source',''):<18} {tags}")
    print(f"\nTotal: {len(filtered)} of {len(items)} resources")

if __name__ == "__main__":
    main()
