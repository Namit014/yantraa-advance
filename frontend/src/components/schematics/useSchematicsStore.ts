import { create } from "zustand";
import type { Node, Edge } from "@xyflow/react";
import dagre from "dagre";

// --- Types ---
export interface SchematicPin {
    id: string;
    label: string;
    side: "top" | "bottom" | "left" | "right";
}

export interface SchematicComponent {
    id: string;
    label: string;
    type: string;
    pins: SchematicPin[];
}

export interface SchematicNetConnection {
    component: string;
    pin: string;
}

export interface SchematicNet {
    id: string;
    label: string;
    connections: SchematicNetConnection[];
}

export interface SchematicBOM {
    name: string;
    qty: number;
}

export interface SchematicValidation {
    type: "warning" | "error" | "info";
    message: string;
}

// React Flow data payload
export interface SchematicNodeData extends Record<string, unknown> {
    label: string;
    type: string;
    pins: SchematicPin[];
}

export type SchematicNode = Node<SchematicNodeData>;
export type SchematicEdge = Edge;

interface SchematicsState {
    prompt: string;
    setPrompt: (p: string) => void;
    
    isGenerating: boolean;
    error: string | null;
    
    nodes: SchematicNode[];
    edges: SchematicEdge[];
    bom: SchematicBOM[];
    validation: SchematicValidation[];
    
    generate: (prompt: string) => Promise<void>;
    fitViewRequest: number;
    triggerFitView: () => void;
}

export const useSchematicsStore = create<SchematicsState>((set, get) => ({
    prompt: "",
    setPrompt: (prompt) => set({ prompt }),
    
    isGenerating: false,
    error: null,
    
    nodes: [],
    edges: [],
    bom: [],
    validation: [],
    
    fitViewRequest: 0,
    triggerFitView: () => set((state) => ({ fitViewRequest: state.fitViewRequest + 1 })),
    
    generate: async (prompt: string) => {
        set({ isGenerating: true, error: null });
        try {
            const url = process.env.NODE_ENV === 'production' 
                ? 'https://api.yantraa.tech/api/schematics/generate'
                : 'http://localhost:8000/api/schematics/generate';
                
            const res = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt }),
            });
            
            if (!res.ok) {
                throw new Error(`API Error: ${res.statusText}`);
            }
            
            const data = await res.json();
            
            // Build Nodes
            const nodes: SchematicNode[] = (data.components || []).map((comp: SchematicComponent) => {
                return {
                    id: comp.id,
                    type: "schematicNode",
                    position: { x: 0, y: 0 },
                    data: {
                        label: comp.label,
                        type: comp.type,
                        pins: comp.pins || [],
                    }
                };
            });
            
            // Build Edges
            const edges: SchematicEdge[] = [];
            (data.nets || []).forEach((net: SchematicNet) => {
                const conns = net.connections || [];
                // Connect the first connection to all others (simple star topology for nets)
                if (conns.length > 1) {
                    const source = conns[0];
                    for (let i = 1; i < conns.length; i++) {
                        const target = conns[i];
                        edges.push({
                            id: `edge-${net.id}-${i}`,
                            source: source.component,
                            sourceHandle: source.pin,
                            target: target.component,
                            targetHandle: target.pin,
                            type: 'step', // standard right-angle routing
                            label: net.label,
                            style: { stroke: "#FFFFFF", strokeWidth: 1.5 },
                            animated: false,
                        });
                    }
                }
            });
            
            // Layout using Dagre
            const dagreGraph = new dagre.graphlib.Graph();
            dagreGraph.setDefaultEdgeLabel(() => ({}));
            dagreGraph.setGraph({ rankdir: "LR", nodesep: 150, ranksep: 250 });
            
            nodes.forEach((node) => {
                dagreGraph.setNode(node.id, { width: 120, height: 180 });
            });
            
            edges.forEach((edge) => {
                dagreGraph.setEdge(edge.source, edge.target);
            });
            
            dagre.layout(dagreGraph);
            
            const layoutedNodes = nodes.map((node) => {
                const nodeWithPosition = dagreGraph.node(node.id);
                return {
                    ...node,
                    position: {
                        x: nodeWithPosition.x - 60,
                        y: nodeWithPosition.y - 90,
                    },
                };
            });
            
            set({
                nodes: layoutedNodes,
                edges,
                bom: data.bom || [],
                validation: data.validation || [],
                isGenerating: false,
            });
            
            get().triggerFitView();
            
        } catch (err: any) {
            console.error(err);
            set({ isGenerating: false, error: err.message || "Failed to generate schematic." });
        }
    },
}));
