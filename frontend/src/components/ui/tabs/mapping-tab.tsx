"use client";

import {
    Search, X, SlidersHorizontal, Plus, Crosshair,
    LayoutGrid, Maximize2, Trash2, RefreshCw,
} from "lucide-react";
import { useState, useRef, useEffect, useCallback } from "react";

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
    width: 140;
    height: 88;
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

// ─── Component ────────────────────────────────────────────────────────────────

export function MappingTab({ aiResponse = "", currentQuery = "", designData }: MappingTabProps) {

    // ── State ──────────────────────────────────────────────────────────────────
    const [nodes, setNodes] = useState<ComponentNode[]>(SEED_NODES);
    const [rawComponents, setRawComponents] = useState<RawComponent[]>(SEED_RAW);
    const [connections, setConnections] = useState<Connection[]>(() =>
        generateConnections(SEED_NODES, SEED_RAW)
    );
    const [isLoading, setIsLoading] = useState(false);
    const [pan, setPan] = useState({ x: 40, y: 40 });
    const [zoom, setZoom] = useState(0.9);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [selectedConnId, setSelectedConnId] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [activeCategory, setActiveCategory] = useState<"all" | ComponentCategory>("all");
    const [hoveredConnId, setHoveredConnId] = useState<string | null>(null);
    const [tooltipConn, setTooltipConn] = useState<{ id: string; x: number; y: number } | null>(null);
    const [editingNode, setEditingNode] = useState<string | null>(null);
    const [editLabel, setEditLabel] = useState("");
    const [editDesc, setEditDesc] = useState("");
    const [editCat, setEditCat] = useState<ComponentCategory>("electronic");
    const [showAddModal, setShowAddModal] = useState(false);
    const [newName, setNewName] = useState("");
    const [newCat, setNewCat] = useState<ComponentCategory>("electronic");
    const [newDesc, setNewDesc] = useState("");
    // Port drag-to-connect
    const [draftLine, setDraftLine] = useState<{ fromId: string; side: "left" | "right"; toX: number; toY: number } | null>(null);
    const [hoveredPort, setHoveredPort] = useState<{ nodeId: string; side: "left" | "right" } | null>(null);

    // ── Refs ───────────────────────────────────────────────────────────────────
    const svgRef = useRef<SVGSVGElement>(null);
    const isPanning = useRef(false);
    const panStart = useRef({ x: 0, y: 0 });
    const panOrigin = useRef({ x: 0, y: 0 });
    const draggingNodeId = useRef<string | null>(null);
    const dragOffset = useRef({ x: 0, y: 0 });
    const didDrag = useRef(false);
    const animRef = useRef<number | null>(null);
    const isDraftingConn = useRef(false);
    const draftFromId = useRef<string | null>(null);
    const draftFromSide = useRef<"left" | "right">("right");
    const lastQueryRef = useRef("");

    // ── Fetch helpers ──────────────────────────────────────────────────────────
    const doFetch = useCallback(
        async (topic: string) => {
            if (!topic || topic === lastQueryRef.current) return;
            lastQueryRef.current = topic;
            setIsLoading(true);
            try {
                const raw = await fetchComponentsFromRAG(topic, aiResponse);
                if (raw.length === 0) return;
                setRawComponents(raw);
                const laid = applyLayout(
                    raw.map((r, i) => ({
                        id: `node-${i}-${Date.now()}`,
                        label: r.name,
                        category: r.category,
                        description: r.description,
                        width: NODE_W,
                        height: NODE_H,
                    }))
                );
                setNodes(laid);
                setConnections(generateConnections(laid, raw));
                setSelectedId(null);
                setSelectedConnId(null);
            } finally {
                setIsLoading(false);
            }
        },
        [aiResponse]
    );

    // ── useEffect: load shared designData when present ─────────────────────────
    useEffect(() => {
        if (!designData) return;
        
        const comps: RawComponent[] = [];
        const rawNodes: Omit<ComponentNode, "x" | "y">[] = [];
        
        if (designData.subsystems) {
            designData.subsystems.forEach((sub: any) => {
                if (sub.components) {
                    sub.components.forEach((comp: any) => {
                        const category = inferCategory(comp.name + " " + (comp.role || ""));
                        const description = `${comp.role || ""}. Voltage: ${comp.voltage || "N/A"}, Interface: ${comp.interface || "N/A"}`;
                        
                        comps.push({
                            name: comp.name,
                            category,
                            description,
                            connects_to: []
                        });
                        
                        rawNodes.push({
                            id: comp.id || `node-${comp.name.replace(/\s+/g, "_")}`,
                            label: comp.name,
                            category,
                            description,
                            width: NODE_W,
                            height: NODE_H
                        });
                    });
                }
            });
        }
        
        const laidNodes = applyLayout(rawNodes);
        
        const mappedConns: Connection[] = [];
        if (designData.connections) {
            designData.connections.forEach((conn: any, i: number) => {
                const fromId = conn.from;
                const toId = conn.to;
                const fromExists = laidNodes.some(n => n.id === fromId);
                const toExists = laidNodes.some(n => n.id === toId);
                
                if (fromExists && toExists) {
                    mappedConns.push({
                        id: `conn-design-${i}-${Date.now()}`,
                        fromId,
                        toId,
                        label: conn.protocol || conn.relation || "connects",
                        isUserEdited: false
                    });
                }
            });
        }
        
        setRawComponents(comps);
        setNodes(laidNodes);
        setConnections(mappedConns);
        setSelectedId(null);
        setSelectedConnId(null);
        setIsLoading(false);
    }, [designData]);

    // ── useEffect: re-fetch when query changes ─────────────────────────────────
    useEffect(() => {
        if (designData || !currentQuery) return;
        doFetch(currentQuery);
    }, [currentQuery, doFetch, designData]);

    // ── useEffect: fallback parse from aiResponse text when no query ───────────
    useEffect(() => {
        if (designData || !aiResponse || currentQuery) return;
        const raw = fallbackExtract(aiResponse);
        if (raw.length === 0) return;
        setRawComponents(raw);
        const laid = applyLayout(
            raw.map((r, i) => ({
                id: `node-ai-${i}-${Date.now()}`,
                label: r.name,
                category: r.category,
                description: r.description,
                width: NODE_W,
                height: NODE_H,
            }))
        );
        setNodes(laid);
        setConnections(generateConnections(laid, raw));
    }, [aiResponse, currentQuery, designData]);

    // ── SVG mouse: pan / drag / port-connect ──────────────────────────────────
    const svgToCanvas = useCallback(
        (clientX: number, clientY: number) => {
            const rect = svgRef.current!.getBoundingClientRect();
            return {
                x: (clientX - rect.left - pan.x) / zoom,
                y: (clientY - rect.top - pan.y) / zoom,
            };
        },
        [pan, zoom]
    );

    const handleSVGMouseDown = useCallback(
        (e: React.MouseEvent<SVGSVGElement>) => {
            if ((e.target as Element).closest("[data-node],[data-port]")) return;
            setSelectedId(null);
            setSelectedConnId(null);
            isPanning.current = true;
            panStart.current = { x: e.clientX, y: e.clientY };
            panOrigin.current = { ...pan };
            e.preventDefault();
        },
        [pan]
    );

    const handleSVGMouseMove = useCallback(
        (e: React.MouseEvent<SVGSVGElement>) => {
            if (isDraftingConn.current && draftFromId.current) {
                const pt = svgToCanvas(e.clientX, e.clientY);
                setDraftLine(prev =>
                    prev ? { ...prev, toX: pt.x, toY: pt.y } : null
                );
                return;
            }
            if (draggingNodeId.current) {
                didDrag.current = true;
                const pt = svgToCanvas(e.clientX, e.clientY);
                setNodes(prev =>
                    prev.map(n =>
                        n.id === draggingNodeId.current
                            ? { ...n, x: pt.x - dragOffset.current.x, y: pt.y - dragOffset.current.y }
                            : n
                    )
                );
                return;
            }
            if (isPanning.current) {
                setPan({
                    x: panOrigin.current.x + (e.clientX - panStart.current.x),
                    y: panOrigin.current.y + (e.clientY - panStart.current.y),
                });
            }
        },
        [svgToCanvas]
    );

    const handleSVGMouseUp = useCallback(() => {
        isPanning.current = false;
        draggingNodeId.current = null;
        isDraftingConn.current = false;
        draftFromId.current = null;
        setDraftLine(null);
        didDrag.current = false;
    }, []);

    const handleWheel = useCallback(
        (e: React.WheelEvent<SVGSVGElement>) => {
            e.preventDefault();
            const rect = svgRef.current!.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            const factor = e.deltaY > 0 ? 0.9 : 1.1;
            setZoom(prev => {
                const next = Math.min(3, Math.max(0.25, prev * factor));
                setPan(p => ({
                    x: mx - (mx - p.x) * (next / prev),
                    y: my - (my - p.y) * (next / prev),
                }));
                return next;
            });
        },
        []
    );

    // ── Node mouse handlers ────────────────────────────────────────────────────
    const handleNodeMouseDown = useCallback(
        (e: React.MouseEvent, nodeId: string) => {
            e.stopPropagation();
            didDrag.current = false;
            const node = nodes.find(n => n.id === nodeId)!;
            const pt = svgToCanvas(e.clientX, e.clientY);
            dragOffset.current = { x: pt.x - node.x, y: pt.y - node.y };
            draggingNodeId.current = nodeId;
        },
        [nodes, svgToCanvas]
    );

    const handleNodeMouseUp = useCallback(
        (nodeId: string) => {
            if (!didDrag.current) {
                setSelectedId(nodeId);
                setSelectedConnId(null);
            }
            draggingNodeId.current = null;
            didDrag.current = false;
        },
        []
    );

    const handleNodeDblClick = useCallback(
        (e: React.MouseEvent, nodeId: string) => {
            e.stopPropagation();
            const node = nodes.find(n => n.id === nodeId);
            if (!node) return;
            setEditingNode(nodeId);
            setEditLabel(node.label);
            setEditDesc(node.description);
            setEditCat(node.category);
        },
        [nodes]
    );

    // ── Port drag-to-connect ───────────────────────────────────────────────────
    const handlePortMouseDown = useCallback(
        (e: React.MouseEvent, nodeId: string, side: "left" | "right") => {
            e.stopPropagation();
            isDraftingConn.current = true;
            draftFromId.current = nodeId;
            draftFromSide.current = side;
            const node = nodes.find(n => n.id === nodeId)!;
            const startX = side === "right" ? node.x + node.width : node.x;
            const startY = node.y + node.height / 2;
            setDraftLine({ fromId: nodeId, side, toX: startX, toY: startY });
        },
        [nodes]
    );

    const handlePortMouseUp = useCallback(
        (e: React.MouseEvent, nodeId: string) => {
            e.stopPropagation();
            if (isDraftingConn.current && draftFromId.current && draftFromId.current !== nodeId) {
                const fromId = draftFromId.current;
                const toId = nodeId;
                const fromNode = nodes.find(n => n.id === fromId)!;
                const toNode = nodes.find(n => n.id === toId)!;
                const newConn: Connection = {
                    id: `conn-user-${Date.now()}`,
                    fromId,
                    toId,
                    label: "custom",
                    isUserEdited: true,
                };
                // Check dedup
                setConnections(prev => {
                    const dup = prev.some(c =>
                        (c.fromId === fromId && c.toId === toId) ||
                        (c.fromId === toId && c.toId === fromId)
                    );
                    return dup ? prev : [...prev, newConn];
                });
            }
            isDraftingConn.current = false;
            draftFromId.current = null;
            setDraftLine(null);
        },
        [nodes]
    );

    // ── Toolbar actions ────────────────────────────────────────────────────────
    const handleAutoLayout = useCallback(() => {
        const laid = applyLayout(nodes);
        const from: Record<string, { x: number; y: number }> = {};
        const to: Record<string, { x: number; y: number }> = {};
        nodes.forEach(n => { from[n.id] = { x: n.x, y: n.y }; });
        laid.forEach(n => { to[n.id] = { x: n.x, y: n.y }; });
        const start = performance.now();
        const dur = 400;
        function tick(now: number) {
            const t = Math.min((now - start) / dur, 1);
            const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
            setNodes(prev =>
                prev.map(n => ({
                    ...n,
                    x: (from[n.id]?.x ?? n.x) + ((to[n.id]?.x ?? n.x) - (from[n.id]?.x ?? n.x)) * ease,
                    y: (from[n.id]?.y ?? n.y) + ((to[n.id]?.y ?? n.y) - (from[n.id]?.y ?? n.y)) * ease,
                }))
            );
            if (t < 1) animRef.current = requestAnimationFrame(tick);
        }
        animRef.current = requestAnimationFrame(tick);
    }, [nodes]);

    const handleFitView = useCallback(() => {
        if (!nodes.length || !svgRef.current) return;
        const rect = svgRef.current.getBoundingClientRect();
        const minX = Math.min(...nodes.map(n => n.x));
        const minY = Math.min(...nodes.map(n => n.y));
        const maxX = Math.max(...nodes.map(n => n.x + n.width));
        const maxY = Math.max(...nodes.map(n => n.y + n.height));
        const w = maxX - minX;
        const h = maxY - minY;
        const newZoom = Math.min(3, Math.max(0.25, Math.min((rect.width - 80) / w, (rect.height - 80) / h)));
        setPan({
            x: (rect.width - w * newZoom) / 2 - minX * newZoom,
            y: (rect.height - h * newZoom) / 2 - minY * newZoom,
        });
        setZoom(newZoom);
    }, [nodes]);

    const handleClear = useCallback(() => {
        if (!window.confirm("Are you sure you want to clear the entire canvas? This cannot be undone.")) return;
        setNodes([]);
        setConnections([]);
        setSelectedId(null);
        setSelectedConnId(null);
        lastQueryRef.current = "";
    }, []);

    const handleRefresh = useCallback(() => {
        lastQueryRef.current = "";
        if (currentQuery) doFetch(currentQuery);
    }, [currentQuery, doFetch]);

    // ── Locate node (animate pan) ──────────────────────────────────────────────
    const locateNode = useCallback(
        (nodeId: string) => {
            const node = nodes.find(n => n.id === nodeId);
            if (!node || !svgRef.current) return;
            const rect = svgRef.current.getBoundingClientRect();
            const targetX = rect.width / 2 - (node.x + node.width / 2) * zoom;
            const targetY = rect.height / 2 - (node.y + node.height / 2) * zoom;
            const startPan = { ...pan };
            const startTime = performance.now();
            const dur = 300;
            function tick(now: number) {
                const t = Math.min((now - startTime) / dur, 1);
                const ease = 1 - Math.pow(1 - t, 3);
                setPan({
                    x: startPan.x + (targetX - startPan.x) * ease,
                    y: startPan.y + (targetY - startPan.y) * ease,
                });
                if (t < 1) animRef.current = requestAnimationFrame(tick);
            }
            animRef.current = requestAnimationFrame(tick);
            setSelectedId(nodeId);
        },
        [nodes, pan, zoom]
    );

    // ── Edit save ──────────────────────────────────────────────────────────────
    const saveEdit = useCallback(() => {
        setNodes(prev =>
            prev.map(n =>
                n.id === editingNode
                    ? { ...n, label: editLabel, description: editDesc, category: editCat }
                    : n
            )
        );
        setEditingNode(null);
    }, [editingNode, editLabel, editDesc, editCat]);

    // ── Add custom component ───────────────────────────────────────────────────
    const handleAddComponent = useCallback(() => {
        if (!newName.trim()) return;
        const rect = svgRef.current?.getBoundingClientRect();
        const cx = rect ? (rect.width / 2 - pan.x) / zoom : 300;
        const cy = rect ? (rect.height / 2 - pan.y) / zoom : 200;
        const newNode: ComponentNode = {
            id: `node-custom-${Date.now()}`,
            label: newName.trim(),
            category: newCat,
            description: newDesc.trim(),
            x: cx - NODE_W / 2,
            y: cy - NODE_H / 2,
            width: NODE_W,
            height: NODE_H,
        };
        const newRaw: RawComponent = {
            name: newName.trim(),
            category: newCat,
            description: newDesc.trim(),
            connects_to: [],
        };
        setNodes(prev => {
            const updated = [...prev, newNode];
            const updatedRaw = [...rawComponents, newRaw];
            const existingPairs = new Set(connections.map(c => `${c.fromId}→${c.toId}`));
            const extra = generateConnections(updated, updatedRaw).filter(
                c => !existingPairs.has(`${c.fromId}→${c.toId}`)
            );
            setConnections(prev2 => [...prev2, ...extra]);
            return updated;
        });
        setRawComponents(prev => [...prev, newRaw]);
        setNewName("");
        setNewCat("electronic");
        setNewDesc("");
        setShowAddModal(false);
    }, [newName, newCat, newDesc, pan, zoom, connections, rawComponents]);

    // ── Cleanup ────────────────────────────────────────────────────────────────
    useEffect(() => () => { if (animRef.current) cancelAnimationFrame(animRef.current); }, []);

    // ── Sidebar filter ─────────────────────────────────────────────────────────
    const TABS: { key: "all" | ComponentCategory; label: string }[] = [
        { key: "all", label: "All" },
        { key: "electronic", label: "Electronic" },
        { key: "mechanical", label: "Mechanical" },
        { key: "sensor", label: "Sensors" },
        { key: "actuator", label: "Actuators" },
    ];

    const filteredNodes = nodes.filter(n => {
        const matchCat = activeCategory === "all" || n.category === activeCategory;
        const matchSearch = n.label.toLowerCase().includes(searchQuery.toLowerCase());
        return matchCat && matchSearch;
    });

    // ── Bezier path ────────────────────────────────────────────────────────────
    function connPath(from: ComponentNode, to: ComponentNode): string {
        const x1 = from.x + from.width;
        const y1 = from.y + from.height / 2;
        const x2 = to.x;
        const y2 = to.y + to.height / 2;
        return `M ${x1} ${y1} C ${x1 + 80} ${y1}, ${x2 - 80} ${y2}, ${x2} ${y2}`;
    }

    function draftPath(): string | null {
        if (!draftLine) return null;
        const fromNode = nodes.find(n => n.id === draftLine.fromId);
        if (!fromNode) return null;
        const x1 = draftLine.side === "right" ? fromNode.x + fromNode.width : fromNode.x;
        const y1 = fromNode.y + fromNode.height / 2;
        const x2 = draftLine.toX;
        const y2 = draftLine.toY;
        return `M ${x1} ${y1} C ${x1 + 60} ${y1}, ${x2 - 60} ${y2}, ${x2} ${y2}`;
    }

    // ── Selected connection ────────────────────────────────────────────────────
    const selectedConn = connections.find(c => c.id === selectedConnId);

    // ─────────────────────────────────────────────────────────────────────────
    //  RENDER
    // ─────────────────────────────────────────────────────────────────────────
    return (
        <div className="w-full h-full flex bg-[#050505] overflow-hidden text-neutral-400 font-sans">

            {/* ── Main Area with Dotted Grid ── */}
            <div
                className="flex-1 h-full relative"
                style={{
                    backgroundImage: "radial-gradient(circle, rgba(139, 92, 246, 0.15) 1px, transparent 1px)",
                    backgroundSize: "24px 24px",
                }}
            >
                {/* ── Toolbar ── */}
                <div
                    className="bg-[#0B0E14]/80 backdrop-blur border border-neutral-800/50 rounded-lg px-3 py-2 flex items-center gap-3"
                    style={{ position: "absolute", top: 12, left: 12, zIndex: 10 }}
                >
                    {[
                        { icon: <LayoutGrid style={{ width: 13, height: 13 }} />, label: "Auto Layout", action: handleAutoLayout, color: "#a3a3a3" },
                        { icon: <Maximize2 style={{ width: 13, height: 13 }} />, label: "Fit View", action: handleFitView, color: "#a3a3a3" },
                        { icon: <Trash2 style={{ width: 13, height: 13 }} />, label: "Clear", action: handleClear, color: "#f87171" },
                        { icon: <RefreshCw style={{ width: 13, height: 13 }} />, label: "Refresh", action: handleRefresh, color: "#38bdf8" },
                    ].map((btn, bi) => (
                        <button
                            key={bi}
                            title={btn.label}
                            onClick={btn.action}
                            style={{
                                display: "flex", alignItems: "center", gap: 5,
                                background: "none", border: "none", color: btn.color,
                                cursor: "pointer", fontSize: 11, padding: "2px 4px", borderRadius: 5,
                            }}
                            onMouseEnter={e => (e.currentTarget.style.opacity = "0.7")}
                            onMouseLeave={e => (e.currentTarget.style.opacity = "1")}
                        >
                            {btn.icon}
                            {btn.label}
                        </button>
                    ))}
                </div>

                {/* ── SVG Canvas ── */}
                <svg
                    ref={svgRef}
                    width="100%"
                    height="100%"
                    style={{ display: "block", userSelect: "none", cursor: isPanning.current ? "grabbing" : "grab" }}
                    onMouseDown={handleSVGMouseDown}
                    onMouseMove={handleSVGMouseMove}
                    onMouseUp={handleSVGMouseUp}
                    onMouseLeave={handleSVGMouseUp}
                    onWheel={handleWheel}
                >
                    <defs>
                        {/* Per-category arrowhead markers */}
                        {(Object.entries(CATEGORY_COLOR) as [ComponentCategory, string][]).map(([cat, col]) => (
                            <marker
                                key={cat}
                                id={`arrow-${cat}`}
                                markerWidth="8"
                                markerHeight="8"
                                refX="6"
                                refY="4"
                                orient="auto"
                            >
                                <polygon points="0 0, 8 4, 0 8" fill={col} opacity="0.7" />
                            </marker>
                        ))}
                        <marker id="arrow-default" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                            <polygon points="0 0, 8 4, 0 8" fill="rgba(139,92,246,0.7)" />
                        </marker>
                        <marker id="arrow-hover" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
                            <polygon points="0 0, 8 4, 0 8" fill="rgba(139,92,246,1)" />
                        </marker>
                        {/* CSS animation for loading dots */}
                        <style>{`
                            @keyframes mtPulse {
                                0%,100%{opacity:0.2} 50%{opacity:1}
                            }
                            .mt-pulse-0{animation:mtPulse 1.2s ease-in-out infinite;}
                            .mt-pulse-1{animation:mtPulse 1.2s ease-in-out 0.2s infinite;}
                            .mt-pulse-2{animation:mtPulse 1.2s ease-in-out 0.4s infinite;}
                        `}</style>
                    </defs>

                    <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>

                        {/* ── Loading state ── */}
                        {isLoading && (
                            <g>
                                <circle className="mt-pulse-0" cx={550} cy={280} r={8} fill="#a78bfa" />
                                <circle className="mt-pulse-1" cx={580} cy={280} r={8} fill="#a78bfa" />
                                <circle className="mt-pulse-2" cx={610} cy={280} r={8} fill="#a78bfa" />
                                <text x={580} y={310} textAnchor="middle" fill="#6b7280" fontSize={13}>
                                    Fetching components...
                                </text>
                            </g>
                        )}

                        {/* ── Connections ── */}
                        {!isLoading && connections.map(conn => {
                            const from = nodes.find(n => n.id === conn.fromId);
                            const to = nodes.find(n => n.id === conn.toId);
                            if (!from || !to) return null;
                            const isHovered = hoveredConnId === conn.id;
                            const isSelected = selectedConnId === conn.id;
                            const d = connPath(from, to);
                            const catColor = CATEGORY_COLOR[from.category];
                            return (
                                <g key={conn.id}>
                                    {/* Invisible fat hit area */}
                                    <path
                                        d={d}
                                        stroke="transparent"
                                        strokeWidth={14}
                                        fill="none"
                                        style={{ cursor: "pointer" }}
                                        onMouseEnter={e => {
                                            setHoveredConnId(conn.id);
                                            const r = svgRef.current!.getBoundingClientRect();
                                            setTooltipConn({ id: conn.id, x: e.clientX - r.left, y: e.clientY - r.top });
                                        }}
                                        onMouseLeave={() => { setHoveredConnId(null); setTooltipConn(null); }}
                                        onClick={() => { setSelectedConnId(conn.id); setSelectedId(null); }}
                                    />
                                    <path
                                        d={d}
                                        stroke={
                                            isSelected
                                                ? catColor
                                                : isHovered
                                                ? `${catColor}dd`
                                                : `${catColor}50`
                                        }
                                        strokeWidth={isSelected ? 2.5 : isHovered ? 2 : 1.5}
                                        strokeDasharray={isSelected ? "6 3" : "none"}
                                        fill="none"
                                        markerEnd={`url(#arrow-${from.category})`}
                                        style={{ pointerEvents: "none", transition: "stroke 0.15s" }}
                                    />
                                </g>
                            );
                        })}

                        {/* ── Draft connection line ── */}
                        {draftLine && draftPath() && (
                            <path
                                d={draftPath()!}
                                stroke="rgba(255,255,255,0.6)"
                                strokeWidth={1.5}
                                strokeDasharray="5 4"
                                fill="none"
                                style={{ pointerEvents: "none" }}
                            />
                        )}

                        {/* ── Nodes ── */}
                        {!isLoading && nodes.map(node => {
                            const isSelected = selectedId === node.id;
                            const color = CATEGORY_COLOR[node.category];
                            const portR = 5;

                            return (
                                <g
                                    key={node.id}
                                    data-node="true"
                                    transform={`translate(${node.x},${node.y})`}
                                    onMouseDown={e => handleNodeMouseDown(e, node.id)}
                                    onMouseUp={() => handleNodeMouseUp(node.id)}
                                    onDoubleClick={e => handleNodeDblClick(e, node.id)}
                                    style={{ cursor: draggingNodeId.current === node.id ? "grabbing" : "grab" }}
                                >
                                    {/* Node card via foreignObject */}
                                    <foreignObject width={node.width} height={node.height}>
                                        <div
                                            style={{
                                                width: "100%",
                                                height: "100%",
                                                background: "#0f1219",
                                                border: `1.5px solid ${isSelected ? color : color + "55"}`,
                                                borderRadius: 10,
                                                padding: 10,
                                                boxSizing: "border-box",
                                                boxShadow: isSelected
                                                    ? `0 0 0 2px ${color}, 0 0 12px ${color}40`
                                                    : "0 2px 12px rgba(0,0,0,0.5)",
                                                display: "flex",
                                                flexDirection: "column",
                                                gap: 3,
                                                position: "relative",
                                                overflow: "hidden",
                                                userSelect: "none",
                                                transition: "box-shadow 0.15s, border-color 0.15s",
                                            }}
                                        >
                                            {/* top color bar */}
                                            <div style={{
                                                position: "absolute", top: 0, left: 0, right: 0, height: 2,
                                                background: color, borderRadius: "10px 10px 0 0", opacity: 0.85,
                                            }} />
                                            {/* icon + category badge row */}
                                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 4 }}>
                                                <CategoryIcon category={node.category} size={18} />
                                                <span style={{
                                                    fontSize: 8, background: color + "22", color,
                                                    border: `1px solid ${color}44`, borderRadius: 4,
                                                    padding: "1px 5px", fontWeight: 600, letterSpacing: "0.05em",
                                                    textTransform: "uppercase",
                                                }}>
                                                    {node.category}
                                                </span>
                                            </div>
                                            {/* label */}
                                            <div style={{
                                                color: "#fff", fontSize: 11, fontWeight: 600, lineHeight: 1.2,
                                                marginTop: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                                            }}>
                                                {node.label}
                                            </div>
                                            {/* description */}
                                            {node.description && (
                                                <div style={{
                                                    color: "#6b7280", fontSize: 9, lineHeight: 1.4,
                                                    overflow: "hidden", display: "-webkit-box",
                                                    WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                                                }}>
                                                    {node.description}
                                                </div>
                                            )}
                                        </div>
                                    </foreignObject>

                                    {/* ── Port handles (left + right) ── */}
                                    {(["left", "right"] as const).map(side => {
                                        const px = side === "right" ? node.width : 0;
                                        const py = node.height / 2;
                                        const isHovP = hoveredPort?.nodeId === node.id && hoveredPort?.side === side;
                                        return (
                                            <circle
                                                key={side}
                                                data-port="true"
                                                cx={px}
                                                cy={py}
                                                r={isHovP ? 7 : portR}
                                                fill={isHovP ? color : "#1a1f2e"}
                                                stroke={color}
                                                strokeWidth={1.5}
                                                style={{ cursor: "crosshair", transition: "r 0.1s, fill 0.1s" }}
                                                onMouseEnter={() => setHoveredPort({ nodeId: node.id, side })}
                                                onMouseLeave={() => setHoveredPort(null)}
                                                onMouseDown={e => handlePortMouseDown(e, node.id, side)}
                                                onMouseUp={e => handlePortMouseUp(e, node.id)}
                                            />
                                        );
                                    })}
                                </g>
                            );
                        })}
                    </g>
                </svg>

                {/* ── Connection hover tooltip ── */}
                {tooltipConn && hoveredConnId && !selectedConnId && (
                    <div style={{
                        position: "absolute",
                        left: tooltipConn.x + 12,
                        top: tooltipConn.y - 30,
                        background: "#1a1f2e",
                        border: "1px solid rgba(139,92,246,0.4)",
                        borderRadius: 6,
                        padding: "3px 10px",
                        fontSize: 11,
                        color: "#c4b5fd",
                        pointerEvents: "none",
                        zIndex: 30,
                        whiteSpace: "nowrap",
                    }}>
                        {connections.find(c => c.id === hoveredConnId)?.label ?? "connection"}
                    </div>
                )}

                {/* ── Selected connection panel ── */}
                {selectedConn && (() => {
                    const from = nodes.find(n => n.id === selectedConn.fromId);
                    const to = nodes.find(n => n.id === selectedConn.toId);
                    return (
                        <div style={{
                            position: "absolute",
                            right: 16,
                            top: 56,
                            width: 220,
                            background: "#131823",
                            border: "1px solid rgba(139,92,246,0.4)",
                            borderRadius: 10,
                            padding: 14,
                            zIndex: 35,
                            boxShadow: "0 8px 32px rgba(0,0,0,0.55)",
                        }}>
                            <div style={{ fontSize: 10, color: "#a78bfa", fontWeight: 700, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                                Connection
                            </div>
                            <div style={{ fontSize: 11, color: "#e5e7eb", marginBottom: 6 }}>
                                Label: <span style={{ color: "#a78bfa" }}>{selectedConn.label}</span>
                            </div>
                            <div style={{ fontSize: 10, color: "#6b7280", marginBottom: 2 }}>Source</div>
                            <select
                                value={selectedConn.fromId}
                                onChange={e => setConnections(prev => prev.map(c => c.id === selectedConn.id ? { ...c, fromId: e.target.value } : c))}
                                style={{ width: "100%", background: "#0b0e14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 5, color: "#e5e7eb", fontSize: 11, padding: "5px 7px", boxSizing: "border-box", marginBottom: 8, outline: "none" }}
                            >
                                {nodes.map(n => <option key={n.id} value={n.id}>{n.label}</option>)}
                            </select>
                            <div style={{ fontSize: 10, color: "#6b7280", marginBottom: 2 }}>Target</div>
                            <select
                                value={selectedConn.toId}
                                onChange={e => setConnections(prev => prev.map(c => c.id === selectedConn.id ? { ...c, toId: e.target.value } : c))}
                                style={{ width: "100%", background: "#0b0e14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 5, color: "#e5e7eb", fontSize: 11, padding: "5px 7px", boxSizing: "border-box", marginBottom: 12, outline: "none" }}
                            >
                                {nodes.map(n => <option key={n.id} value={n.id}>{n.label}</option>)}
                            </select>
                            <div style={{ display: "flex", gap: 8 }}>
                                <button
                                    onClick={() => { setConnections(prev => prev.filter(c => c.id !== selectedConn.id)); setSelectedConnId(null); }}
                                    style={{ flex: 1, background: "#450a0a", border: "1px solid #7f1d1d", borderRadius: 6, color: "#fca5a5", fontSize: 11, padding: "6px 0", cursor: "pointer" }}
                                >Delete</button>
                                <button
                                    onClick={() => setSelectedConnId(null)}
                                    style={{ flex: 1, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, color: "#6b7280", fontSize: 11, padding: "6px 0", cursor: "pointer" }}
                                >Close</button>
                            </div>
                        </div>
                    );
                })()}

                {/* ── Inline node edit popover ── */}
                {editingNode && (() => {
                    const node = nodes.find(n => n.id === editingNode);
                    if (!node) return null;
                    const ex = node.x * zoom + pan.x;
                    const ey = node.y * zoom + pan.y + node.height * zoom + 8;
                    return (
                        <div style={{
                            position: "absolute",
                            left: Math.min(ex, window.innerWidth - 270),
                            top: Math.min(ey, window.innerHeight - 260),
                            width: 248,
                            background: "#131823",
                            border: "1px solid rgba(139,92,246,0.4)",
                            borderRadius: 10,
                            padding: 14,
                            zIndex: 40,
                            boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
                        }}>
                            <div style={{ fontSize: 11, color: "#a78bfa", fontWeight: 700, marginBottom: 8 }}>Edit Node</div>
                            <input
                                value={editLabel}
                                onChange={e => setEditLabel(e.target.value)}
                                style={{ width: "100%", background: "#0b0e14", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, color: "#fff", fontSize: 12, padding: "6px 8px", boxSizing: "border-box", marginBottom: 8, outline: "none" }}
                                placeholder="Label"
                            />
                            <textarea
                                value={editDesc}
                                onChange={e => setEditDesc(e.target.value)}
                                rows={2}
                                style={{ width: "100%", background: "#0b0e14", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, color: "#a3a3a3", fontSize: 11, padding: "6px 8px", boxSizing: "border-box", resize: "none", outline: "none", marginBottom: 8 }}
                                placeholder="Description"
                            />
                            <select
                                value={editCat}
                                onChange={e => setEditCat(e.target.value as ComponentCategory)}
                                style={{ width: "100%", background: "#0b0e14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, color: "#a3a3a3", fontSize: 12, padding: "6px 8px", boxSizing: "border-box", marginBottom: 10, outline: "none" }}
                            >
                                {VALID_CATEGORIES.map(cat => <option key={cat} value={cat}>{cat}</option>)}
                            </select>
                            <div style={{ display: "flex", gap: 8 }}>
                                <button onClick={saveEdit} style={{ flex: 1, background: "#a78bfa", border: "none", borderRadius: 6, color: "#fff", fontSize: 11, fontWeight: 700, padding: "6px 0", cursor: "pointer" }}>Save</button>
                                <button onClick={() => setEditingNode(null)} style={{ flex: 1, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, color: "#a3a3a3", fontSize: 11, padding: "6px 0", cursor: "pointer" }}>Cancel</button>
                            </div>
                        </div>
                    );
                })()}

                {/* ── Empty state ── */}
                {nodes.length === 0 && !isLoading && (
                    <div style={{
                        position: "absolute", inset: 0, display: "flex", flexDirection: "column",
                        alignItems: "center", justifyContent: "center", pointerEvents: "none",
                    }}>
                        <div style={{ color: "rgba(139,92,246,0.3)", fontSize: 52, marginBottom: 12 }}>⬡</div>
                        <p style={{ color: "rgba(255,255,255,0.2)", fontSize: 13, textAlign: "center", lineHeight: 1.8 }}>
                            No components yet.<br />Ask Yantra AI to get started.
                        </p>
                    </div>
                )}
            </div>

            {/* ── Component Library Sidebar on Right ── */}
            <div className="w-[320px] h-full bg-[#0B0E14] border-l border-neutral-800/50 flex flex-col shrink-0">

                {/* Header */}
                <div className="flex items-center justify-between p-4 pb-2 mt-2">
                    <h2 className="text-xs font-bold text-white tracking-widest uppercase">Component Library</h2>
                    <button className="text-neutral-500 hover:text-neutral-300">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Search Bar */}
                <div className="px-4 py-3 flex gap-2">
                    <div className="flex-1 bg-[#131823] rounded-lg border border-neutral-800/50 flex items-center px-3">
                        <Search className="w-4 h-4 text-neutral-500 shrink-0" />
                        <input
                            type="text"
                            placeholder="Search components..."
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            className="w-full bg-transparent border-none text-xs text-neutral-200 focus:outline-none focus:ring-0 px-2 py-2.5 placeholder:text-neutral-600"
                        />
                    </div>
                    <button className="w-10 bg-[#131823] rounded-lg border border-neutral-800/50 flex items-center justify-center text-neutral-400 hover:text-neutral-200 shrink-0">
                        <SlidersHorizontal className="w-4 h-4" />
                    </button>
                </div>

                {/* Tabs */}
                <div className="px-4 py-1 flex items-center gap-4 text-[11px] font-medium text-neutral-500 border-b border-neutral-800/30 overflow-x-auto no-scrollbar">
                    {TABS.map(tab => (
                        <div
                            key={tab.key}
                            onClick={() => setActiveCategory(tab.key)}
                            className={`pb-2 whitespace-nowrap cursor-pointer relative ${activeCategory === tab.key ? "text-white" : "hover:text-neutral-300"}`}
                        >
                            {tab.label}
                            {activeCategory === tab.key && (
                                <div className="absolute bottom-0 left-0 w-full h-[2px] bg-blue-500 rounded-t-full" />
                            )}
                        </div>
                    ))}
                </div>

                {/* List Content */}
                <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
                    {isLoading ? (
                        <div style={{ color: "rgba(139,92,246,0.5)", fontSize: 11, textAlign: "center", marginTop: 40 }}>
                            Loading components...
                        </div>
                    ) : filteredNodes.length === 0 ? (
                        <div style={{ color: "rgba(255,255,255,0.15)", fontSize: 11, textAlign: "center", marginTop: 32, lineHeight: 1.8 }}>
                            {nodes.length === 0 ? "Ask the AI to populate components" : "No matching components"}
                        </div>
                    ) : filteredNodes.map(node => {
                        const color = CATEGORY_COLOR[node.category];
                        const isSelected = selectedId === node.id;
                        return (
                            <div
                                key={node.id}
                                onClick={() => { setSelectedId(node.id); setSelectedConnId(null); }}
                                style={{
                                    width: "100%",
                                    minHeight: 72,
                                    background: isSelected ? "#1a1f2e" : "#131823",
                                    borderRadius: 12,
                                    borderTop: `1px solid ${isSelected ? color + "66" : "rgba(255,255,255,0.06)"}`,
                                    borderRight: `1px solid ${isSelected ? color + "66" : "rgba(255,255,255,0.06)"}`,
                                    borderBottom: `1px solid ${isSelected ? color + "66" : "rgba(255,255,255,0.06)"}`,
                                    borderLeft: `3px solid ${color}`,
                                    padding: "10px 12px",
                                    boxSizing: "border-box",
                                    cursor: "pointer",
                                    display: "flex",
                                    alignItems: "flex-start",
                                    gap: 10,
                                    transition: "background 0.15s",
                                    boxShadow: isSelected ? `0 0 0 1px ${color}33` : "none",
                                }}
                            >
                                <div style={{ marginTop: 2, flexShrink: 0 }}>
                                    <CategoryIcon category={node.category} size={18} />
                                </div>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ color: "#fff", fontSize: 11, fontWeight: 700, lineHeight: 1.3, marginBottom: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                        {node.label}
                                    </div>
                                    <div style={{ color: "#6b7280", fontSize: 10, lineHeight: 1.5, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                                        {node.description || "No description"}
                                    </div>
                                </div>
                                <button
                                    title="Locate on canvas"
                                    onClick={e => { e.stopPropagation(); locateNode(node.id); }}
                                    style={{ background: "none", border: "none", color: "#4b5563", cursor: "pointer", padding: 4, borderRadius: 4, display: "flex", alignItems: "center", flexShrink: 0, marginTop: 1 }}
                                    onMouseEnter={e => (e.currentTarget.style.color = color)}
                                    onMouseLeave={e => (e.currentTarget.style.color = "#4b5563")}
                                >
                                    <Crosshair style={{ width: 13, height: 13 }} />
                                </button>
                            </div>
                        );
                    })}
                </div>

                {/* Add Custom Component Button */}
                <div className="p-4 pb-6 pt-2">
                    {showAddModal && (
                        <div style={{
                            background: "#131823",
                            border: "1px solid rgba(139,92,246,0.35)",
                            borderRadius: 12,
                            padding: 16,
                            marginBottom: 10,
                            boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
                        }}>
                            <div style={{ fontSize: 11, color: "#a78bfa", fontWeight: 700, marginBottom: 10 }}>New Component</div>
                            <input
                                value={newName}
                                onChange={e => setNewName(e.target.value)}
                                placeholder="Component name"
                                style={{ width: "100%", background: "#0b0e14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, color: "#fff", fontSize: 12, padding: "7px 10px", boxSizing: "border-box", marginBottom: 8, outline: "none" }}
                            />
                            <select
                                value={newCat}
                                onChange={e => setNewCat(e.target.value as ComponentCategory)}
                                style={{ width: "100%", background: "#0b0e14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, color: "#a3a3a3", fontSize: 12, padding: "7px 10px", boxSizing: "border-box", marginBottom: 8, outline: "none" }}
                            >
                                {VALID_CATEGORIES.map(cat => <option key={cat} value={cat}>{cat}</option>)}
                            </select>
                            <textarea
                                value={newDesc}
                                onChange={e => setNewDesc(e.target.value)}
                                placeholder="Description (optional)"
                                rows={2}
                                style={{ width: "100%", background: "#0b0e14", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, color: "#a3a3a3", fontSize: 11, padding: "7px 10px", boxSizing: "border-box", resize: "none", outline: "none", marginBottom: 10 }}
                            />
                            <div style={{ display: "flex", gap: 8 }}>
                                <button
                                    onClick={handleAddComponent}
                                    style={{ flex: 1, background: "#a78bfa", border: "none", borderRadius: 6, color: "#fff", fontSize: 11, fontWeight: 700, padding: "7px 0", cursor: "pointer" }}
                                >Add to Canvas</button>
                                <button
                                    onClick={() => setShowAddModal(false)}
                                    style={{ flex: 1, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, color: "#6b7280", fontSize: 11, padding: "7px 0", cursor: "pointer" }}
                                >Cancel</button>
                            </div>
                        </div>
                    )}
                    <button
                        onClick={() => setShowAddModal(v => !v)}
                        className="w-full py-2.5 rounded-lg border border-blue-500/30 bg-[#0B0E14] text-blue-500 text-xs font-medium flex items-center justify-center gap-2 hover:bg-blue-500/5 transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        Add Custom Component
                    </button>
                </div>
            </div>
        </div>
    );
}
