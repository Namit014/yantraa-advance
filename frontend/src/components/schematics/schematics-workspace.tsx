"use client";

import { useEffect, useMemo, useRef } from "react";
import {
    ReactFlow,
    Background,
    BackgroundVariant,
    Controls,
    MiniMap,
    ConnectionLineType,
    useReactFlow,
    ReactFlowProvider
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Sparkles, Loader2, Download, Maximize, AlertCircle } from "lucide-react";
import { useSchematicsStore } from "./useSchematicsStore";
import { SchematicNodeComponent } from "./SchematicNode";

function FlowCanvas({ currentQuery }: { currentQuery?: string; designData?: any }) {
    const store = useSchematicsStore();
    const { fitView } = useReactFlow();
    
    // Auto-fit view when triggered by store
    useEffect(() => {
        if (store.fitViewRequest > 0) {
            setTimeout(() => {
                fitView({ padding: 0.2, maxZoom: 1 });
            }, 100);
        }
    }, [store.fitViewRequest, fitView]);

    const nodeTypes = useMemo(() => ({ schematicNode: SchematicNodeComponent as any }), []);

    // Initial generate
    const hasGenerated = useRef(false);
    useEffect(() => {
        const query = currentQuery?.trim();
        if (query && !hasGenerated.current) {
            hasGenerated.current = true;
            store.setPrompt(query);
            store.generate(query);
        }
    }, [currentQuery, store]);

    return (
        <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%", backgroundColor: "#000000", color: "#FFFFFF", fontFamily: "monospace", borderRadius: "8px", overflow: "hidden", border: "1px solid #333" }}>
            {/* Top Toolbar */}
            <div style={{ display: "flex", alignItems: "center", padding: "10px 16px", borderBottom: "1px solid #333333", backgroundColor: "#111111", gap: "16px", flexShrink: 0 }}>
                <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "8px" }}>
                    <Sparkles size={16} />
                    <span style={{ fontWeight: "bold" }}>AI Schematics</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <button 
                        onClick={() => fitView({ padding: 0.2 })}
                        style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 12px", background: "#222222", border: "1px solid #444", borderRadius: "4px", cursor: "pointer", color: "#fff", fontSize: "12px" }}
                    >
                        <Maximize size={14} /> Fit Screen
                    </button>
                    <button 
                        disabled
                        style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 12px", background: "#222222", border: "1px solid #444", borderRadius: "4px", opacity: 0.5, cursor: "not-allowed", color: "#fff", fontSize: "12px" }}
                    >
                        <Download size={14} /> SVG
                    </button>
                    <button 
                        disabled
                        style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 12px", background: "#222222", border: "1px solid #444", borderRadius: "4px", opacity: 0.5, cursor: "not-allowed", color: "#fff", fontSize: "12px" }}
                    >
                        <Download size={14} /> PNG
                    </button>
                    <button 
                        disabled
                        style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 12px", background: "#222222", border: "1px solid #444", borderRadius: "4px", opacity: 0.5, cursor: "not-allowed", color: "#fff", fontSize: "12px" }}
                    >
                        KiCad Netlist
                    </button>
                </div>
            </div>
            
            {/* Main Area */}
            <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
                {/* Canvas */}
                <div style={{ flex: 1, position: "relative" }}>
                    {store.isGenerating && (
                        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", zIndex: 10, background: "rgba(0,0,0,0.85)" }}>
                            <Loader2 size={32} className="animate-spin mb-4 text-[#3b82f6]" />
                            <div style={{ color: "#60a5fa" }}>Generating Component-level Schematic...</div>
                        </div>
                    )}
                    {store.error && (
                        <div style={{ position: "absolute", top: 16, left: 16, zIndex: 10, background: "#440000", border: "1px solid #FF0000", padding: "8px 16px", borderRadius: "4px", display: "flex", alignItems: "center", gap: "8px" }}>
                            <AlertCircle size={16} color="#FF5555" />
                            <span style={{ color: "#FF5555", fontSize: "13px" }}>{store.error}</span>
                        </div>
                    )}
                    {!store.isGenerating && store.nodes.length === 0 && !store.error && (
                        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", zIndex: 5, pointerEvents: "none", opacity: 0.7 }}>
                            <div style={{ marginBottom: "12px" }}>
                                <Sparkles size={32} style={{ color: "#555" }} />
                            </div>
                            <div style={{ fontSize: "14px", color: "#888" }}>Waiting for robot prompt...</div>
                        </div>
                    )}
                    <ReactFlow
                        nodes={store.nodes}
                        edges={store.edges}
                        nodeTypes={nodeTypes}
                        nodesDraggable={true} // Allow dragging to fix layout manually if needed
                        nodesConnectable={false}
                        elementsSelectable={true}
                        connectionLineType={ConnectionLineType.Step}
                        minZoom={0.05}
                        maxZoom={4}
                        proOptions={{ hideAttribution: true }}
                    >
                        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#333333" />
                        <Controls style={{ background: "#111111", border: "1px solid #333333", fill: "#fff" }} />
                        <MiniMap style={{ background: "#111111", border: "1px solid #333333" }} maskColor="rgba(0,0,0,0.7)" nodeColor="#FFFFFF" />
                    </ReactFlow>
                </div>
                
                {/* Sidebar */}
                <div style={{ width: "300px", background: "#111111", borderLeft: "1px solid #333333", display: "flex", flexDirection: "column", flexShrink: 0 }}>
                    <div style={{ padding: "12px 16px", borderBottom: "1px solid #333333", fontWeight: "bold", fontSize: "13px", color: "#ddd" }}>Project Data</div>
                    <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
                        <div style={{ marginBottom: "24px" }}>
                            <div style={{ color: "#888888", marginBottom: "8px", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Generated BOM ({store.bom.length})</div>
                            {store.bom.length === 0 && <div style={{ opacity: 0.5, fontSize: "12px" }}>No components</div>}
                            {store.bom.map((item, i) => (
                                <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", padding: "6px 0", borderBottom: "1px solid #222" }}>
                                    <span>{item.name}</span>
                                    <span style={{ color: "#888" }}>x{item.qty}</span>
                                </div>
                            ))}
                        </div>
                        
                        <div style={{ marginBottom: "24px" }}>
                            <div style={{ color: "#888888", marginBottom: "8px", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Validation Checks</div>
                            {store.validation.length === 0 && <div style={{ opacity: 0.5, fontSize: "12px" }}>No issues found</div>}
                            {store.validation.map((v, i) => (
                                <div key={i} style={{ display: "flex", gap: "8px", fontSize: "11px", padding: "8px", background: v.type === 'error' ? '#310' : '#330', borderLeft: `2px solid ${v.type === 'error' ? '#f00' : '#ff0'}`, marginBottom: "8px" }}>
                                    <AlertCircle size={14} color={v.type === 'error' ? '#f55' : '#fd0'} style={{ flexShrink: 0 }} />
                                    <span>{v.message}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export function SchematicsWorkspace({ currentQuery, designData }: { currentQuery?: string; designData?: any }) {
    return (
        <ReactFlowProvider>
            <FlowCanvas currentQuery={currentQuery} designData={designData} />
        </ReactFlowProvider>
    );
}
