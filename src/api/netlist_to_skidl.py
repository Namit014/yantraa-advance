import sys
import io
import contextlib
from skidl import Part, Net, ERC, default_circuit

def run_erc_on_netlist(logical_netlist: dict) -> list:
    """
    Takes a LogicalNetlist dict (components[], nets[])
    Builds a SKiDL circuit in memory, runs ERC,
    and returns a structured list of ERC issues.
    """
    # Reset the default circuit so consecutive API calls don't stack
    default_circuit.reset()
    
    components = logical_netlist.get("components", [])
    nets = logical_netlist.get("nets", [])
    
    skidl_parts = {}
    issues = []
    
    # 1. Instantiate Parts
    for comp in components:
        comp_id = comp.get("id")
        part_id = comp.get("partId")
        designator = comp.get("designator", comp_id)
        
        # We create a generic connector part for SKiDL because we don't have
        # proper KiCad library parts mapped for all our modules yet.
        # This generic part will have as many pins as our logical component.
        try:
            p = Part("Connector", "Conn_01x01_Socket", dest=default_circuit)
            p.ref = designator.replace(" ", "_")
        except Exception:
            p = Part("Connector", "Conn_01x01_Socket", dest=default_circuit)
            p.ref = f"FALLBACK_{comp_id}"
            
        skidl_parts[comp_id] = p
        
    # 2. Wire up the Nets
    for net in nets:
        net_name = net.get("name", "UnnamedNet")
        members = net.get("members", [])
        
        # SKiDL Net
        n = Net(net_name)
        
        for member in members:
            comp_id = member.get("componentId")
            pin_name = member.get("pinName")
            
            if comp_id in skidl_parts:
                part = skidl_parts[comp_id]
                try:
                    # In SKiDL, if the part doesn't have the named pin, it might throw.
                    # Since we are using generic 1-pin parts right now to just get 
                    # the netlist to compile, we will attach to pin '1' for everything
                    # to test connectivity conceptually, but we will rely on our own 
                    # Python structural validation for pin compatibility.
                    n += part[1] 
                except Exception:
                    pass

    # 3. Run ERC and capture stdout/stderr output
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        try:
            ERC()
        except Exception as e:
            issues.append({
                "severity": "error",
                "message": f"ERC Execution Error: {e}"
            })
            
    result = output.getvalue()
    
    # Parse SKiDL ERC output (crude parsing for now)
    if result.strip():
        lines = result.split("\n")
        for line in lines:
            if not line.strip(): continue
            if "WARNING" in line.upper():
                issues.append({"severity": "warning", "message": line.strip()})
            elif "ERROR" in line.upper():
                issues.append({"severity": "error", "message": line.strip()})
            else:
                issues.append({"severity": "info", "message": line.strip()})
                
    return issues
