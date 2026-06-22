import re

with open('frontend/src/components/ui/tabs/mapping-tab.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

with open('scratch/gen_conn.ts', 'r', encoding='utf-16le') as f:
    gen_conn_text = f.read()

# Replace the specific label matching lines inside gen_conn_text
old_label_code = """            let label = "connection";
            if (pairKey === "actuator-controller" || pairKey === "controller-actuator") label = "drive";
            else if (pairKey.includes("sensor") && pairKey.includes("power")) label = "power";
            else if (pairKey.includes("sensor")) label = "data";
            else if (pairKey.includes("power")) label = "power";
            else if (pairKey.includes("electronic")) label = "signal";
            else if (pairKey.includes("mechanical")) label = "linkage";"""

new_label_code = """            let label = "connection";
            if (pairKey.includes("mechanical")) label = "linkage";
            else if (pairKey === "actuator-controller" || pairKey === "controller-actuator") label = "drive";
            else if (pairKey.includes("sensor") && pairKey.includes("power")) label = "power";
            else if (pairKey.includes("sensor")) label = "data";
            else if (pairKey.includes("power")) label = "power";
            else if (pairKey.includes("electronic")) label = "signal";"""

gen_conn_text = gen_conn_text.replace(old_label_code, new_label_code)

# Insert it back where the NetworkX comment is
nx_comment = """// The connection generation logic has been migrated to the Python backend (src/api/mapping/generate.py)
// utilizing networkx.DiGraph for superior topological sorting and validation."""

content = content.replace(nx_comment, gen_conn_text)

# Also restore SEED_CONNECTIONS initialization
content = content.replace("const SEED_CONNECTIONS: Connection[] = [];", "const SEED_CONNECTIONS = generateConnections(SEED_BASE_NODES as ComponentNode[], SEED_RAW);")

# Also fix doFetch
old_do_fetch = """        try {
            const res = await fetch("http://localhost:8000/api/mapping/build-graph", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ components: updatedRaw })
            });
            if (res.ok) {
                const data = await res.json();
                if (data.warnings && data.warnings.length > 0) {
                    console.warn("[NetworkX Mapping Warnings]:", data.warnings);
                }
                const newConnections = data.connections;
                setConnections(newConnections);
                const layoutedNodes = applyLayout(updatedNodes, newConnections);
                setNodes(layoutedNodes);
            } else {
                console.error("Failed to fetch graph from backend", await res.text());
                const layoutedNodes = applyLayout(updatedNodes, []);
                setNodes(layoutedNodes);
            }
        } catch (e) {
            console.error("Backend unreachable", e);
            const layoutedNodes = applyLayout(updatedNodes, []);
            setNodes(layoutedNodes);
        }"""

new_do_fetch = """        const newConnections = generateConnections(updatedNodes, updatedRaw);
        setConnections(newConnections);
        const layoutedNodes = applyLayout(updatedNodes, newConnections);
        setNodes(layoutedNodes);"""

content = content.replace(old_do_fetch, new_do_fetch)

with open('frontend/src/components/ui/tabs/mapping-tab.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done replacing mapping-tab.tsx")
