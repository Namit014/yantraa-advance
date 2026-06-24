"""
Real SKiDL ERC adapter. Builds per-part typed Parts from parts-db pin definitions.
No more generic 1-pin Connector sockets.
"""
from skidl import Part, Net, Pin, ERC, SKIDL, TEMPLATE, reset
import io
import contextlib

PIN_TYPE_MAP = {
    "PWRIN":     Pin.types.PWRIN,
    "PWROUT":    Pin.types.PWROUT,
    "INPUT":     Pin.types.INPUT,
    "OUTPUT":    Pin.types.OUTPUT,
    "BIDIR":     Pin.types.BIDIR,
    "TRISTATE":  Pin.types.TRISTATE,
    "PASSIVE":   Pin.types.PASSIVE,
    "NOCONNECT": Pin.types.NOCONNECT,
}

def _build_part_template(part_id: str, pdb_entry: dict | None) -> tuple:
    """Returns (Part template, fallback_warnings[])."""
    if pdb_entry is None:
        p = Part(tool=SKIDL, name=part_id, footprint="", dest=TEMPLATE)
        p += Pin(num=1, name="P1", func=Pin.types.PASSIVE)
        return p, [{"severity": "warning",
                    "message": f"Part '{part_id}' has no electrical pin model — ERC skipped",
                    "component_id": None}]
    p = Part(tool=SKIDL, name=pdb_entry["id"], footprint="", dest=TEMPLATE)
    for i, pin_def in enumerate(pdb_entry.get("pins", []), start=1):
        raw = pin_def.get("skidl_type", "PASSIVE")
        func = PIN_TYPE_MAP.get(raw, Pin.types.PASSIVE)
        if raw not in PIN_TYPE_MAP:
            print(f"[YANTRAA WARNING] Unknown skidl_type '{raw}' on {pdb_entry['id']}.{pin_def['name']} — PASSIVE")
        p += Pin(num=i, name=pin_def["name"], func=func)
    return p, []

def run_erc_on_netlist(logical_netlist: dict, parts_db: list = None) -> list:
    reset()
    pdb_index = {p["id"]: p for p in (parts_db or [])}
    components = logical_netlist.get("components", [])
    nets_data   = logical_netlist.get("nets", [])
    issues = []

    # 1. Build part templates
    templates = {}
    skidl_instances = {}
    for comp in components:
        if comp.get("is_support"): continue
        comp_id  = comp["id"]
        part_id  = comp.get("partId", "")
        pdb_entry = pdb_index.get(part_id)
        tmpl, warns = _build_part_template(part_id, pdb_entry)
        for w in warns:
            w["component_id"] = comp_id
            issues.append(w)
        templates[comp_id] = tmpl
        inst = tmpl()
        inst.ref = comp.get("designator", comp_id).replace(" ", "_")
        skidl_instances[comp_id] = inst

    # 2. Wire nets — by named pin, not pin[1]
    for net_def in nets_data:
        net_name = net_def.get("name", "UnnamedNet")
        n = Net(net_name)
        for member in net_def.get("members", []):
            cid = member.get("componentId")
            pname = member.get("pinName")
            inst = skidl_instances.get(cid)
            if inst is None: continue
            try:
                n += inst[pname]
            except Exception as e:
                issues.append({"severity": "warning",
                               "message": f"Could not wire {cid}.{pname} to net {net_name}: {e}",
                               "component_id": cid, "net_name": net_name})

    # 3. Run SKiDL ERC and capture output
    buf = io.StringIO()
    import logging
    from skidl import erc_logger
    handler = logging.StreamHandler(buf)
    erc_logger.addHandler(handler)
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            ERC()
    except Exception as e:
        issues.append({"severity": "error", "message": f"ERC execution error: {e}"})
    finally:
        erc_logger.removeHandler(handler)
    
    # 4. Parse ERC output with known SKiDL patterns (not blind substring)
    ERC_PATTERNS = [
        ("No drives",             "error"),
        ("Multiple drivers",      "error"),
        ("Unconnected pin",       "warning"),
        ("No load",               "warning"),
        ("Net is not driven",     "error"),
        ("Pin is not connected",  "warning"),
        ("Pin conflict",          "error"),
        ("Insufficient drive",    "warning")
    ]
    for line in buf.getvalue().splitlines():
        line = line.strip()
        if not line: continue
        matched = False
        for pattern, severity in ERC_PATTERNS:
            if pattern.lower() in line.lower():
                issues.append({"severity": severity, "message": line})
                matched = True
                break
        if not matched and line and not line.startswith("ERC INFO:"):
            issues.append({"severity": "info", "message": line})

    return issues
