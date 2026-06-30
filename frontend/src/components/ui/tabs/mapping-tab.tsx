"use client";

import {
    Search, X, SlidersHorizontal, Plus, Crosshair,
    LayoutGrid, Maximize2, Trash2, RefreshCw, Network
} from "lucide-react";
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import dagre from "dagre";

// ─── RAG endpoint (same as v0-ai-chat.tsx) ────────────────────────────────────
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.yantraa.tech";

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
    quantity?: number;
    partNumber?: string;
    aliases?: string[];
    assembly_parent?: string;
    assembly_depth?: number;
    relation_types?: Record<string, string>;
    confidence?: number;
    subcategory?: string;
    canonical_id?: string;
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
    quantity?: number;
    partNumber?: string;
    canonical_id?: string;
    aliases?: string[];
    subcategory?: string;
    assembly_parent?: string;
    assembly_depth?: number;
    confidence?: number;
}

interface Connection {
    id: string;
    fromId: string;
    toId: string;
    label: string;
    relation_type?: string;
    confidence?: number;
    evidence_sources?: string[];
    isUserEdited: boolean;
}

// ─── Category config ──────────────────────────────────────────────────────────

const CATEGORY_COLOR: Record<ComponentCategory, string> = {
    mechanical: "#94a3b8",
    actuator: "#f97316",
    controller: "#a855f7",
    sensor: "#06b6d4",
    power: "#eab308",
    electronic: "#4ade80",
};

export const WIRE_COLORS: Record<string, string> = {
    // Basic types
    power: '#ef4444',
    ground: '#10b981',
    signal: '#eab308',
    data: '#a855f7',
    drive: '#f97316',
    pwm: '#3b82f6',
    can: '#14b8a6',
    linkage: '#94a3b8',
    
    // 16 Typed relations
    mounted_to: '#94a3b8',
    bolted_to: '#64748b',
    welded_to: '#78716c',
    contains: '#6366f1',
    houses: '#8b5cf6',
    supports: '#a78bfa',
    drives: '#f97316',
    transmits_torque_to: '#fb923c',
    rotates_about: '#fbbf24',
    slides_on: '#34d399',
    limits_motion_of: '#2dd4bf',
    electrically_connected: '#60a5fa',
    pneumatically_connected: '#38bdf8',
    hydraulically_connected: '#0ea5e9',
    senses: '#06b6d4',
    controls: '#a855f7',
    generic_connection: '#60a5fa',
    
    default: '#60a5fa'
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

// ─── Fuzzy Matcher ────────────────────────────────────────────────────────────

function fuzzyMatch(a: string, b: string): boolean {
    const normalize = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
    const na = normalize(a);
    const nb = normalize(b);
    if (na.includes(nb) || nb.includes(na)) return true;
    
    // Split by non-alphanumeric, filter out purely empty strings
    const wordsA = a.toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 1);
    const wordsB = b.toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 1);
    const intersection = wordsA.filter(w => wordsB.includes(w));
    
    // More robust keyword matching (handles IMU, DOF, etc.)
    if (wordsA.length > 0 && intersection.length / wordsA.length >= 0.6) return true;
    if (wordsB.length > 0 && intersection.length / wordsB.length >= 0.6) return true;
    
    return false;
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
        
        // Remove trailing commas before closing brackets/braces (common LLM mistake)
        const jsonStr = cleaned.slice(start, end + 1).replace(/,\s*([\]}])/g, '$1');
        
        const arr = JSON.parse(jsonStr);
        if (!Array.isArray(arr)) return null;
        const validItems = arr.filter((item: any) => {
            const name = String(item.name ?? "").toLowerCase();
            if (/firmware|software|sketch|code/.test(name)) return false;
            return true;
        });

        return validItems.map((item: Record<string, unknown>) => {
            let name = String(item.name ?? "Unknown");
            // Strip leading quantities like "17x ", "2x ", "4 x "
            name = name.replace(/^\d+\s*[xX]\s*/, "");
            
            if (name.includes("30-cell") || name.includes("30-Cell")) {
                name = name.replace(/30-[cC]ell/, "3-Cell");
            }
            
            let inferredCategory = VALID_CATEGORIES.includes(item.category as ComponentCategory)
                ? (item.category as ComponentCategory)
                : inferCategory(name);

            // Force override AI mistakes on categorization
            if (/battery|power supply|lipo/i.test(name)) inferredCategory = "power";
            if (/servo|motor|actuator/i.test(name)) inferredCategory = "actuator";
            if (/shield|driver|arduino|raspberry/i.test(name)) inferredCategory = "controller";
            
            return {
                name,
                category: inferredCategory,
                description: String(item.description ?? ""),
                quantity: Number(item.quantity) || 1,
                partNumber: item.partNumber ? String(item.partNumber) : undefined,
                connects_to: Array.isArray(item.connects_to)
                    ? item.connects_to.map(String)
                    : [],
                aliases: Array.isArray(item.aliases) ? item.aliases.map(String) : [],
                subcategory: item.subcategory ? String(item.subcategory) : undefined,
                canonical_id: item.canonical_id ? String(item.canonical_id) : undefined,
                relation_types: item.relation_types && typeof item.relation_types === 'object' ? item.relation_types as Record<string, string> : undefined,
                assembly_parent: item.assembly_parent && item.assembly_parent !== "null" ? String(item.assembly_parent) : undefined,
                assembly_depth: Number(item.assembly_depth) || 0,
                confidence: Number(item.confidence) || undefined
            };
        });
    } catch (e) {
        // Log just the text to avoid a red stack trace in the browser console,
        // since we have fallback mechanisms in place.
        console.warn(`[ComponentData] AI returned invalid JSON. Falling back to keyword extraction. Raw payload was: \n${text}`);
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
    aiResponseFallback: string,
    existingNodes: ComponentNode[]
): Promise<RawComponent[]> {
    const existingStr = existingNodes.length > 0 
        ? existingNodes.map(n => `- ${n.label} (${n.category})`).join("\n") 
        : "None";

    const prompt1 = `You are a Senior Mechanical Systems Engineer, CAD Intelligence Architect, and Robotics Assembly Analyst.
Generate an engineering-grade BOM and component mapping for the topic: '${topic}'.
DO NOT rely solely on filenames. Generate canonical IDs (COMP_XXXXXX) and subcategories.
Do not duplicate the following existing nodes: ${existingStr}

Return ONLY a JSON array with objects matching exactly this schema:
{
  "name": "Component Name",
  "canonical_id": "COMP_XXXXXX",
  "aliases": ["Alias1", "Alias2"],
  "category": "actuator" | "sensor" | "controller" | "mechanical" | "power" | "electronic",
  "subcategory": "Motor" | "Bearing" | "Fastener" | "PCB" | "Housing" | "Sensor" | "Bracket" | "Connector",
  "description": "Technical description",
  "connects_to": ["TargetName"],
  "relation_types": {"TargetName": "drives" | "mounted_to" | "electrically_connected"},
  "assembly_parent": "ParentNameOrNull",
  "assembly_depth": 0,
  "confidence": 0.95
}`;

    try {
        const res1 = await fetch(`${API_BASE}/api/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
            body: JSON.stringify({ query: prompt1 }),
        });
        if (res1.ok) {
            const data1 = await res1.json();
            const parsed1 = parseRAGJson(String(data1.response ?? ""));
            if (parsed1 && parsed1.length > 0) return parsed1;
        }
    } catch { /* fall through */ }

    // Second attempt — stricter fallback
    const prompt2 =
        `Output only raw JSON, no prose. Array of objects with fields: name, category, subcategory, description, connects_to, relation_types (map of target to relation type), canonical_id, aliases. ` +
        `Topic: '${topic}'`;
    try {
        const res2 = await fetch(`${API_BASE}/api/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
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

function applyLayout(rawNodes: Omit<ComponentNode, "x" | "y">[], connections: Connection[] = []): ComponentNode[] {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    
    // Top to Bottom flow
    dagreGraph.setGraph({ rankdir: 'TB', ranksep: 120, nodesep: 150 });

    const connectedIds = new Set<string>();
    connections.forEach(c => {
        connectedIds.add(c.fromId);
        connectedIds.add(c.toId);
    });

    // Add nodes to dagre (only connected ones)
    rawNodes.forEach(n => {
        if (connectedIds.has(n.id)) {
            dagreGraph.setNode(n.id, { width: NODE_W, height: NODE_H });
        }
    });

    // Enforce hierarchy by forcing edges to go from lower rank to higher rank
    connections.forEach(e => {
        const fromNode = rawNodes.find(n => n.id === e.fromId);
        const toNode = rawNodes.find(n => n.id === e.toId);
        if (!fromNode || !toNode) return;
        
        const r1 = CATEGORY_ORDER.indexOf(fromNode.category);
        const r2 = CATEGORY_ORDER.indexOf(toNode.category);
        
        if (r1 <= r2) {
            dagreGraph.setEdge(e.fromId, e.toId);
        } else {
            // Reverse edge direction for dagre layout calculation so it respects the hierarchy
            dagreGraph.setEdge(e.toId, e.fromId);
        }
    });

    dagre.layout(dagreGraph);

    const result: ComponentNode[] = [];
    let unconnectedY = 80;
    
    rawNodes.forEach(n => {
        if (connectedIds.has(n.id)) {
            const nodeWithPosition = dagreGraph.node(n.id);
            result.push({
                ...(n as ComponentNode),
                x: nodeWithPosition.x - NODE_W / 2 + 100, // Shift slightly right
                y: nodeWithPosition.y - NODE_H / 2 + 80,
            });
        } else {
            // Float disconnected islands far to the right
            result.push({
                ...(n as ComponentNode),
                x: VIRTUAL_W + 100,
                y: unconnectedY,
            });
            unconnectedY += 150;
        }
    });

    return result;
}

// ─── Connection generator ─────────────────────────────────────────────────────

async function generateConnectionsAPI(
    nodes: ComponentNode[],
    raw: RawComponent[]
): Promise<{ connections: Connection[], updatedNodes: ComponentNode[] }> {
    try {
        // We must map nodes back to RawComponents to send to the backend
        const rawPayload = raw.map(r => {
            const n = nodes.find(node => fuzzyMatch(node.label, r.name));
            return {
                id: n ? n.id : `rag-${Date.now()}-${Math.random().toString(36).substring(7)}`,
                ...r,
                category: n ? n.category : r.category
            };
        });

        const res = await fetch(`${API_BASE}/api/mapping/build-graph`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ components: rawPayload })
        });
        
        if (!res.ok) throw new Error("Graph API failed");
        
        const data = await res.json();
        const apiConns = data.connections || [];
        const enrichedComponents = data.components || [];
        
        // Return updated nodes with canonical info and confidence if provided by backend in the future
        const newNodes = nodes.map(n => {
            const enriched = enrichedComponents.find((ec: any) => ec.id === n.id || ec.name === n.label);
            if (enriched) {
                return {
                    ...n,
                    canonical_id: enriched.canonical_id,
                    subcategory: enriched.subcategory,
                    confidence: enriched.confidence,
                    aliases: enriched.aliases,
                    assembly_parent: enriched.assembly_parent,
                    assembly_depth: enriched.assembly_depth
                };
            }
            return n;
        });

        return { connections: apiConns, updatedNodes: newNodes };
    } catch (e) {
        console.error("API mapping failed, returning empty connections", e);
        return { connections: [], updatedNodes: nodes };
    }
}



// ─── Seed data ────────────────────────────────────────────────────────────────

const SEED_RAW: RawComponent[] = [];

const SEED_BASE_NODES = SEED_RAW.map((r, i) => ({
    id: `seed-${i}`,
    label: r.name,
    category: r.category,
    description: r.description,
    width: NODE_W,
    height: NODE_H,
    quantity: r.quantity,
    partNumber: r.partNumber,
}));

const SEED_CONNECTIONS: Connection[] = [];
const SEED_NODES: ComponentNode[] = applyLayout(SEED_BASE_NODES as ComponentNode[], SEED_CONNECTIONS);

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
    isChatLoading?: boolean;
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
    
    // Generate dynamic mock pins based on component category
    let pins: string[] = [];
    switch (data.category) {
        case "controller":
            pins = ["5V", "GND", "TX", "RX", "PWM"];
            break;
        case "sensor":
            pins = ["5V", "GND", "SDA", "SCL"];
            break;
        case "actuator":
            pins = ["PWM", "5V", "GND"];
            break;
        case "power":
            pins = ["12V", "5V", "GND"];
            break;
        case "electronic":
            pins = ["VIN", "GND", "SIG"];
            break;
        case "mechanical":
            pins = [];
            break;
        default:
            pins = ["IO", "GND"];
    }

    return (
        <div style={{
            background: "#13161c",
            border: `1px solid ${color}50`,
            borderRadius: "8px",
            padding: "10px",
            minWidth: "160px",
            color: "white",
            fontSize: "12px",
            boxShadow: "0 4px 6px rgba(0,0,0,0.3)"
        }}>
            {/* We map generic target handles on the left so wires can snap anywhere */}
            <Handle id="left" type="target" position={Position.Left} style={{ background: color, width: 8, height: 8 }} />
            
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                <div style={{ width: 20, height: 20, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <CategoryIcon category={data.category} size={14} />
                </div>
                <strong 
                    style={{ 
                        whiteSpace: "nowrap", 
                        overflow: "hidden", 
                        textOverflow: "ellipsis", 
                        maxWidth: "180px", 
                        display: "block" 
                    }} 
                    title={data.label}
                >
                    {data.label}
                </strong>
            </div>
            
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: "4px" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                    <div style={{ fontSize: "9px", color: color, textTransform: "uppercase", letterSpacing: "1px" }}>
                        {data.category}
                    </div>
                    {data.subcategory && (
                        <div style={{ fontSize: "8px", color: "#8b949e" }}>
                            {data.subcategory}
                        </div>
                    )}
                </div>
                
                {/* Confidence Badge */}
                {data.confidence !== undefined && (
                    <div style={{ 
                        fontSize: "9px", 
                        padding: "2px 4px", 
                        borderRadius: "4px", 
                        background: data.confidence >= 0.95 ? "#064e3b" : data.confidence >= 0.80 ? "#713f12" : "#7f1d1d",
                        color: data.confidence >= 0.95 ? "#34d399" : data.confidence >= 0.80 ? "#fbbf24" : "#f87171",
                        border: `1px solid ${data.confidence >= 0.95 ? "#059669" : data.confidence >= 0.80 ? "#d97706" : "#dc2626"}`
                    }}>
                        {(data.confidence * 100).toFixed(0)}%
                    </div>
                )}
                
                {/* Pins render */}
                {pins.length > 0 && (
                    <div style={{ display: "flex", gap: "4px" }}>
                        {pins.map(pin => (
                            <div key={pin} style={{
                                fontSize: "8px",
                                background: "#1e2430",
                                color: "#8b949e",
                                padding: "2px 4px",
                                borderRadius: "3px",
                                border: "1px solid #30363d",
                                fontFamily: "monospace"
                            }}>
                                {pin}
                            </div>
                        ))}
                    </div>
                )}
            </div>
            
            {/* Generic source handles on the right */}
            <Handle id="right" type="source" position={Position.Right} style={{ background: color, width: 8, height: 8 }} />
        </div>
    );
};

const nodeTypes = { customComponent: CustomComponentNode };

export function MappingTab({ aiResponse = "", currentQuery = "", designData, isChatLoading = false }: MappingTabProps) {
    const [activeView, setActiveView] = useState<"matrix" | "canvas" | "bom">("matrix");
    
    useEffect(() => {
        console.log(`[MappingTab] Successfully mounted/loaded with activeView: ${activeView}`);
    }, []);

    const [nodes, setNodes] = useState<ComponentNode[]>(SEED_NODES);
    const [rawComponents, setRawComponents] = useState<RawComponent[]>(SEED_RAW);
    const [connections, setConnections] = useState<Connection[]>(SEED_CONNECTIONS);
    const [sidebarTab, setSidebarTab] = useState<"library" | "bom" | "validation">("library");
    const hasSubsystemsError = designData && (!designData.subsystems || designData.subsystems.length === 0);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedId, setSelectedId] = useState<string | null>(null);

    const [rfNodes, setRfNodes] = useState<Node[]>([]);
    
    useEffect(() => {
        setRfNodes(nodes.map((n, i) => ({
            id: n.id,
            type: 'customComponent',
            position: { x: n.x ?? (i * 200 % 800), y: n.y ?? (Math.floor(i * 200 / 800) * 150) },
            data: { 
                label: n.label, 
                category: n.category, 
                description: n.description,
                subcategory: n.subcategory,
                confidence: n.confidence 
            },
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
    
    const [confidenceThreshold, setConfidenceThreshold] = useState(0.80);

    const lastQueryRef = useRef<string>("");
    const rfEdges: Edge[] = useMemo(() => {
        const edgeGroups = new Map<string, Connection[]>();
        
        const filteredConnections = connections.filter(c => c.confidence === undefined || c.confidence >= confidenceThreshold);
        
        filteredConnections.forEach(c => {
            const key = c.fromId < c.toId ? `${c.fromId}-${c.toId}` : `${c.toId}-${c.fromId}`;
            if (!edgeGroups.has(key)) edgeGroups.set(key, []);
            edgeGroups.get(key)!.push(c);
        });

        return filteredConnections.map(c => {
            const edgeColor = WIRE_COLORS[c.relation_type?.toLowerCase() || c.label?.toLowerCase()] || WIRE_COLORS.default;
            
            const key = c.fromId < c.toId ? `${c.fromId}-${c.toId}` : `${c.toId}-${c.fromId}`;
            const group = edgeGroups.get(key)!;
            const idx = group.indexOf(c);
            
            // Cycle through edge types so parallel edges geometrically separate, fixing overlapping labels
            const types = ['smoothstep', 'default', 'straight', 'step'];
            let edgeType = types[idx % types.length];
            
            // Hardcode specific overrides if they are the ONLY wire, for aesthetics
            if (group.length === 1) {
                if (c.label === 'ground') edgeType = 'default';
                if (c.label === 'power') edgeType = 'smoothstep';
            }

            const isLowConfidence = c.confidence !== undefined && c.confidence < 0.90;

            return {
                id: c.id,
                source: c.fromId,
                target: c.toId,
                label: c.relation_type || c.label,
                type: edgeType,
                animated: isLowConfidence,
                style: { 
                    stroke: edgeColor, 
                    strokeWidth: 1.5,
                    strokeDasharray: isLowConfidence ? '5,5' : undefined,
                    opacity: isLowConfidence ? 0.6 : 1
                },
                labelStyle: { fill: '#a3a3a3', fontWeight: 600, fontSize: 11, className: 'edge-label-text' },
                labelBgStyle: { fill: '#13161c', className: 'edge-label-bg' },
                markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor },
                className: 'custom-edge-hover'
            };
        });
    }, [connections, confidenceThreshold]);


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
        let fetchedRaw: RawComponent[] = [];
        
        // Fast-path optimization: use designData natively if available to avoid 10s LLM delay
        if (designData && designData.subsystems && designData.subsystems.length > 0) {
            console.log("[MappingTab] Leveraging designData for instant mapping!");
            const compMap = new Map<string, string>();
            designData.subsystems.forEach((sub: any) => {
                sub.components?.forEach((c: any) => compMap.set(c.id, c.name));
            });
            
            designData.subsystems.forEach((sub: any) => {
                sub.components?.forEach((c: any) => {
                    const bomItem = designData.bom?.find((b: any) => fuzzyMatch(b.name, c.name));
                    const connectsToNames = designData.connections
                        ?.filter((conn: any) => conn.from === c.id || conn.from_id === c.id || conn.id_from === c.id)
                        .map((conn: any) => {
                            const toId = conn.to || conn.to_id || conn.id_to;
                            return compMap.get(toId);
                        })
                        .filter(Boolean) || [];
                        
                    fetchedRaw.push({
                        name: c.name,
                        category: inferCategory(c.name),
                        description: bomItem?.description || c.role || "",
                        quantity: bomItem?.qty || 1,
                        connects_to: connectsToNames
                    });
                });
            });
            // Brief artificial delay just for UX smoothness
            await new Promise(resolve => setTimeout(resolve, 300));
        } else {
            fetchedRaw = await fetchComponentsFromRAG(q, aiResponse, nodes);
        }
        
        let updatedRaw = [...rawComponents];
        let updatedNodes = [...nodes];
        
        for (const newRaw of fetchedRaw) {
            const existingRawIdx = updatedRaw.findIndex(r => fuzzyMatch(r.name, newRaw.name));
            if (existingRawIdx !== -1) {
                updatedRaw[existingRawIdx] = {
                    ...updatedRaw[existingRawIdx],
                    // Use Math.max since designData is cumulative, we don't want to exponentially multiply qty
                    quantity: Math.max(updatedRaw[existingRawIdx].quantity || 1, newRaw.quantity || 1),
                    connects_to: Array.from(new Set([...updatedRaw[existingRawIdx].connects_to, ...newRaw.connects_to]))
                };
                
                const nodeIdx = updatedNodes.findIndex(n => fuzzyMatch(n.label, newRaw.name));
                if (nodeIdx !== -1) {
                    updatedNodes[nodeIdx] = {
                        ...updatedNodes[nodeIdx],
                        quantity: updatedRaw[existingRawIdx].quantity
                    };
                }
            } else {
                newRaw.quantity = newRaw.quantity || 1;
                // Double check to strip out the prefix one more time
                newRaw.name = newRaw.name.replace(/^\d+\s*[xX]\s*/, "");
                updatedRaw.push(newRaw);
                const newNode: ComponentNode = {
                    id: `rag-${Date.now()}-${Math.random().toString(36).substring(7)}`,
                    label: newRaw.name,
                    category: newRaw.category,
                    description: newRaw.description,
                    partNumber: newRaw.partNumber,
                    quantity: newRaw.quantity,
                    x: 0, y: 0, width: NODE_W, height: NODE_H
                };
                updatedNodes.push(newNode);
            }
        }
        setRawComponents(updatedRaw);
        
        const { connections: newConnections, updatedNodes: nodesFromAPI } = await generateConnectionsAPI(updatedNodes, updatedRaw);
        setConnections(newConnections);
        const layoutedNodes = applyLayout(nodesFromAPI, newConnections);
        setNodes(layoutedNodes);
        
        setIsLoading(false);
    }, [aiResponse, rawComponents, nodes, designData]);

    // ONE-TIME DEDUP PASS (Runs on hot-reload to clean up dirty session data)
    useEffect(() => {
        let hasDupes = false;
        const testRaw = [...rawComponents];
        for(let i=0; i<testRaw.length; i++) {
            for(let j=i+1; j<testRaw.length; j++) {
                if (fuzzyMatch(testRaw[i].name, testRaw[j].name)) hasDupes = true;
            }
        }
        if (!hasDupes) return;

        setRawComponents(prevRaw => {
            let updatedRaw = [...prevRaw];
            for (let i = 0; i < updatedRaw.length; i++) {
                for (let j = i + 1; j < updatedRaw.length; j++) {
                    if (fuzzyMatch(updatedRaw[i].name, updatedRaw[j].name)) {
                        updatedRaw[i] = {
                            ...updatedRaw[i],
                            quantity: (updatedRaw[i].quantity || 1) + (updatedRaw[j].quantity || 1),
                            connects_to: Array.from(new Set([...updatedRaw[i].connects_to, ...updatedRaw[j].connects_to]))
                        };
                        updatedRaw.splice(j, 1);
                        j--;
                    }
                }
            }
            return updatedRaw;
        });

        setNodes(prevNodes => {
            let updatedNodes = [...prevNodes];
            for (let i = 0; i < updatedNodes.length; i++) {
                for (let j = i + 1; j < updatedNodes.length; j++) {
                    if (fuzzyMatch(updatedNodes[i].label, updatedNodes[j].label)) {
                        updatedNodes[i] = {
                            ...updatedNodes[i],
                            quantity: (updatedNodes[i].quantity || 1) + (updatedNodes[j].quantity || 1),
                        };
                        updatedNodes.splice(j, 1);
                        j--;
                    }
                }
            }
            return updatedNodes;
        });
    }, []); // Run exactly once

    const lastDesignRef = useRef<any>(null);

    useEffect(() => {
        // Trigger mapping update when designData finishes loading from the main API
        // This completely eliminates the race condition and duplicate network requests
        if (designData && designData !== lastDesignRef.current) {
            lastDesignRef.current = designData;
            lastQueryRef.current = currentQuery; // Sync query ref to prevent fallback trigger
            doFetch(currentQuery || "design");
        } else if (currentQuery && currentQuery !== lastQueryRef.current && !designData && !isChatLoading) {
            // Fallback for standalone query execution
            lastQueryRef.current = currentQuery;
            doFetch(currentQuery);
        }
    }, [designData, currentQuery, doFetch, isChatLoading]);

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
        setNodes(prev => applyLayout(prev, connections));
    }, [connections]);

    const handleAddComponent = useCallback(() => {
        if (!newName.trim()) return;
        const nameClean = newName.trim();
        
        const existingNodeIdx = nodes.findIndex(n => fuzzyMatch(n.label, nameClean));
        if (existingNodeIdx !== -1) {
            setNodes(prev => prev.map((n, i) => i === existingNodeIdx ? { ...n, quantity: (n.quantity || 1) + 1 } : n));
            setRawComponents(prev => prev.map(r => fuzzyMatch(r.name, nameClean) ? { ...r, quantity: (r.quantity || 1) + 1 } : r));
        } else {
            const newNode: ComponentNode = {
                id: `node-custom-${Date.now()}`,
                label: nameClean,
                category: newCat,
                description: newDesc.trim(),
                quantity: 1,
                x: 0, y: 0, width: NODE_W as any, height: NODE_H as any,
            };
            const newRaw: RawComponent = {
                name: nameClean,
                category: newCat,
                description: newDesc.trim(),
                connects_to: [],
                quantity: 1,
            };
            setNodes(prev => [...prev, newNode]);
            setRawComponents(prev => [...prev, newRaw]);
        }
        
        setNewName("");
        setNewCat("electronic");
        setNewDesc("");
        setShowAddModal(false);
    }, [newName, newCat, newDesc, nodes]);

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
    const groupedNodes = useMemo(() => {
        const groups: Partial<Record<ComponentCategory, ComponentNode[]>> = {};
        CATEGORY_ORDER.forEach(cat => { groups[cat] = []; });
        filteredNodes.forEach(n => {
            if (groups[n.category]) groups[n.category]!.push(n);
        });
        return groups;
    }, [filteredNodes]);

    const selectedNode = nodes.find(n => n.id === selectedId);
    const inputsToSelected = connections.filter(c => c.toId === selectedId);
    const outputsFromSelected = connections.filter(c => c.fromId === selectedId);

    const handleExportBOM = useCallback(() => {
        const rows = [["Category", "Name", "Part Number", "Quantity", "Description", "Connections"]];
        CATEGORY_ORDER.forEach(cat => {
            const group = groupedNodes[cat];
            if (!group || group.length === 0) return;
            group.forEach(n => {
                const conns = connections.filter(c => c.fromId === n.id).map(c => {
                    const t = nodes.find(x => x.id === c.toId);
                    return t ? t.label : c.toId;
                }).join(" | ");
                rows.push([
                    n.category,
                    `"${n.label.replace(/"/g, '""')}"`,
                    `"${(n.partNumber || "").replace(/"/g, '""')}"`,
                    String(n.quantity || 1),
                    `"${n.description.replace(/"/g, '""')}"`,
                    `"${conns.replace(/"/g, '""')}"`
                ]);
            });
        });
        const csv = rows.map(r => r.join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "robot-bom.csv";
        a.click();
        URL.revokeObjectURL(url);
    }, [nodes, connections, groupedNodes]);

    return (
        <div className="w-full h-full flex flex-col bg-[#0A0A0A] overflow-hidden text-[#888888] font-sans">
            
            {/* TOP TOOLBAR: View Toggle */}
            <div className="h-12 border-b border-[#2A2A2A] flex items-center justify-between px-6 bg-[#161616] shrink-0 z-30">
                <div className="flex gap-1 bg-[#1E1E1E] p-1 rounded-lg border border-[#2A2A2A]">
                    <button 
                        onClick={() => setActiveView("matrix")}
                        className={`px-4 py-1.5 rounded text-xs font-medium transition-all ${activeView === 'matrix' ? 'bg-[#252525] text-[#F0F0F0] shadow' : 'text-[#888888] hover:text-[#F0F0F0]'}`}
                    >
                        Matrix View
                    </button>
                    <button 
                        onClick={() => setActiveView("canvas")}
                        className={`px-4 py-1.5 rounded text-xs font-medium transition-all ${activeView === 'canvas' ? 'bg-[#252525] text-[#F0F0F0] shadow' : 'text-[#888888] hover:text-[#F0F0F0]'}`}
                    >
                        Canvas Wiring View
                    </button>
                    <button 
                        onClick={() => setActiveView("bom")}
                        className={`px-4 py-1.5 rounded text-xs font-medium transition-all ${activeView === 'bom' ? 'bg-[#252525] text-[#F0F0F0] shadow' : 'text-[#888888] hover:text-[#F0F0F0]'}`}
                    >
                        BOM View
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    {isLoading && <div className="text-xs text-[#888888] animate-pulse mr-4">Updating from AI...</div>}
                    
                    {/* Confidence Threshold Filter */}
                    <div className="flex items-center gap-2 mr-4 bg-[#1E1E1E] px-3 py-1 rounded-lg border border-[#2A2A2A]">
                        <span className="text-[10px] uppercase font-semibold text-[#888888] tracking-widest">Conf &ge; {(confidenceThreshold * 100).toFixed(0)}%</span>
                        <input 
                            type="range" 
                            min="0.50" 
                            max="0.99" 
                            step="0.05"
                            value={confidenceThreshold}
                            onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                            className="w-20 accent-sky-500 h-1 bg-[#2A2A2A] rounded-lg appearance-none cursor-pointer"
                        />
                    </div>
                    
                    {activeView === 'bom' && (
                        <button onClick={handleExportBOM} className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-[#F0F0F0] bg-[#1E1E1E] hover:bg-[#252525] rounded border border-[#2A2A2A] transition-colors">Export CSV</button>
                    )}
                    <button onClick={handleAutoLayout} className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-[#888888] bg-[#1E1E1E] hover:bg-[#252525] hover:text-[#F0F0F0] rounded border border-[#2A2A2A] transition-colors"><Network size={12} /> Auto Layout</button>
                    <button onClick={handleRefresh} className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-[#888888] bg-[#1E1E1E] hover:bg-[#252525] hover:text-[#F0F0F0] rounded border border-[#2A2A2A] transition-colors"><RefreshCw size={12} /> Refresh</button>
                    <button onClick={handleClear} className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-[#FF4444] bg-[#1E1E1E] hover:bg-[rgba(255,68,68,0.08)] rounded border border-[#2A2A2A] transition-colors"><Trash2 size={12} /> Clear</button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden relative">
                {/* 1. COMPONENT LIBRARY (Left Column) */}
                <div className="w-[320px] h-full bg-[#161616] border-r border-[#2A2A2A] flex flex-col shrink-0 z-20">
                    <div className="flex items-center justify-between p-4 pb-2 mt-2">
                        <h2 className="text-xs font-medium text-[#888888] tracking-widest uppercase">Component Library</h2>
                    </div>
                    <div className="px-4 py-3 flex gap-2">
                        <div className="flex-1 bg-[#1E1E1E] rounded-lg border border-[#2A2A2A] flex items-center px-3">
                            <Search className="w-4 h-4 text-[#555555] shrink-0" />
                            <input
                                type="text"
                                placeholder="Search library..."
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                className="w-full bg-transparent border-none text-xs text-[#F0F0F0] focus:outline-none focus:ring-0 px-2 py-2.5 placeholder:text-[#555555]"
                            />
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#1E1E1E] hover:bg-[#252525] border border-[#2A2A2A] text-[#888888] hover:text-[#F0F0F0] rounded-lg text-xs font-medium transition-colors mb-2"
                        >
                            + Add Custom Component
                        </button>
                        {filteredNodes.length === 0 ? (
                            <div className="text-[#555555] text-xs text-center mt-10">No components found.</div>
                        ) : (
                            filteredNodes.map(node => {
                                const color = CATEGORY_COLOR[node.category] || "#666";
                                return (
                                    <div key={`lib-${node.id}`} className="flex items-center justify-between bg-[#1E1E1E] rounded-lg p-3 border border-[#2A2A2A] hover:bg-[#252525] transition-colors">
                                        <div className="flex items-center gap-3">
                                            <div style={{ width: 28, height: 28, background: "rgba(255,255,255,0.03)", border: `1px solid ${color}40`, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                                <CategoryIcon category={node.category} size={14} />
                                            </div>
                                            <div>
                                                <div className="text-[#F0F0F0] text-xs font-medium truncate max-w-[140px]">{node.label}</div>
                                                <div className="text-[10px]" style={{ color }}>{node.category}</div>
                                            </div>
                                        </div>
                                        <button onClick={() => {
                                            setNodes(p => p.map(n => n.id === node.id ? { ...n, quantity: (n.quantity || 1) + 1 } : n));
                                            setRawComponents(p => p.map(r => r.name.toLowerCase() === node.label.toLowerCase() ? { ...r, quantity: (r.quantity || 1) + 1 } : r));
                                        }} className="text-[#555555] hover:text-[#F0F0F0] bg-[#252525] hover:bg-[#333333] p-1.5 rounded-md transition-colors">
                                            <Plus size={14} />
                                        </button>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>

                {/* 2. DYNAMIC MAIN VIEW (Middle Column) */}
                <div className="flex-1 h-full bg-[#0A0A0A] relative border-r border-[#2A2A2A] flex flex-col">
                    {isLoading ? (
                        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                            <div className="w-16 h-16 border-4 border-sky-500/20 border-t-sky-500 rounded-full animate-spin mb-6"></div>
                            <h2 className="text-xl font-bold text-white tracking-widest uppercase mb-2">Generating Component Mapping</h2>
                            <p className="text-neutral-500 text-sm max-w-md">Our AI is analyzing your prompt to generate the optimal mechanical and electronic components, and routing the wiring connections. Please wait...</p>
                        </div>
                    ) : activeView === "bom" ? (
                        <div className="flex-1 overflow-y-auto p-8 bg-[#0A0A0A]">
                            <div className="max-w-5xl mx-auto pb-10">
                                <div className="flex items-center justify-between mb-8">
                                    <h1 className="text-xl font-semibold text-[#F0F0F0] tracking-widest uppercase">Bill of Materials</h1>
                                </div>
                                {CATEGORY_ORDER.map(cat => {
                                    const group = groupedNodes[cat];
                                    if (!group || group.length === 0) return null;
                                    const catColor = CATEGORY_COLOR[cat];
                                    const totalQty = group.reduce((sum, n) => sum + (n.quantity || 1), 0);
                                    return (
                                        <div key={`bom-${cat}`} className="mb-10 bg-[#161616] rounded-xl border border-[#2A2A2A] overflow-hidden">
                                            <div className="px-5 py-4 border-b border-[#2A2A2A] bg-[#161616] flex items-center justify-between">
                                                <div className="text-xs font-bold uppercase tracking-[0.15em] flex items-center gap-3" style={{ color: catColor }}>
                                                    <CategoryIcon category={cat} size={14} /> {cat}
                                                </div>
                                                <div className="text-xs font-medium text-[#888888] bg-[#1E1E1E] px-3 py-1 rounded-full border border-[#2A2A2A]">
                                                    {group.length} unique component{group.length !== 1 && 's'}
                                                </div>
                                            </div>
                                            <div className="overflow-x-auto">
                                                <table className="w-full text-left border-collapse">
                                                    <thead>
                                                        <tr className="bg-[#161616] text-[10px] font-bold text-[#888888] uppercase tracking-widest">
                                                            <th className="px-6 py-3 border-b border-[#2A2A2A] w-1/4">Component Name</th>
                                                            <th className="px-6 py-3 border-b border-[#2A2A2A] w-32">Part Number</th>
                                                            <th className="px-6 py-3 border-b border-[#2A2A2A] w-24 text-center">Qty</th>
                                                            <th className="px-6 py-3 border-b border-[#2A2A2A]">Key Specs</th>
                                                            <th className="px-6 py-3 border-b border-[#2A2A2A] w-1/4">Connections To</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="text-xs text-[#F0F0F0]">
                                                        {group.map(node => {
                                                            const nodeOutputs = connections.filter(c => c.fromId === node.id);
                                                            return (
                                                                <tr key={`bom-row-${node.id}`} className="border-b border-[#1F1F1F] hover:bg-[#1E1E1E] transition-colors group">
                                                                    <td className="px-6 py-4 font-medium text-[#F0F0F0] tracking-wide">{node.label}</td>
                                                                    <td className="px-6 py-4 text-[#555555] font-mono text-[10px]">{node.partNumber || "N/A"}</td>
                                                                    <td className="px-6 py-4 text-center">
                                                                        <span className="font-bold text-[#F0F0F0] bg-[#252525] px-3 py-1 rounded text-[11px] border border-[#2A2A2A]">
                                                                            {node.quantity || 1}
                                                                        </span>
                                                                    </td>
                                                                    <td className="px-6 py-4 text-[#888888] max-w-xs leading-relaxed">{node.description}</td>
                                                                    <td className="px-6 py-4">
                                                                        <div className="flex flex-wrap gap-1.5">
                                                                            {nodeOutputs.length === 0 ? <span className="text-neutral-600 italic text-[11px]">None</span> : nodeOutputs.map(conn => {
                                                                                const targetNode = nodes.find(n => n.id === conn.toId);
                                                                                if (!targetNode) return null;
                                                                                return (
                                                                                    <span key={`bom-conn-${conn.id}`} className="px-2 py-1 bg-[#252525] border border-[#2A2A2A] rounded text-[10px] text-[#888888]">
                                                                                        {targetNode.label}
                                                                                    </span>
                                                                                );
                                                                            })}
                                                                        </div>
                                                                    </td>
                                                                </tr>
                                                            );
                                                        })}
                                                    </tbody>
                                                </table>
                                            </div>
                                            <div className="px-6 py-4 bg-[#161616] border-t border-[#2A2A2A] flex justify-between items-center text-xs">
                                                <span className="font-medium text-[#888888] uppercase tracking-widest">Total Category Items</span>
                                                <span className="font-bold text-[#F0F0F0] bg-[#1E1E1E] px-3 py-1 rounded border border-[#2A2A2A]">{totalQty}</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ) : activeView === "matrix" ? (
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
                                                        className={`flex items-stretch bg-[#161616] rounded-xl border transition-all cursor-pointer overflow-hidden ${isSelected ? 'border-[#444444] bg-[#1E1E1E]' : 'border-[#2A2A2A] hover:border-[#333333] hover:bg-[#1E1E1E]'}`}
                                                        style={{ minHeight: '64px' }}
                                                    >
                                                        <div className="w-1.5" style={{ background: catColor }} />
                                                        <div className="flex items-center gap-4 px-4 py-3 w-[300px] shrink-0 border-r border-[#2A2A2A]">
                                                            <div style={{ width: 36, height: 36, background: "rgba(255,255,255,0.02)", border: `1px solid ${catColor}30`, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                                                <CategoryIcon category={cat} size={20} />
                                                            </div>
                                                            <div className="min-w-0">
                                                                <div className="text-[#F0F0F0] text-[13px] font-medium truncate">{node.label}</div>
                                                                <div className="text-[#555555] text-[10px] uppercase tracking-wider mt-0.5">Qty: {node.quantity || 1}</div>
                                                            </div>
                                                        </div>
                                                        <div className="flex-1 px-5 py-3 flex items-center flex-wrap gap-2">
                                                            {nodeOutputs.length === 0 ? (
                                                                <span className="text-[#555555] text-xs italic">No outgoing connections</span>
                                                            ) : (
                                                                nodeOutputs.map(conn => {
                                                                    const targetNode = nodes.find(n => n.id === conn.toId);
                                                                    if (!targetNode) return null;
                                                                    return (
                                                                        <div 
                                                                            key={conn.id} 
                                                                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#252525] border border-[#2A2A2A] text-[#888888] hover:border-[#444444] hover:text-[#F0F0F0] transition-colors"
                                                                            onClick={(e) => { e.stopPropagation(); setSelectedId(targetNode.id); }}
                                                                        >
                                                                            <span className="text-[#555555]">⮑</span> {targetNode.label}
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
                            <div style={{ position: 'absolute', inset: 0 }}>
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
                                    onNodeClick={(_: any, node: any) => setSelectedId(node.id)}
                                    nodeTypes={nodeTypes}
                                    fitView
                                    onlyRenderVisibleElements={true}
                                    proOptions={{ hideAttribution: true }}
                                >
                                    <Background color="#1E1E1E" gap={24} size={1} />
                                    <Controls style={{ backgroundColor: '#161616', border: '1px solid #2A2A2A' }} />
                                </ReactFlow>
                            </div>
                        </div>
                    )}
                </div>

                {/* 3. INSPECTOR (Right Column) */}
                <div className="w-[340px] h-full bg-[#161616] flex flex-col shrink-0 z-20">
                    <div className="flex items-center justify-between p-4 border-b border-[#2A2A2A] bg-[#161616]">
                        <h2 className="text-xs font-medium text-[#888888] tracking-widest uppercase">Inspector</h2>
                    </div>
                    
                    {selectedNode ? (
                        <div className="flex-1 overflow-y-auto">
                            {/* Header Details */}
                            <div className="p-5 border-b border-[#2A2A2A]">
                                <div className="flex items-center gap-3 mb-4">
                                    <div style={{ width: 48, height: 48, background: "rgba(255,255,255,0.03)", border: `1px solid ${CATEGORY_COLOR[selectedNode.category]}40`, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                        <CategoryIcon category={selectedNode.category} size={24} />
                                    </div>
                                    <div>
                                        <h3 className="text-[#F0F0F0] text-sm font-medium leading-tight">{selectedNode.label}</h3>
                                        <span className="inline-block mt-1 text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded" style={{ background: `${CATEGORY_COLOR[selectedNode.category]}20`, color: CATEGORY_COLOR[selectedNode.category] }}>
                                            {selectedNode.category}
                                        </span>
                                    </div>
                                </div>
                                <div className="text-xs text-[#888888] leading-relaxed mb-4">
                                    {selectedNode.description || "No description provided for this component."}
                                </div>
                                <button 
                                    onClick={() => {
                                        setNodes(p => p.filter(n => n.id !== selectedId));
                                        setConnections(p => p.filter(c => c.fromId !== selectedId && c.toId !== selectedId));
                                        setSelectedId(null);
                                    }}
                                    className="w-full py-2 bg-[rgba(255,68,68,0.06)] hover:bg-[rgba(255,68,68,0.12)] text-[#FF4444] text-xs font-medium rounded border border-[rgba(255,68,68,0.15)] transition-colors"
                                >
                                    Delete Component
                                </button>
                            </div>

                            {/* Connection Manager */}
                            <div className="p-5">
                                <h4 className="text-[11px] font-medium text-[#888888] uppercase tracking-widest mb-4">Connection Manager</h4>
                                
                                <div className="mb-6">
                                    <div className="text-xs font-medium text-[#F0F0F0] mb-2 flex items-center gap-2"><span className="text-emerald-500">▼</span> Inputs To This</div>
                                    {inputsToSelected.length === 0 ? (
                                        <div className="text-xs text-[#555555] bg-[#1E1E1E] p-3 rounded border border-[#2A2A2A]">None</div>
                                    ) : (
                                        <div className="flex flex-col gap-2">
                                            {inputsToSelected.map(conn => {
                                                const fromNode = nodes.find(n => n.id === conn.fromId);
                                                const labelColor = WIRE_COLORS[conn.label?.toLowerCase()] || WIRE_COLORS.default;
                                                return (
                                                    <div key={conn.id} className="flex items-center justify-between bg-[#1E1E1E] p-2.5 rounded border border-[#2A2A2A]">
                                                        <div className="text-xs text-[#888888] truncate pr-2 flex items-center">
                                                            From: <span className="font-medium text-[#F0F0F0] ml-1">{fromNode?.label || "Unknown"}</span>
                                                            <span className="ml-2 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded" style={{color: labelColor, border: `1px solid ${labelColor}40`, background: `${labelColor}15`}}>{conn.label}</span>
                                                        </div>
                                                        <button onClick={() => setConnections(p => p.filter(c => c.id !== conn.id))} className="text-[#555555] hover:text-[#FF4444] transition-colors"><Trash2 size={12} /></button>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>

                                <div className="mb-6">
                                    <div className="text-xs font-medium text-[#F0F0F0] mb-2 flex items-center gap-2"><span className="text-sky-500">▲</span> Outputs From This</div>
                                    {outputsFromSelected.length === 0 ? (
                                        <div className="text-xs text-[#555555] bg-[#1E1E1E] p-3 rounded border border-[#2A2A2A]">None</div>
                                    ) : (
                                        <div className="flex flex-col gap-2">
                                            {outputsFromSelected.map(conn => {
                                                const toNode = nodes.find(n => n.id === conn.toId);
                                                const labelColor = WIRE_COLORS[conn.label?.toLowerCase()] || WIRE_COLORS.default;
                                                return (
                                                    <div key={conn.id} className="flex items-center justify-between bg-[#1E1E1E] p-2.5 rounded border border-[#2A2A2A]">
                                                        <div className="text-xs text-[#888888] truncate pr-2 flex items-center">
                                                            To: <span className="font-medium text-[#F0F0F0] ml-1">{toNode?.label || "Unknown"}</span>
                                                            <span className="ml-2 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded" style={{color: labelColor, border: `1px solid ${labelColor}40`, background: `${labelColor}15`}}>{conn.label}</span>
                                                        </div>
                                                        <button onClick={() => setConnections(p => p.filter(c => c.id !== conn.id))} className="text-[#555555] hover:text-[#FF4444] transition-colors"><Trash2 size={12} /></button>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>

                                {/* Add Connection */}
                                <div className="mt-8 pt-6 border-t border-[#2A2A2A]">
                                    <h5 className="text-[10px] font-medium text-[#888888] uppercase tracking-widest mb-3">Add New Connection</h5>
                                    <div className="flex flex-col gap-3">
                                        <select 
                                            value={inspectorConnTarget} 
                                            onChange={e => setInspectorConnTarget(e.target.value)}
                                            className="w-full bg-[#0A0A0A] border border-[#2A2A2A] rounded px-3 py-2 text-xs text-[#F0F0F0] outline-none focus:border-[#444444] transition-colors"
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
                                                className="flex-1 bg-[#0A0A0A] border border-[#2A2A2A] rounded px-3 py-2 text-xs text-[#F0F0F0] outline-none focus:border-[#444444] transition-colors placeholder:text-[#555555]"
                                            />
                                            <button 
                                                onClick={handleAddConnection}
                                                disabled={!inspectorConnTarget}
                                                className="px-4 bg-[#F0F0F0] hover:bg-white disabled:bg-[#252525] disabled:text-[#555555] text-black text-xs font-semibold rounded transition-colors"
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
                            <div className="w-16 h-16 rounded-full bg-[#1E1E1E] border border-[#2A2A2A] flex items-center justify-center mb-4 text-[#555555]">
                                <LayoutGrid size={24} />
                            </div>
                            <h3 className="text-sm font-medium text-[#888888] mb-2">No Component Selected</h3>
                            <p className="text-xs text-[#555555] leading-relaxed">
                                Select a component from the Assembly Matrix to view its details and manage connections.
                            </p>
                        </div>
                    )}
                </div>

                {/* Add Custom Component Modal */}
                {showAddModal && (
                    <div className="absolute inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center">
                        <div className="w-[360px] bg-[#161616] border border-[#2A2A2A] rounded-xl p-6 shadow-2xl">
                            <h3 className="text-sm font-medium text-[#F0F0F0] mb-4">Add Custom Component</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-[10px] font-medium text-[#888888] uppercase tracking-wider mb-1">Name</label>
                                    <input value={newName} onChange={e => setNewName(e.target.value)} className="w-full bg-[#0A0A0A] border border-[#2A2A2A] rounded-lg px-3 py-2 text-xs text-[#F0F0F0] outline-none focus:border-[#444444] transition-colors placeholder:text-[#555555]" placeholder="e.g. LIDAR Sensor" />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-medium text-[#888888] uppercase tracking-wider mb-1">Category</label>
                                    <select value={newCat} onChange={e => setNewCat(e.target.value as ComponentCategory)} className="w-full bg-[#0A0A0A] border border-[#2A2A2A] rounded-lg px-3 py-2 text-xs text-[#F0F0F0] outline-none focus:border-[#444444] transition-colors">
                                        {VALID_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-[10px] font-medium text-[#888888] uppercase tracking-wider mb-1">Description</label>
                                    <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={3} className="w-full bg-[#0A0A0A] border border-[#2A2A2A] rounded-lg px-3 py-2 text-xs text-[#F0F0F0] outline-none focus:border-[#444444] transition-colors resize-none placeholder:text-[#555555]" placeholder="Brief description..." />
                                </div>
                            </div>
                            <div className="flex gap-3 mt-6">
                                <button onClick={() => setShowAddModal(false)} className="flex-1 py-2 rounded-lg text-xs font-medium text-[#888888] bg-[#1E1E1E] hover:bg-[#252525] border border-[#2A2A2A] transition-colors">Cancel</button>
                                <button onClick={handleAddComponent} className="flex-1 py-2 rounded-lg text-xs font-semibold text-black bg-[#F0F0F0] hover:bg-white transition-colors">Add Component</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
