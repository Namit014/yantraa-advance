import json
import re

# Simulate "Before" logic
def generate_connections_before(nodes, raw):
    connections = []
    seen = set()
    
    def addConn(fromId, toId, label):
        if not fromId or not toId or fromId == toId: return
        key1 = f"{fromId}→{toId}"
        key2 = f"{toId}→{fromId}"
        if key1 in seen or key2 in seen: return
        seen.add(key1)
        connections.append({
            "id": f"conn-{len(connections)}-time",
            "fromId": fromId,
            "toId": toId,
            "label": label
        })

    # RAG connects_to
    for rc in raw:
        fromNode = next((n for n in nodes if n['label'] == rc['name']), None)
        if not fromNode: continue
        for targetName in rc['connects_to']:
            toNode = next((n for n in nodes if n['label'] == targetName), None)
            if not toNode: continue
            
            srcId = fromNode['id']
            dstId = toNode['id']
            
            # Direction overrides in old code? None existed for power, only actuator-controller
            if fromNode['category'] == 'actuator' and toNode['category'] == 'controller':
                srcId = toNode['id']
                dstId = fromNode['id']
                
            srcNode = next(n for n in nodes if n['id'] == srcId)
            dstNode = next(n for n in nodes if n['id'] == dstId)
            pairKey = f"{srcNode['category']}-{dstNode['category']}"
            
            label = "connection"
            if pairKey in ["actuator-controller", "controller-actuator"]: label = "drive"
            elif "sensor" in pairKey and "power" in pairKey: label = "power"
            elif "sensor" in pairKey: label = "data"
            elif "power" in pairKey: label = "power"
            elif "electronic" in pairKey: label = "signal"
            elif "mechanical" in pairKey: label = "linkage"
            
            addConn(srcId, dstId, label)
            
    # Secondary fallback
    connectedIds = set()
    for c in connections:
        connectedIds.add(c['fromId'])
        connectedIds.add(c['toId'])

    byCategory = {}
    for n in nodes:
        byCategory.setdefault(n['category'], []).append(n)
        
    controllers = byCategory.get("controller", [])
    actuators = byCategory.get("actuator", [])
    sensors = byCategory.get("sensor", [])
    mechanical = byCategory.get("mechanical", [])
    power = byCategory.get("power", [])
    electronic = byCategory.get("electronic", [])
    
    for a in actuators:
        if a['id'] not in connectedIds:
            for c in controllers: addConn(a['id'], c['id'], "drive") # OLD WAS THIS
    for s in sensors:
        if s['id'] not in connectedIds:
            for c in controllers: addConn(s['id'], c['id'], "data")
    for m in mechanical:
        if m['id'] not in connectedIds:
            # skipped linkage logic for brevity since irrelevant
            pass
    for p in power:
        if p['id'] not in connectedIds:
            for c in controllers: addConn(p['id'], c['id'], "power")
            for a in actuators: addConn(p['id'], a['id'], "power")
    for c in controllers:
        if c['id'] not in connectedIds:
            for e in electronic: addConn(c['id'], e['id'], "signal")

    return connections

# Simulate "After" logic
def generate_connections_after(nodes, raw):
    connections = []
    seen = set()
    connCounter = 0
    
    def addConn(fromId, toId, label):
        nonlocal connCounter
        if not fromId or not toId or fromId == toId: return
        key1 = f"{fromId}→{toId}→{label}"
        key2 = f"{toId}→{fromId}→{label}"
        if key1 in seen or key2 in seen: return
        seen.add(key1)
        connections.append({
            "id": f"conn-{connCounter}-time",
            "fromId": fromId,
            "toId": toId,
            "label": label
        })
        connCounter += 1

    # RAG connects_to
    for rc in raw:
        fromNode = next((n for n in nodes if n['label'] == rc['name']), None)
        if not fromNode: continue
        for targetName in rc['connects_to']:
            toNode = next((n for n in nodes if n['label'] == targetName), None)
            if not toNode: continue
            
            srcId = fromNode['id']
            dstId = toNode['id']
            
            # NEW: direction overrides for power
            if fromNode['category'] == 'actuator' and toNode['category'] == 'controller':
                srcId = toNode['id']
                dstId = fromNode['id']
            elif toNode['category'] == 'power':
                srcId = toNode['id']
                dstId = fromNode['id']
                
            srcNode = next(n for n in nodes if n['id'] == srcId)
            dstNode = next(n for n in nodes if n['id'] == dstId)
            pairKey = f"{srcNode['category']}-{dstNode['category']}"
            
            label = "connection"
            if pairKey in ["actuator-controller", "controller-actuator"]: label = "drive"
            elif "sensor" in pairKey and "power" in pairKey: label = "power"
            elif "sensor" in pairKey: label = "data"
            elif "power" in pairKey: label = "power"
            elif "electronic" in pairKey: label = "signal"
            elif "mechanical" in pairKey: label = "linkage"
            
            if label == "power":
                addConn(srcId, dstId, "power")
                addConn(srcId, dstId, "ground")
            else:
                addConn(srcId, dstId, label)
            
    # Secondary fallback
    connectedIds = set()
    for c in connections:
        connectedIds.add(c['fromId'])
        connectedIds.add(c['toId'])

    byCategory = {}
    for n in nodes:
        byCategory.setdefault(n['category'], []).append(n)
        
    controllers = byCategory.get("controller", [])
    actuators = byCategory.get("actuator", [])
    sensors = byCategory.get("sensor", [])
    mechanical = byCategory.get("mechanical", [])
    power = byCategory.get("power", [])
    electronic = byCategory.get("electronic", [])
    
    for a in actuators:
        if a['id'] not in connectedIds:
            for c in controllers: addConn(c['id'], a['id'], "drive")
    for s in sensors:
        if s['id'] not in connectedIds:
            for c in controllers: addConn(s['id'], c['id'], "data")
    for p in power:
        if p['id'] not in connectedIds:
            for c in controllers: 
                addConn(p['id'], c['id'], "power")
                addConn(p['id'], c['id'], "ground")
            for a in actuators: 
                addConn(p['id'], a['id'], "power")
                addConn(p['id'], a['id'], "ground")
    for c in controllers:
        if c['id'] not in connectedIds:
            for e in electronic: addConn(c['id'], e['id'], "signal")

    # Post processing: ground wires
    currentConns = list(connections)
    for c in currentConns:
        if c['label'] == 'power':
            hasGround = any(existing['fromId'] == c['fromId'] and existing['toId'] == c['toId'] and existing['label'] == 'ground' for existing in connections)
            if not hasGround:
                addConn(c['fromId'], c['toId'], 'ground')
                
    # Post processing: triple driver
    actIds = [a['id'] for a in actuators]
    for actId in actIds:
        drives = [c for c in connections if c['toId'] == actId and c['label'] == 'drive']
        if len(drives) > 1:
            drivers = []
            for d in drives:
                dr = next((n for n in nodes if n['id'] == d['fromId']), None)
                if dr: drivers.append(dr)
            
            def score(n):
                l = n['label'].lower()
                if "shield" in l or "driver" in l or "hat" in l: return 3
                if "arduino" in l or "raspberry" in l or "mega" in l or "esp" in l: return 2
                return 1
            
            drivers.sort(key=score, reverse=True)
            bestDriver = drivers[0]
            
            for i in range(1, len(drivers)):
                weaker = drivers[i]
                for c in list(connections):
                    if c['fromId'] == weaker['id'] and c['toId'] == actId and c['label'] == 'drive':
                        connections.remove(c)
                
                existing = any((c['fromId'] == weaker['id'] and c['toId'] == bestDriver['id']) or (c['toId'] == weaker['id'] and c['fromId'] == bestDriver['id']) for c in connections)
                if not existing:
                    addConn(weaker['id'], bestDriver['id'], 'signal')
                    
    return connections


# Dummy nodes from SEED_NODES
nodes = [
    {"id": "power-1", "label": "3-Cell LiPo Battery", "category": "power"},
    {"id": "power-2", "label": "Power Supply", "category": "power"},
    {"id": "sensor-1", "label": "IMU Sensor", "category": "sensor"},
    {"id": "sensor-2", "label": "Ultrasonic Range Finder", "category": "sensor"},
    {"id": "sensor-3", "label": "9 DOF IMU", "category": "sensor"},
    {"id": "actuator-1", "label": "Servo Motor A", "category": "actuator"},
    {"id": "actuator-2", "label": "Servo Motor B", "category": "actuator"},
    {"id": "actuator-3", "label": "High-Torque Digital Servo", "category": "actuator"},
    {"id": "controller-1", "label": "Motion Controller", "category": "controller"},
    {"id": "controller-2", "label": "Arduino Mega 2560", "category": "controller"},
    {"id": "controller-3", "label": "Servo Controller Shield", "category": "controller"}
]

# Dummy RAG response that connects sensors to power, and multiple drivers to actuator
raw = [
    {"name": "IMU Sensor", "connects_to": ["3-Cell LiPo Battery", "Arduino Mega 2560"]},
    {"name": "Ultrasonic Range Finder", "connects_to": ["Power Supply", "Arduino Mega 2560"]},
    {"name": "Servo Motor A", "connects_to": []},
    {"name": "Servo Motor B", "connects_to": []},
    {"name": "High-Torque Digital Servo", "connects_to": []},
    {"name": "Motion Controller", "connects_to": ["Servo Motor A", "Servo Motor B", "High-Torque Digital Servo"]},
    {"name": "Arduino Mega 2560", "connects_to": ["Servo Motor A", "Servo Motor B", "High-Torque Digital Servo"]},
    {"name": "Servo Controller Shield", "connects_to": ["Servo Motor A", "Servo Motor B", "High-Torque Digital Servo"]},
]

print("BEFORE:")
b_conns = generate_connections_before(nodes, raw)
for c in b_conns:
    if "sensor" in c['fromId'] and "power" in c['toId'] or "power" in c['fromId'] and "sensor" in c['toId']:
        print(f"  {c['fromId']} -> {c['toId']} ({c['label']})")
print("\nAFTER:")
a_conns = generate_connections_after(nodes, raw)
for c in a_conns:
    if "sensor" in c['fromId'] and "power" in c['toId'] or "power" in c['fromId'] and "sensor" in c['toId']:
        print(f"  {c['fromId']} -> {c['toId']} ({c['label']})")

print("\nACTUATOR DRIVERS BEFORE:")
for c in b_conns:
    if "actuator" in c['toId'] and c['label'] == "drive":
        print(f"  {c['fromId']} -> {c['toId']} ({c['label']})")

print("\nACTUATOR DRIVERS AFTER:")
for c in a_conns:
    if "actuator" in c['toId'] and c['label'] == "drive":
        print(f"  {c['fromId']} -> {c['toId']} ({c['label']})")
    elif c['label'] == "signal" and ("controller" in c['fromId'] and "controller" in c['toId']):
        print(f"  {c['fromId']} -> {c['toId']} (chained {c['label']})")

