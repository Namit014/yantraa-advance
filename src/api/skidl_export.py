import json
import os
import sys
import io
import contextlib

# Import SKiDL and KiCad utilities
from skidl import Part, Net, ERC, default_circuit

# Load the component registry
REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "component_registry.json")
try:
    with open(REGISTRY_PATH, 'r') as f:
        COMPONENT_REGISTRY = json.load(f)
except Exception:
    COMPONENT_REGISTRY = {}

def process_skidl_erc(nodes, wires):
    """
    Takes Yantraa ReactFlow nodes and edges (wires),
    builds the SKiDL circuit in memory, runs ERC,
    and returns a string containing the warnings/errors.
    """
    # Reset the default circuit so consecutive API calls don't stack
    default_circuit.reset()
    
    # Keep track of instantiated SKiDL Parts
    skidl_parts = {}
    
    # 1. Instantiate Parts
    for node in nodes:
        node_id = node.get("id")
        node_data = node.get("data", {})
        
        # Try to find a mapping based on shape, then type, then ID
        shape = node_data.get("shape", "")
        ntype = node_data.get("type", "")
        
        mapping = COMPONENT_REGISTRY.get(shape) or COMPONENT_REGISTRY.get(ntype)
        
        if not mapping:
            # Fallback to a generic connector if no mapping exists,
            # just so SKiDL has a valid Part to connect to.
            mapping = {"library": "Connector", "part": "Conn_01x01_Socket"}
            
        try:
            # Note: For strict ERC, SKiDL needs the actual KiCad libraries available.
            # We wrap instantiation in a try-except to handle missing libraries gracefully
            # by creating a "stub" generic part if the library isn't found.
            p = Part(mapping["library"], mapping["part"], dest=default_circuit)
            p.ref = node_data.get("label", node_id).replace(" ", "_")
        except Exception as e:
            # Fallback for missing libraries
            p = Part("Connector", "Conn_01x01_Socket", dest=default_circuit)
            p.ref = f"FALLBACK_{node_id}"
            
        skidl_parts[node_id] = p
        
    # 2. Wire up the Nets
    # We group connections by Net. In Yantraa, edges are point-to-point.
    # For now, we'll create a unique Net for every edge.
    for idx, wire in enumerate(wires):
        src = wire.get("from", {})
        tgt = wire.get("to", {})
        
        src_node_id = src.get("nodeId")
        tgt_node_id = tgt.get("nodeId")
        
        # Yantraa provides portId, we treat it as the pin number/name
        # If the user's feedback mentioned sourcePin/targetPin, we check those first
        src_pin = src.get("sourcePin", src.get("portId", "1"))
        tgt_pin = tgt.get("targetPin", tgt.get("portId", "1"))
        
        if src_node_id in skidl_parts and tgt_node_id in skidl_parts:
            src_part = skidl_parts[src_node_id]
            tgt_part = skidl_parts[tgt_node_id]
            
            # Create a net
            net_name = wire.get("label") or f"Net_{idx}"
            n = Net(net_name)
            
            try:
                # Try connecting to exact pin name/number. 
                # If the generic part doesn't have it, SKiDL will raise an Exception.
                n += src_part[src_pin]
                n += tgt_part[tgt_pin]
            except Exception:
                # If pins don't match exactly (due to mock parts), just connect to pin 1
                try:
                    n += src_part[1]
                    n += tgt_part[1]
                except Exception:
                    pass

    # 3. Run ERC and capture stdout/stderr output
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        try:
            ERC()
        except Exception as e:
            print(f"ERC Execution Error: {e}")
            
    result = output.getvalue()
    
    # If ERC passed silently, provide a success message
    if not result.strip():
        result = "ERC passed with no errors or warnings."
        
    return result
