"use client";

import {
    Search, X, SlidersHorizontal, Plus, Crosshair,
    LayoutGrid, Maximize2, Trash2, RefreshCw, Network
} from "lucide-react";
import { useState, useRef, useEffect, useCallback, useMemo } from "react";

// ─── RAG endpoint (same as v0-ai-chat.tsx) ────────────────────────────────────
const RAG_ENDPOINT = `${process.env.NEXT_PUBLIC_API_URL}/api/ask`;

// ─── Types ────────────────────────────────────────────────────────────────────

type ComponentCategory =
    | "actuator"
    | "sensor"
    | "controller"
    | "mechanical"
    | "power"
    | "electronic";

interface RawComponent {
    name: string;
    category: ComponentCategory;
    description: string;
    connects_to: string[];
}

interface ComponentNode {
    id: string;
    label: string;
    category: ComponentCategory;
    description: string;
    x: number;
    y: number;
    width?: number;
    height?: number;
}

interface Connection {
    id: string;
    fromId: string;
    toId: string;
    label: string;
    isUserEdited: boolean;
}

// ─── Category config ──────────────────────────────────────────────────────────

const CATEGORY_COLOR: Record<ComponentCategory, string> = {
    actuator: "#f97316",
    sensor: "#22d3ee",
    controller: "#a78bfa",
    mechanical: "#94a3b8",
    power: "#facc15",
    electronic: "#4ade80",
};

const CATEGORY_ORDER: ComponentCategory[] = [
    "mechanical",
    "actuator",
    "controller",
    "sensor",
    "power",
    "electronic",
];

// ─── Keyword-based category inference ─────────────────────────────────────────

function inferCategory(text: string): ComponentCategory {
    const t = text.toLowerCase();
    if (/motor|servo|actuator|pneumatic|hydraulic/.test(t)) return "actuator";
    if (/sensor|encoder|imu|lidar|camera|gyro|accelero|proximity|force|torque/.test(t)) return "sensor";
    if (/controller|mcu|microcontroller|plc|cpu|arduino|raspberry|fpga|driver|board/.test(t)) return "controller";
    if (/frame|arm|link|rod|joint|bracket|shaft|bearing|gear|effector|structure|base/.test(t)) return "mechanical";
    if (/power|supply|battery|cable|wire|psu|capacitor|regulator/.test(t)) return "power";
    return "electronic";
}

// ─── RAG fetcher ──────────────────────────────────────────────────────────────

const VALID_CATEGORIES: ComponentCategory[] = [
    "actuator", "sensor", "controller", "mechanical", "power", "electronic",
];

function parseRAGJson(text: string): RawComponent[] | null {
    try {
        // Strip markdown fences
        const cleaned = text
            .replace(/```json\s*/gi, "")
            .replace(/```\s*/g, "")
            .trim();
        const start = cleaned.indexOf("[");
        const end = cleaned.lastIndexOf("]");
        if (start === -1 || end === -1) return null;
        const arr = JSON.parse(cleaned.slice(start, end + 1));
        if (!Array.isArray(arr)) return null;
        return arr.map((item: Record<string, unknown>) => ({
            name: String(item.name ?? "Unknown"),
            category: VALID_CATEGORIES.includes(item.category as ComponentCategory)
                ? (item.category as ComponentCategory)
                : inferCategory(String(item.name ?? "")),
            description: String(item.description ?? ""),
            connects_to: Array.isArray(item.connects_to)
                ? item.connects_to.map(String)
                : [],
        }));
    } catch {
        return null;
    }
}

function fallbackExtract(aiResponse: string): RawComponent[] {
    const results: RawComponent[] = [];
    const lines = aiResponse.split(/\n/).map(l => l.trim()).filter(Boolean);
    for (const line of lines) {
        const match = line.match(/^\d+[\.\)]\s+\*?\*?([A-Z][A-Za-z0-9 /\-]+)\*?\*?:?/);
        const boldMatch = line.match(/^\*\*([A-Z][A-Za-z0-9 /\-]+)\*\*:?/);
        const raw = match?.[1] ?? boldMatch?.[1];
        if (!raw || raw.length < 3) continue;
        results.push({
            name: raw.trim(),
            category: inferCategory(raw),
            description: "",
            connects_to: [],
        });
    }
    return results;
}

async function fetchComponentsFromRAG(
    topic: string,
    aiResponseFallback: string
): Promise<RawComponent[]> {
    const prompt1 =
        `Return ONLY a JSON array. No explanation, no markdown, no extra text. ` +
        `For the topic: '${topic}', list a comprehensive and highly detailed set of low-level hardware components needed to build this robot (e.g., specific microcontrollers, specific sensors, motor drivers, high-torque servos, lipo batteries, structural brackets, etc.). Provide at least 8 to 15 components if possible. Do NOT just say "arm" or "leg". ` +
        `Each item must have exactly these fields: ` +
        `{"name": string, "category": one of exactly: "actuator"|"sensor"|"controller"|"mechanical"|"power"|"electronic", ` +
        `"description": string, "connects_to": string[]}`;

    try {
        const res1 = await fetch(RAG_ENDPOINT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: prompt1 }),
        });
        if (res1.ok) {
            const data1 = await res1.json();
            const parsed1 = parseRAGJson(String(data1.response ?? ""));
            if (parsed1 && parsed1.length > 0) return parsed1;
        }
    } catch { /* fall through */ }

    // Second attempt — stricter
    const prompt2 =
        `Output only raw JSON, no prose. Array of objects with fields: name, category, description, connects_to. ` +
        `Topic: '${topic}'`;
    try {
        const res2 = await fetch(RAG_ENDPOINT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: prompt2 }),
        });
        if (res2.ok) {
            const data2 = await res2.json();
            const parsed2 = parseRAGJson(String(data2.response ?? ""));
            if (parsed2 && parsed2.length > 0) return parsed2;
        }
    } catch { /* fall through */ }

    // Keyword fallback
    return fallbackExtract(aiResponseFallback);
}

// ─── Layout ───────────────────────────────────────────────────────────────────

const NODE_W = 140 as const;
const NODE_H = 88 as const;
const VIRTUAL_W = 1200;

function applyLayout(rawNodes: Omit<ComponentNode, "x" | "y">[]): ComponentNode[] {
    const byCategory: Partial<Record<ComponentCategory, typeof rawNodes>> = {};
    rawNodes.forEach(n => {
        if (!byCategory[n.category]) byCategory[n.category] = [];
        byCategory[n.category]!.push(n);
    });

    const result: ComponentNode[] = [];
    let rowIndex = 0;

    CATEGORY_ORDER.forEach(cat => {
        const group = byCategory[cat];
        if (!group || group.length === 0) return;
        const rowW = group.length * 180;
        const startX = Math.max(60, (VIRTUAL_W - rowW) / 2);
        group.forEach((n, i) => {
            result.push({
                ...(n as ComponentNode),
                x: startX + i * 180,
                y: 80 + rowIndex * 160,
            });
        });
        rowIndex++;
    });

    return result;
}

// ─── Connection generator ─────────────────────────────────────────────────────

function generateConnections(
    nodes: ComponentNode[],
    raw: RawComponent[]
): Connection[] {
    const connections: Connection[] = [];
    const seen = new Set<string>();

    function addConn(
        fromId: string,
        toId: string,
        label: string,
        userEdited = false
    ) {
        if (!fromId || !toId || fromId === toId) return;
        const key1 = `${fromId}→${toId}`;
        const key2 = `${toId}→${fromId}`;
        if (seen.has(key1) || seen.has(key2)) return;
        seen.add(key1);
        connections.push({
            id: `conn-${connections.length}-${Date.now()}`,
            fromId,
            toId,
            label,
            isUserEdited: userEdited,
        });
    }

    const nodeMap = new Map<string, ComponentNode>();
    nodes.forEach(n => nodeMap.set(n.id, n));

    // Primary pass — use RAG connects_to
    raw.forEach(rc => {
        const fromNode = nodes.find(
            n => n.label.toLowerCase().trim() === rc.name.toLowerCase().trim()
        );
        if (!fromNode) return;
        rc.connects_to.forEach(targetName => {
            const toNode = nodes.find(
                n => n.label.toLowerCase().trim() === targetName.toLowerCase().trim()
            );
            if (!toNode) return;
            const pairKey = `${fromNode.category}-${toNode.category}`;
            const label =
                pairKey === "actuator-controller" || pairKey === "controller-actuator"
                    ? "drive"
                    : pairKey.includes("sensor")
                    ? "data"
                    : pairKey.includes("power")
                    ? "power"
                    : pairKey.includes("electronic")
                    ? "signal"
                    : pairKey.includes("mechanical")
                    ? "linkage"
                    : "connection";
            addConn(fromNode.id, toNode.id, label);
        });
    });

    // Secondary fallback for any unconnected nodes
    const byCategory: Partial<Record<ComponentCategory, ComponentNode[]>> = {};
    nodes.forEach(n => {
        if (!byCategory[n.category]) byCategory[n.category] = [];
        byCategory[n.category]!.push(n);
    });

    const controllers = byCategory["controller"] ?? [];
    const actuators = byCategory["actuator"] ?? [];
    const sensors = byCategory["sensor"] ?? [];
    const mechanical = byCategory["mechanical"] ?? [];
    const power = byCategory["power"] ?? [];
    const electronic = byCategory["electronic"] ?? [];

    // Only connect nodes that have zero connections so far
    const connectedIds = new Set<string>();
    connections.forEach(c => {
        connectedIds.add(c.fromId);
        connectedIds.add(c.toId);
    });

    actuators
        .filter(a => !connectedIds.has(a.id))
        .forEach(a => controllers.forEach(c => addConn(a.id, c.id, "drive")));
    sensors
        .filter(s => !connectedIds.has(s.id))
        .forEach(s => controllers.forEach(c => addConn(s.id, c.id, "data")));
    mechanical
        .filter(m => !connectedIds.has(m.id))
        .forEach((m, i) => {
            const target = actuators[i % Math.max(1, actuators.length)];
            if (target) addConn(m.id, target.id, "linkage");
        });
    power
        .filter(p => !connectedIds.has(p.id))
        .forEach(p => {
            controllers.forEach(c => addConn(p.id, c.id, "power"));
            actuators.forEach(a => addConn(p.id, a.id, "power"));
        });
    controllers
        .filter(c => !connectedIds.has(c.id))
        .forEach(c => electronic.forEach(e => addConn(c.id, e.id, "signal")));

    return connections;
}

// ─── Seed data ────────────────────────────────────────────────────────────────

const SEED_RAW: RawComponent[] = [
    { name: "Motion Controller", category: "controller", description: "Main MCU coordinating all subsystems", connects_to: ["Servo Motor A", "Servo Motor B", "IMU Sensor"] },
    { name: "Servo Motor A", category: "actuator", description: "Upper arm drive servo, 180° range", connects_to: ["Arm Frame"] },
    { name: "Servo Motor B", category: "actuator", description: "Lower arm drive servo, 270° range", connects_to: ["Arm Frame"] },
    { name: "IMU Sensor", category: "sensor", description: "6-axis inertial measurement unit", connects_to: [] },
    { name: "Arm Frame", category: "mechanical", description: "Aluminium extruded structural frame", connects_to: [] },
    { name: "Power Supply", category: "power", description: "24V regulated DC power supply", connects_to: ["Motion Controller", "Servo Motor A", "Servo Motor B"] },
];

const SEED_NODES: ComponentNode[] = applyLayout(
    SEED_RAW.map((r, i) => ({
        id: `seed-${i}`,
        label: r.name,
        category: r.category,
        description: r.description,
        width: NODE_W,
        height: NODE_H,
    }))
);

// ─── Inline SVG icons ─────────────────────────────────────────────────────────

function CategoryIcon({ category, size = 18 }: { category: ComponentCategory; size?: number }) {
    const c = CATEGORY_COLOR[category];
    const s = size;
    switch (category) {
        case "actuator":
            return (
                <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
                    <circle cx="10" cy="10" r="8" stroke={c} strokeWidth="1.5" />
                    <line x1="2" y1="10" x2="18" y2="10" stroke={c} strokeWidth="1.5" />
                    <line x1="10" y1="2" x2="10" y2="18" stroke={c} strokeWidth="1.5" />
                </svg>
            );
        case "sensor":
            return (
                <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
                    <circle cx="10" cy="10" r="2.5" fill={c} />
                    <path d="M5.5 14.5 A6.4 6.4 0 0 1 14.5 14.5" stroke={c} strokeWidth="1.5" fill="none" />
                    <path d="M2.5 17 A10.6 10.6 0 0 1 17.5 17" stroke={c} strokeWidth="1" fill="none" opacity="0.45" />
                </svg>
            );
        case "controller":
            return (
                <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
                    <rect x="4" y="4" width="12" height="12" rx="2" stroke={c} strokeWidth="1.5" />
                    <line x1="7" y1="7" x2="9" y2="7" stroke={c} strokeWidth="1" />
                    <line x1="11" y1="7" x2="13" y2="7" stroke={c} strokeWidth="1" />
                    <line x1="7" y1="10" x2="13" y2="10" stroke={c} strokeWidth="1" />
                    <line x1="7" y1="13" x2="9" y2="13" stroke={c} strokeWidth="1" />
                    <line x1="11" y1="13" x2="13" y2="13" stroke={c} strokeWidth="1" />
                    <line x1="8" y1="1" x2="8" y2="4" stroke={c} strokeWidth="1" />
                    <line x1="12" y1="1" x2="12" y2="4" stroke={c} strokeWidth="1" />
                    <line x1="8" y1="16" x2="8" y2="19" stroke={c} strokeWidth="1" />
                    <line x1="12" y1="16" x2="12" y2="19" stroke={c} strokeWidth="1" />
                </svg>
            );
        case "mechanical":
            return (
                <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
                    <circle cx="10" cy="10" r="3.5" stroke={c} strokeWidth="1.5" />
                    <circle cx="10" cy="10" r="1.2" fill={c} />
                    <path d="M10 2 L11.2 5.5 L8.8 5.5 Z" fill={c} />
                    <path d="M10 18 L11.2 14.5 L8.8 14.5 Z" fill={c} />
                    <path d="M2 10 L5.5 11.2 L5.5 8.8 Z" fill={c} />
                    <path d="M18 10 L14.5 11.2 L14.5 8.8 Z" fill={c} />
                    <path d="M4.1 4.1 L6.6 6.6" stroke={c} strokeWidth="1.5" />
                    <path d="M15.9 15.9 L13.4 13.4" stroke={c} strokeWidth="1.5" />
                    <path d="M4.1 15.9 L6.6 13.4" stroke={c} strokeWidth="1.5" />
                    <path d="M15.9 4.1 L13.4 6.6" stroke={c} strokeWidth="1.5" />
                </svg>
            );
        case "power":
            return (
                <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
                    <path d="M11 2 L6 11 L10 11 L9 18 L14 9 L10 9 Z" fill={c} />
                </svg>
            );
        case "electronic":
            return (
                <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
                    <circle cx="5" cy="10" r="2.5" stroke={c} strokeWidth="1.5" />
                    <circle cx="15" cy="10" r="2.5" stroke={c} strokeWidth="1.5" />
                    <line x1="7.5" y1="10" x2="12.5" y2="10" stroke={c} strokeWidth="1.5" />
                    <circle cx="10" cy="10" r="1" fill={c} />
                </svg>
            );
    }
}


// ─── Props ────────────────────────────────────────────────────────────────────

interface MappingTabProps {
    aiResponse?: string;
    currentQuery?: string;
    designData?: any;
}

// ─── React Flow Custom Node ───────────────────────────────────────────────────

import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    addEdge,
    Connection as RFConnection,
    Edge,
    Node,
    MarkerType,
    Handle,
    Position,
    Panel,
    applyNodeChanges,
    NodeChange
} from 'reactflow';
import 'reactflow/dist/style.css';

const CustomComponentNode = ({ data }: any) => {
    const color = CATEGORY_COLOR[data.category as ComponentCategory] || "#ccc";
    return (
        <div style={{
            background: "#13161c",
            border: `1px solid ${color}50`,
            borderRadius: "8px",
            padding: "10px",
            minWidth: "150px",
            color: "white",
            fontSize: "12px",
            boxShadow: "0 4px 6px rgba(0,0,0,0.3)"
        }}>
            <Handle type="target" position={Position.Left} style={{ background: color }} />
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <div style={{ width: 20, height: 20, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <CategoryIcon category={data.category} size={14} />
                </div>
                <strong style={{ whiteSpace: "nowrap" }}>{data.label}</strong>
            </div>
            <div style={{ fontSize: "9px", color: color, textTransform: "uppercase", letterSpacing: "1px" }}>
                {data.category}
            </div>
            <Handle type="source" position={Position.Right} style={{ background: color }} />
        </div>
    );
};

const nodeTypes = {
    customComponent: CustomComponentNode,
};

// ─── Component ────────────────────────────────────────────────────────────────

export function MappingTab({ aiResponse = "", currentQuery = "", designData }: MappingTabProps) {
    const [activeView, setActiveView] = useState<"matrix" | "canvas">("canvas");
    
    const [nodes, setNodes] = useState<ComponentNode[]>(SEED_NODES);
    const [rawComponents, setRawComponents] = useState<RawComponent[]>(SEED_RAW);
    const [connections, setConnections] = useState<Connection[]>(() =>
        generateConnections(SEED_NODES, SEED_RAW) as any
    );
    const [isLoading, setIsLoading] = useState(false);
    const [selectedId, setSelectedId] = useState<string | null>(null);

    const [rfNodes, setRfNodes] = useState<Node[]>([]);
    
    useEffect(() => {
        setRfNodes(nodes.map((n, i) => ({
            id: n.id,
            type: 'customComponent',
            position: { x: n.x ?? (i * 200 % 800), y: n.y ?? (Math.floor(i * 200 / 800) * 150) },
            data: { label: n.label, category: n.category, description: n.description },
            ...(n.width && { width: n.width }),
            ...(n.height && { height: n.height })
        })));
    }, [nodes]);

    const onNodesChange = useCallback((changes: NodeChange[]) => {
        setRfNodes((nds) => {
            return applyNodeChanges(changes, nds);
        });
        
        setNodes((nds) => {
            let updated = [...nds];
            let changed = false;
            for (const change of changes) {
                if (change.type === 'position' && change.position) {
                    const idx = updated.findIndex(n => n.id === change.id);
                    if (idx !== -1) {
                        updated[idx] = { ...updated[idx], x: change.position.x, y: change.position.y };
                        changed = true;
                    }
                }
                if (change.type === 'dimensions' && change.dimensions) {
                    const idx = updated.findIndex(n => n.id === change.id);
                    if (idx !== -1) {
                        updated[idx] = { ...updated[idx], width: change.dimensions.width, height: change.dimensions.height };
                        changed = true;
                    }
                }
            }
            return changed ? updated : nds;
        });
    }, []);

    const [searchQuery, setSearchQuery] = useState("");
    
    const [showAddModal, setShowAddModal] = useState(false);
    const [newName, setNewName] = useState("");
    const [newCat, setNewCat] = useState<ComponentCategory>("electronic");
    const [newDesc, setNewDesc] = useState("");

    const [inspectorConnTarget, setInspectorConnTarget] = useState("");
    const [inspectorConnLabel, setInspectorConnLabel] = useState("wire");

    const lastQueryRef = useRef<string>("");
    const rfEdges: Edge[] = useMemo(() => {
        const WIRE_COLORS: Record<string, string> = {
            power: '#ef4444',
            ground: '#22c55e',
            signal: '#eab308',
            data: '#a855f7',
            drive: '#f97316',
            pwm: '#3b82f6',
            can: '#14b8a6',
            default: '#60a5fa'
        };

        return connections.map(c => {
            const edgeColor = WIRE_COLORS[c.label?.toLowerCase()] || WIRE_COLORS.default;
            return {
                id: c.id,
                source: c.fromId,
                target: c.toId,
                label: c.label,
                type: 'smoothstep',
                animated: false,
                style: { stroke: edgeColor, strokeWidth: 1.5 },
                labelStyle: { fill: '#a3a3a3', fontWeight: 600, fontSize: 11, className: 'edge-label-text' },
                labelBgStyle: { fill: '#13161c', className: 'edge-label-bg' },
                markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor },
                className: 'custom-edge-hover'
            };
        });
    }, [connections]);


    const onConnect = useCallback((params: RFConnection) => {
        if (!params.source || !params.target) return;
        const newConn = {
            id: `conn-rf-${Date.now()}`,
            fromId: params.source,
            toId: params.target,
            label: "wire",
            isUserEdited: true,
        };
        setConnections(prev => [...prev, newConn]);
    }, []);

    const doFetch = useCallback(async (q: string) => {
        setIsLoading(true);
        const raw = await fetchComponentsFromRAG(q, aiResponse);
        const nextRaw = [...rawComponents, ...raw];
        const nextNodes = nextRaw.map((r, i) => ({
            id: `rag-${Date.now()}-${i}`,
            label: r.name,
            category: r.category,
            description: r.description,
            x: 0, y: 0, width: NODE_W, height: NODE_H
        } as ComponentNode));
        
        setRawComponents(nextRaw);
        setNodes(applyLayout([...nodes, ...nextNodes]));
        setConnections(generateConnections([...nodes, ...nextNodes], nextRaw) as any);
        setIsLoading(false);
    }, [aiResponse, rawComponents, nodes]);

    useEffect(() => {
        if (currentQuery && currentQuery !== lastQueryRef.current) {
            lastQueryRef.current = currentQuery;
            doFetch(currentQuery);
        }
    }, [currentQuery, doFetch]);

    const handleClear = useCallback(() => {
        if (!window.confirm("Are you sure you want to clear all mapped components?")) return;
        setNodes([]);
        setConnections([]);
        setSelectedId(null);
        lastQueryRef.current = "";
    }, []);

    const handleRefresh = useCallback(() => {
        lastQueryRef.current = "";
        if (currentQuery) doFetch(currentQuery);
    }, [currentQuery, doFetch]);

    const handleAutoLayout = useCallback(() => {
        setNodes(prev => applyLayout(prev));
    }, []);

    const handleAddComponent = useCallback(() => {
        if (!newName.trim()) return;
        const newNode: ComponentNode = {
            id: `node-custom-${Date.now()}`,
            label: newName.trim(),
            category: newCat,
            description: newDesc.trim(),
            x: 0, y: 0, width: NODE_W as any, height: NODE_H as any,
        };
        const newRaw: RawComponent = {
            name: newName.trim(),
            category: newCat,
            description: newDesc.trim(),
            connects_to: [],
        };
        setNodes(prev => [...prev, newNode]);
        setRawComponents(prev => [...prev, newRaw]);
        setNewName("");
        setNewCat("electronic");
        setNewDesc("");
        setShowAddModal(false);
    }, [newName, newCat, newDesc]);

    const handleAddConnection = useCallback(() => {
        if (!selectedId || !inspectorConnTarget) return;
        const newConn = {
            id: `conn-user-${Date.now()}`,
            fromId: selectedId,
            toId: inspectorConnTarget,
            label: inspectorConnLabel || "wire",
            isUserEdited: true,
        };
        setConnections(prev => {
            const dup = prev.some(c => (c.fromId === selectedId && c.toId === inspectorConnTarget) || (c.fromId === inspectorConnTarget && c.toId === selectedId));
            return dup ? prev : [...prev, newConn];
        });
        setInspectorConnTarget("");
        setInspectorConnLabel("wire");
    }, [selectedId, inspectorConnTarget, inspectorConnLabel]);

    // Grouping nodes by category for the middle column
    const filteredNodes = nodes.filter(n => n.label.toLowerCase().includes(searchQuery.toLowerCase()));
    const groupedNodes: Partial<Record<ComponentCategory, ComponentNode[]>> = {};
    CATEGORY_ORDER.forEach(cat => { groupedNodes[cat] = []; });
    filteredNodes.forEach(n => {
        if (groupedNodes[n.category]) groupedNodes[n.category]!.push(n);
    });

    const selectedNode = nodes.find(n => n.id === selectedId);
    const inputsToSelected = connections.filter(c => c.toId === selectedId);
    const outputsFromSelected = connections.filter(c => c.fromId === selectedId);

    return (
        <div className="w-full h-full flex flex-col bg-[#050505] overflow-hidden text-neutral-400 font-sans">
            
            {/* TOP TOOLBAR: View Toggle */}
            <div className="h-12 border-b border-neutral-800/50 flex items-center justify-between px-6 bg-[#0B0E14] shrink-0 z-30">
                <div className="flex gap-1 bg-[#131823] p-1 rounded-lg border border-neutral-800/50">
                    <button 
                        onClick={() => setActiveView("matrix")}
                        className={`px-4 py-1.5 rounded text-xs font-bold transition-all ${activeView === 'matrix' ? 'bg-[#1a2333] text-sky-400 shadow' : 'text-neutral-500 hover:text-neutral-300'}`}
                    >
                        Matrix View
                    </button>
                    <button 
                        onClick={() => setActiveView("canvas")}
                        className={`px-4 py-1.5 rounded text-xs font-bold transition-all ${activeView === 'canvas' ? 'bg-[#1a2333] text-sky-400 shadow' : 'text-neutral-500 hover:text-neutral-300'}`}
                    >
                        Canvas Wiring View
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    {isLoading && <div className="text-xs text-blue-400 animate-pulse mr-4">Updating from AI...</div>}
                    <button onClick={handleAutoLayout} className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-purple-400 bg-purple-900/20 hover:bg-purple-900/40 rounded border border-purple-900/50 transition-colors"><Network size={12} /> Auto Layout</button>
                    <button onClick={handleRefresh} className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-sky-400 bg-sky-900/20 hover:bg-sky-900/40 rounded border border-sky-900/50 transition-colors"><RefreshCw size={12} /> Refresh</button>
                    <button onClick={handleClear} className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-red-400 bg-red-900/20 hover:bg-red-900/40 rounded border border-red-900/50 transition-colors"><Trash2 size={12} /> Clear</button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden relative">
                {/* 1. COMPONENT LIBRARY (Left Column) */}
                <div className="w-[320px] h-full bg-[#0B0E14] border-r border-neutral-800/50 flex flex-col shrink-0 z-20">
                    <div className="flex items-center justify-between p-4 pb-2 mt-2">
                        <h2 className="text-xs font-bold text-white tracking-widest uppercase">Component Library</h2>
                    </div>
                    <div className="px-4 py-3 flex gap-2">
                        <div className="flex-1 bg-[#131823] rounded-lg border border-neutral-800/50 flex items-center px-3">
                            <Search className="w-4 h-4 text-neutral-500 shrink-0" />
                            <input
                                type="text"
                                placeholder="Search library..."
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                className="w-full bg-transparent border-none text-xs text-neutral-200 focus:outline-none focus:ring-0 px-2 py-2.5 placeholder:text-neutral-600"
                            />
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#0a101d] hover:bg-[#1a2333] border border-blue-900/50 text-blue-400 hover:text-blue-300 rounded-lg text-xs font-semibold transition-colors mb-2"
                        >
                            + Add Custom Component
                        </button>
                        {filteredNodes.length === 0 ? (
                            <div className="text-neutral-500 text-xs text-center mt-10">No components found.</div>
                        ) : (
                            filteredNodes.map(node => {
                                const color = CATEGORY_COLOR[node.category] || "#666";
                                return (
                                    <div key={`lib-${node.id}`} className="flex items-center justify-between bg-[#131823] rounded-lg p-3 border border-neutral-800/50">
                                        <div className="flex items-center gap-3">
                                            <div style={{ width: 28, height: 28, background: "rgba(255,255,255,0.03)", border: `1px solid ${color}40`, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                                <CategoryIcon category={node.category} size={14} />
                                            </div>
                                            <div>
                                                <div className="text-white text-xs font-bold truncate max-w-[140px]">{node.label}</div>
                                                <div className="text-[10px]" style={{ color }}>{node.category}</div>
                                            </div>
                                        </div>
                                        <button onClick={() => {
                                            const newNode = { ...node, id: `node-dup-${Date.now()}` };
                                            setNodes(p => [...p, newNode]);
                                        }} className="text-neutral-500 hover:text-white bg-neutral-800/50 hover:bg-neutral-700/50 p-1.5 rounded-md transition-colors">
                                            <Plus size={14} />
                                        </button>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>

                {/* 2. DYNAMIC MAIN VIEW (Middle Column) */}
                <div className="flex-1 h-full bg-[#050505] relative border-r border-neutral-800/50 flex flex-col">
                    {activeView === "matrix" ? (
                        <div className="flex-1 overflow-y-auto p-6">
                            {CATEGORY_ORDER.map(cat => {
                                const group = groupedNodes[cat];
                                if (!group || group.length === 0) return null;
                                const catColor = CATEGORY_COLOR[cat];
                                return (
                                    <div key={cat} className="mb-8">
                                        <div className="text-[10px] font-black uppercase tracking-[0.15em] mb-3 flex items-center gap-2" style={{ color: catColor }}>
                                            <CategoryIcon category={cat} size={12} /> {cat}
                                            <div className="flex-1 h-px bg-gradient-to-r from-current to-transparent opacity-20 ml-2" />
                                        </div>
                                        <div className="flex flex-col gap-2">
                                            {group.map(node => {
                                                const isSelected = selectedId === node.id;
                                                const nodeOutputs = connections.filter(c => c.fromId === node.id);
                                                return (
                                                    <div 
                                                        key={node.id}
                                                        onClick={() => setSelectedId(node.id)}
                                                        className={`flex items-stretch bg-[#0f1219] rounded-xl border transition-all cursor-pointer overflow-hidden ${isSelected ? 'border-sky-500/50 shadow-[0_0_15px_rgba(14,165,233,0.15)] bg-[#131b26]' : 'border-neutral-800/60 hover:border-neutral-700 hover:bg-[#13161c]'}`}
                                                        style={{ minHeight: '64px' }}
                                                    >
                                                        <div className="w-1.5" style={{ background: catColor }} />
                                                        <div className="flex items-center gap-4 px-4 py-3 w-[300px] shrink-0 border-r border-neutral-800/50">
                                                            <div style={{ width: 36, height: 36, background: "rgba(255,255,255,0.02)", border: `1px solid ${catColor}30`, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                                                <CategoryIcon category={cat} size={20} />
                                                            </div>
                                                            <div className="min-w-0">
                                                                <div className="text-white text-[13px] font-bold truncate">{node.label}</div>
                                                                <div className="text-neutral-500 text-[10px] uppercase tracking-wider mt-0.5">Qty: 1</div>
                                                            </div>
                                                        </div>
                                                        <div className="flex-1 px-5 py-3 flex items-center flex-wrap gap-2">
                                                            {nodeOutputs.length === 0 ? (
                                                                <span className="text-neutral-600 text-xs italic">No outgoing connections</span>
                                                            ) : (
                                                                nodeOutputs.map(conn => {
                                                                    const targetNode = nodes.find(n => n.id === conn.toId);
                                                                    if (!targetNode) return null;
                                                                    return (
                                                                        <div 
                                                                            key={conn.id} 
                                                                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#1a1f2e] border border-neutral-700/50 text-neutral-300 hover:border-sky-500/50 hover:text-sky-300 transition-colors"
                                                                            onClick={(e) => { e.stopPropagation(); setSelectedId(targetNode.id); }}
                                                                        >
                                                                            <span className="text-neutral-500">⮑</span> {targetNode.label}
                                                                        </div>
                                                                    );
                                                                })
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="flex-1 w-full h-full relative" style={{ minHeight: 0 }}>
                            <div style={{ width: '100%', height: '100%' }}>
                                <style>{`
                                    .custom-edge-hover .edge-label-text, 
                                    .custom-edge-hover .edge-label-bg {
                                        opacity: 0;
                                        transition: opacity 0.2s ease-in-out;
                                    }
                                    .custom-edge-hover:hover .edge-label-text, 
                                    .custom-edge-hover:hover .edge-label-bg,
                                    .custom-edge-hover.selected .edge-label-text,
                                    .custom-edge-hover.selected .edge-label-bg {
                                        opacity: 1;
                                    }
                                `}</style>
                                <ReactFlow
                                    nodes={rfNodes}
                                    edges={rfEdges}
                                    onNodesChange={onNodesChange}
                                    onConnect={onConnect}
                                    onNodeClick={(_, node) => setSelectedId(node.id)}
                                    nodeTypes={nodeTypes}
                                    fitView
                                    proOptions={{ hideAttribution: true }}
                                >
                                    <Background color="#222" gap={16} />
                                    <Controls style={{ backgroundColor: '#13161c', border: '1px solid #333' }} />
                                </ReactFlow>
                            </div>
                        </div>
                    )}
                </div>

                {/* 3. INSPECTOR (Right Column) */}
                <div className="w-[340px] h-full bg-[#0B0E14] flex flex-col shrink-0 z-20">
                    <div className="flex items-center justify-between p-4 border-b border-neutral-800/50 bg-[#0f1219]">
                        <h2 className="text-xs font-bold text-white tracking-widest uppercase">Inspector</h2>
                    </div>
                    
                    {selectedNode ? (
                        <div className="flex-1 overflow-y-auto">
                            {/* Header Details */}
                            <div className="p-5 border-b border-neutral-800/50">
                                <div className="flex items-center gap-3 mb-4">
                                    <div style={{ width: 48, height: 48, background: "rgba(255,255,255,0.03)", border: `1px solid ${CATEGORY_COLOR[selectedNode.category]}40`, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                        <CategoryIcon category={selectedNode.category} size={24} />
                                    </div>
                                    <div>
                                        <h3 className="text-white text-sm font-bold leading-tight">{selectedNode.label}</h3>
                                        <span className="inline-block mt-1 text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded" style={{ background: `${CATEGORY_COLOR[selectedNode.category]}20`, color: CATEGORY_COLOR[selectedNode.category] }}>
                                            {selectedNode.category}
                                        </span>
                                    </div>
                                </div>
                                <div className="text-xs text-neutral-400 leading-relaxed mb-4">
                                    {selectedNode.description || "No description provided for this component."}
                                </div>
                                <button 
                                    onClick={() => {
                                        setNodes(p => p.filter(n => n.id !== selectedId));
                                        setConnections(p => p.filter(c => c.fromId !== selectedId && c.toId !== selectedId));
                                        setSelectedId(null);
                                    }}
                                    className="w-full py-2 bg-red-950/30 hover:bg-red-900/40 text-red-400 text-xs font-semibold rounded border border-red-900/30 transition-colors"
                                >
                                    Delete Component
                                </button>
                            </div>

                            {/* Connection Manager */}
                            <div className="p-5">
                                <h4 className="text-[11px] font-bold text-neutral-500 uppercase tracking-widest mb-4">Connection Manager</h4>
                                
                                <div className="mb-6">
                                    <div className="text-xs font-semibold text-neutral-300 mb-2 flex items-center gap-2"><span className="text-emerald-500">▼</span> Inputs To This</div>
                                    {inputsToSelected.length === 0 ? (
                                        <div className="text-xs text-neutral-600 bg-[#0f1219] p-3 rounded border border-neutral-800/50">None</div>
                                    ) : (
                                        <div className="flex flex-col gap-2">
                                            {inputsToSelected.map(conn => {
                                                const fromNode = nodes.find(n => n.id === conn.fromId);
                                                return (
                                                    <div key={conn.id} className="flex items-center justify-between bg-[#13161c] p-2.5 rounded border border-neutral-800/80">
                                                        <div className="text-xs text-neutral-300 truncate pr-2">From: <span className="font-medium text-white">{fromNode?.label || "Unknown"}</span></div>
                                                        <button onClick={() => setConnections(p => p.filter(c => c.id !== conn.id))} className="text-neutral-500 hover:text-red-400"><Trash2 size={12} /></button>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>

                                <div className="mb-6">
                                    <div className="text-xs font-semibold text-neutral-300 mb-2 flex items-center gap-2"><span className="text-sky-500">▲</span> Outputs From This</div>
                                    {outputsFromSelected.length === 0 ? (
                                        <div className="text-xs text-neutral-600 bg-[#0f1219] p-3 rounded border border-neutral-800/50">None</div>
                                    ) : (
                                        <div className="flex flex-col gap-2">
                                            {outputsFromSelected.map(conn => {
                                                const toNode = nodes.find(n => n.id === conn.toId);
                                                return (
                                                    <div key={conn.id} className="flex items-center justify-between bg-[#13161c] p-2.5 rounded border border-neutral-800/80">
                                                        <div className="text-xs text-neutral-300 truncate pr-2">To: <span className="font-medium text-white">{toNode?.label || "Unknown"}</span></div>
                                                        <button onClick={() => setConnections(p => p.filter(c => c.id !== conn.id))} className="text-neutral-500 hover:text-red-400"><Trash2 size={12} /></button>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>

                                {/* Add Connection */}
                                <div className="mt-8 pt-6 border-t border-neutral-800/50">
                                    <h5 className="text-[10px] font-bold text-neutral-500 uppercase tracking-widest mb-3">Add New Connection</h5>
                                    <div className="flex flex-col gap-3">
                                        <select 
                                            value={inspectorConnTarget} 
                                            onChange={e => setInspectorConnTarget(e.target.value)}
                                            className="w-full bg-[#0f1219] border border-neutral-800 rounded px-3 py-2 text-xs text-neutral-200 outline-none focus:border-sky-500/50"
                                        >
                                            <option value="">Select target component...</option>
                                            {nodes.filter(n => n.id !== selectedId).map(n => (
                                                <option key={`opt-${n.id}`} value={n.id}>{n.label}</option>
                                            ))}
                                        </select>
                                        <div className="flex gap-2">
                                            <input 
                                                value={inspectorConnLabel}
                                                onChange={e => setInspectorConnLabel(e.target.value)}
                                                placeholder="Connection label"
                                                className="flex-1 bg-[#0f1219] border border-neutral-800 rounded px-3 py-2 text-xs text-neutral-200 outline-none focus:border-sky-500/50"
                                            />
                                            <button 
                                                onClick={handleAddConnection}
                                                disabled={!inspectorConnTarget}
                                                className="px-4 bg-sky-600 hover:bg-sky-500 disabled:bg-neutral-800 disabled:text-neutral-600 text-white text-xs font-bold rounded transition-colors"
                                            >
                                                Add
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                            <div className="w-16 h-16 rounded-full bg-[#0f1219] border border-neutral-800 flex items-center justify-center mb-4 text-neutral-700">
                                <LayoutGrid size={24} />
                            </div>
                            <h3 className="text-sm font-semibold text-neutral-300 mb-2">No Component Selected</h3>
                            <p className="text-xs text-neutral-500 leading-relaxed">
                                Select a component from the Assembly Matrix to view its details and manage connections.
                            </p>
                        </div>
                    )}
                </div>

                {/* Add Custom Component Modal */}
                {showAddModal && (
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
                        <div className="w-[360px] bg-[#0B0E14] border border-neutral-800 rounded-xl shadow-2xl p-6">
                            <h3 className="text-sm font-bold text-white mb-4">Add Custom Component</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-1">Name</label>
                                    <input value={newName} onChange={e => setNewName(e.target.value)} className="w-full bg-[#131823] border border-neutral-800 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-sky-500/50" placeholder="e.g. LIDAR Sensor" />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-1">Category</label>
                                    <select value={newCat} onChange={e => setNewCat(e.target.value as ComponentCategory)} className="w-full bg-[#131823] border border-neutral-800 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-sky-500/50">
                                        {VALID_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-1">Description</label>
                                    <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={3} className="w-full bg-[#131823] border border-neutral-800 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-sky-500/50 resize-none" placeholder="Brief description..." />
                                </div>
                            </div>
                            <div className="flex gap-3 mt-6">
                                <button onClick={() => setShowAddModal(false)} className="flex-1 py-2 rounded-lg text-xs font-semibold text-neutral-400 bg-neutral-800/50 hover:bg-neutral-800 transition-colors">Cancel</button>
                                <button onClick={handleAddComponent} className="flex-1 py-2 rounded-lg text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 transition-colors">Add Component</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
