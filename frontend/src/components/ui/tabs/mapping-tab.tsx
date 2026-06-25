"use client";

import {
    Search, X, SlidersHorizontal, Plus, Crosshair,
    LayoutGrid, Maximize2, Trash2, RefreshCw, Network, PanelLeft, PanelRight
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
    mechanical: "#94a3b8",
    actuator: "#f97316",
    controller: "#a855f7",
    sensor: "#06b6d4",
    power: "#eab308",
    electronic: "#4ade80",
};

export const WIRE_COLORS: Record<string, string> = {
    power: '#ef4444',     // Red
    ground: '#10b981',    // Emerald Green
    signal: '#eab308',    // Yellow
    data: '#a855f7',      // Purple
    drive: '#f97316',     // Orange
    pwm: '#3b82f6',       // Blue
    can: '#14b8a6',       // Teal
    linkage: '#94a3b8',   // Slate
    default: '#60a5fa'    // Light Blue
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

    const prompt1 =
        `Return ONLY a JSON array. No explanation, no markdown, no extra text. ` +
        `Here is the list of existing components already in the system:\n${existingStr}\n\n` +
        `For the topic: '${topic}', list a comprehensive and highly detailed set of NEW low-level hardware components needed. ` +
        `DO NOT duplicate or re-describe ANY of the existing components listed above. If you need to refer to an existing component in 'connects_to', use its EXACT name. ` +
        `Each item must have exactly these fields: ` +
        `{"name": string, "category": one of exactly: "actuator"|"sensor"|"controller"|"mechanical"|"power"|"electronic", ` +
        `"description": string, "connects_to": string[]}`;

    try {
        const res1 = await fetch(`${API_BASE}/api/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
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
        const res2 = await fetch(`${API_BASE}/api/ask`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
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

﻿function generateConnections(
    nodes: ComponentNode[],
    raw: RawComponent[]
): Connection[] {
    const connections: Connection[] = [];
    const seen = new Set<string>();

    let connCounter = 0;

    function addConn(
        fromId: string,
        toId: string,
        label: string,
        userEdited = false
    ) {
        if (!fromId || !toId || fromId === toId) return;
        const key1 = `${fromId}→${toId}→${label}`;
        const key2 = `${toId}→${fromId}→${label}`;
        if (seen.has(key1) || seen.has(key2)) return;
        seen.add(key1);
        connections.push({
            id: `conn-${connCounter++}-${Date.now()}`,
            fromId,
            toId,
            label,
            isUserEdited: userEdited,
        });
    }

    const nodeMap = new Map<string, ComponentNode>();
    nodes.forEach(n => nodeMap.set(n.id, n));

    // Primary pass ΓÇö use RAG connects_to
    raw.forEach(rc => {
        const fromNode = nodes.find(n => fuzzyMatch(n.label, rc.name));
        if (!fromNode) return;
        rc.connects_to.forEach(targetName => {
            const toNode = nodes.find(n => fuzzyMatch(n.label, targetName));
            if (!toNode) return;
            
            let srcId = fromNode.id;
            let dstId = toNode.id;

            // Enforce directionality overrides
            if (fromNode.category === 'actuator' && toNode.category === 'controller') {
                srcId = toNode.id;
                dstId = fromNode.id;
            } else if (toNode.category === 'power') {
                srcId = toNode.id;
                dstId = fromNode.id;
            }

            const srcNode = nodes.find(n => n.id === srcId)!;
            const dstNode = nodes.find(n => n.id === dstId)!;
            const pairKey = `${srcNode.category}-${dstNode.category}`;
            
            let label = "connection";
            if (pairKey.includes("mechanical")) label = "linkage";
            else if (pairKey === "actuator-controller" || pairKey === "controller-actuator") label = "drive";
            else if (pairKey.includes("sensor") && pairKey.includes("power")) label = "power";
            else if (pairKey.includes("sensor")) label = "data";
            else if (pairKey.includes("power")) label = "power";
            else if (pairKey.includes("electronic")) label = "signal";
            
            if (label === "power") {
                addConn(srcId, dstId, "power");
                addConn(srcId, dstId, "ground");
            } else {
                addConn(srcId, dstId, label);
            }
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
        .forEach(a => controllers.forEach(c => addConn(c.id, a.id, "drive")));
    sensors
        .filter(s => !connectedIds.has(s.id))
        .forEach(s => controllers.forEach(c => addConn(s.id, c.id, "data")));
        
    // Chain mechanical parts to reduce crossing lines
    const unconnectedMechanical = mechanical.filter(m => !connectedIds.has(m.id));
    if (unconnectedMechanical.length > 0) {
        if (actuators.length > 0) {
            addConn(unconnectedMechanical[0].id, actuators[0].id, "linkage");
        }
        for (let i = 1; i < unconnectedMechanical.length; i++) {
            addConn(unconnectedMechanical[i].id, unconnectedMechanical[i-1].id, "linkage");
        }
    }
    
    // Route power hierarchically: Power -> Controller -> Actuator (removes giant sweeping ground wires)
    power
        .filter(p => !connectedIds.has(p.id))
        .forEach(p => {
            if (controllers.length > 0) {
                controllers.forEach(c => { 
                    addConn(p.id, c.id, "power"); 
                    addConn(p.id, c.id, "ground"); 
                });
            } else {
                actuators.forEach(a => { 
                    addConn(p.id, a.id, "power"); 
                    addConn(p.id, a.id, "ground"); 
                });
            }
        });
        
    controllers
        .filter(c => !connectedIds.has(c.id))
        .forEach(c => electronic.forEach(e => addConn(c.id, e.id, "signal")));

    // ΓöÇΓöÇΓöÇ Post-processing: Ground Wires & Triple-Driver Resolution ΓöÇΓöÇΓöÇ
    
    // 1. Ensure all power wires have a ground return path
    const currentConns = [...connections];
    currentConns.forEach(c => {
        if (c.label === "power") {
            const hasGround = connections.find(existing => existing.fromId === c.fromId && existing.toId === c.toId && existing.label === "ground");
            if (!hasGround) {
                addConn(c.fromId, c.toId, "ground");
            }
        }
    });

    // 2. Resolve Triple-Driver Ambiguity
    const actIds = actuators.map(a => a.id);
    actIds.forEach(actId => {
        const drives = connections.filter(c => c.toId === actId && c.label === "drive");
        if (drives.length > 1) {
            const drivers = drives.map(d => nodes.find(n => n.id === d.fromId)).filter(Boolean) as ComponentNode[];
            // Sort drivers: Shield/Driver > specific MCU > generic controller
            drivers.sort((a, b) => {
                const score = (n: ComponentNode) => {
                    const l = n.label.toLowerCase();
                    if (l.includes("shield") || l.includes("driver") || l.includes("hat")) return 3;
                    if (l.includes("arduino") || l.includes("raspberry") || l.includes("mega") || l.includes("esp")) return 2;
                    return 1;
                };
                return score(b) - score(a);
            });
            const bestDriver = drivers[0];
            
            // Remove weaker drives to actuator, daisy-chain to bestDriver instead
            for (let i = 1; i < drivers.length; i++) {
                const weaker = drivers[i];
                const idx = connections.findIndex(c => c.fromId === weaker.id && c.toId === actId && c.label === "drive");
                if (idx !== -1) connections.splice(idx, 1);
                
                const existing = connections.find(c => 
                    (c.fromId === weaker.id && c.toId === bestDriver.id) || 
                    (c.toId === weaker.id && c.fromId === bestDriver.id)
                );
                if (!existing) {
                    addConn(weaker.id, bestDriver.id, "signal");
                }
            }
        }
    });

    return connections;
}



// ─── Seed data ────────────────────────────────────────────────────────────────




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
                <div style={{ fontSize: "9px", color: color, textTransform: "uppercase", letterSpacing: "1px" }}>
                    {data.category}
                </div>
                
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

export function MappingTab({ aiResponse = "", currentQuery = "", designData, isChatLoading = false }: MappingTabProps) {
    const nodeTypes = useMemo(() => ({ customComponent: CustomComponentNode }), []);
    const [activeView, setActiveView] = useState<"canvas">("canvas");
    const [isLibraryOpen, setIsLibraryOpen] = useState(true);
    const [isInspectorOpen, setIsInspectorOpen] = useState(true);
    
    useEffect(() => {
        console.log(`[MappingTab] Successfully mounted/loaded with activeView: ${activeView}`);
    }, []);

    const [nodes, setNodes] = useState<ComponentNode[]>([]);
    const [rawComponents, setRawComponents] = useState<RawComponent[]>([]);
    const [connections, setConnections] = useState<Connection[]>([]);
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
        const edgeGroups = new Map<string, Connection[]>();
        connections.forEach(c => {
            const key = c.fromId < c.toId ? `${c.fromId}-${c.toId}` : `${c.toId}-${c.fromId}`;
            if (!edgeGroups.has(key)) edgeGroups.set(key, []);
            edgeGroups.get(key)!.push(c);
        });

        return connections.map(c => {
            const edgeColor = WIRE_COLORS[c.label?.toLowerCase()] || WIRE_COLORS.default;
            
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

            return {
                id: c.id,
                source: c.fromId,
                target: c.toId,
                label: c.label,
                type: edgeType,
                animated: false,
                style: { stroke: edgeColor, strokeWidth: 1.5 },
                labelStyle: { fill: '#a3a3a3', fontWeight: 600, fontSize: 11, className: 'edge-label-text' },
                labelBgStyle: { fill: '#13161c', className: 'edge-label-bg' },
                markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor },
                className: 'custom-edge-hover'
            };
        });
    }, [connections]);
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
        
        const newConnections = generateConnections(updatedNodes, updatedRaw);
        setConnections(newConnections);
        const layoutedNodes = applyLayout(updatedNodes, newConnections);
        setNodes(layoutedNodes);
        
        setIsLoading(false);
    }, [aiResponse, rawComponents, nodes, designData]);
    // ── useEffect: load shared designData when present ─────────────────────────
    useEffect(() => {
        if (!designData) return;
        
        const comps: RawComponent[] = [];
        const rawNodes: Omit<ComponentNode, "x" | "y">[] = [];
        
        if (designData.subsystems) {
            designData.subsystems.forEach((sub: any) => {
                const compList = sub.components || [];
                if (compList.length === 0) {
                    const category = "electronic";
                    const description = "No components mapped for this subsystem.";
                    const placeholderId = `placeholder-${sub.name.replace(/\s+/g, "_")}`;
                    
                    comps.push({
                        name: `[Subsystem: ${sub.name}]`,
                        category,
                        description,
                        connects_to: []
                    });
                    
                    rawNodes.push({
                        id: placeholderId,
                        label: `No components mapped for ${sub.name}`,
                        category,
                        description,
                        width: NODE_W,
                        height: NODE_H
                    });
                } else {
                    compList.forEach((comp: any) => {
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
        setIsLoading(false);
    }, [designData]);

    // ── useEffect: re-fetch when query changes ─────────────────────────────────
    useEffect(() => {
        if (designData || !currentQuery) return;
        if (lastQueryRef.current === currentQuery) return;
        lastQueryRef.current = currentQuery;
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

    

    const validationList = useMemo(() => {
        return designData?.validation || [];
    }, [designData]);



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
        } else if (currentQuery && currentQuery !== lastQueryRef.current && !designData) {
            // Fallback for standalone query execution
            lastQueryRef.current = currentQuery;
            doFetch(currentQuery);
        }
    }, [designData, currentQuery, doFetch]);

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

    

    return (
        <div className="w-full h-full flex flex-col bg-[#050505] overflow-hidden text-neutral-400 font-sans">
            


            <div className="flex-1 flex overflow-hidden relative">
                {/* FLOATING TOGGLE BUTTON */}
                <button 
                    onClick={() => setIsLibraryOpen(!isLibraryOpen)}
                    className={`absolute top-[26px] left-4 z-50 p-1.5 rounded transition-colors ${isLibraryOpen ? 'bg-[#1a2333] text-sky-400' : 'bg-[#131823] border border-neutral-800 text-neutral-400 hover:text-white shadow-lg'}`}
                    title="Toggle Component Library"
                >
                    <PanelLeft size={16} />
                </button>

                {/* 1. COMPONENT LIBRARY (Left Column) */}
                <div className={`h-full bg-[#0B0E14] border-r border-neutral-800/50 flex flex-col shrink-0 z-20 transition-all duration-300 ease-in-out ${isLibraryOpen ? 'w-[320px] opacity-100' : 'w-0 opacity-0 border-none overflow-hidden'}`}>
                    <div className="flex items-center justify-between p-4 pl-12 pb-2 mt-2">
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
                                            setNodes(p => p.map(n => n.id === node.id ? { ...n, quantity: (n.quantity || 1) + 1 } : n));
                                            setRawComponents(p => p.map(r => r.name.toLowerCase() === node.label.toLowerCase() ? { ...r, quantity: (r.quantity || 1) + 1 } : r));
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
                                    .react-flow__controls {
                                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5) !important;
                                        border: 1px solid #333 !important;
                                        background-color: #0B0E14 !important;
                                        border-radius: 6px !important;
                                        overflow: hidden !important;
                                    }
                                    .react-flow__controls-button {
                                        background-color: #0B0E14 !important;
                                        border-bottom: 1px solid #333 !important;
                                        color: #fff !important;
                                    }
                                    .react-flow__controls-button:last-child {
                                        border-bottom: none !important;
                                    }
                                    .react-flow__controls-button:hover {
                                        background-color: #1a2333 !important;
                                    }
                                    .react-flow__controls-button svg {
                                        fill: #ccc !important;
                                    }
                                    .react-flow__controls-button:hover svg {
                                        fill: #fff !important;
                                    }
                                `}</style>
                                <ReactFlow
                                    nodes={rfNodes}
                                    edges={rfEdges}
                                    onNodesChange={onNodesChange}
                                    onConnect={onConnect}
                                    onNodeClick={(_: any, node: any) => {
                                        setSelectedId(node.id);
                                        setIsInspectorOpen(true);
                                    }}
                                    nodeTypes={nodeTypes}
                                    fitView
                                    onlyRenderVisibleElements={true}
                                    proOptions={{ hideAttribution: true }}
                                >
                                    <Background color="#222" gap={16} />
                                    <Controls />
                                </ReactFlow>
                            </div>
                        </div>
                </div>

                {/* FLOATING RIGHT TOGGLE BUTTON */}
                <button 
                    onClick={() => setIsInspectorOpen(!isInspectorOpen)}
                    className={`absolute top-[22px] right-4 z-50 p-1.5 rounded transition-colors ${isInspectorOpen ? 'bg-[#1a2333] text-sky-400' : 'bg-[#131823] border border-neutral-800 text-neutral-400 hover:text-white shadow-lg'}`}
                    title="Toggle Inspector"
                >
                    <PanelRight size={16} />
                </button>

                {/* 3. INSPECTOR (Right Column) */}
                <div className={`h-full bg-[#0B0E14] flex flex-col shrink-0 z-20 transition-all duration-300 ease-in-out ${isInspectorOpen ? 'w-[340px] opacity-100' : 'w-0 opacity-0 border-none overflow-hidden'}`}>
                    <div className="flex items-center justify-between p-4 pr-12 border-b border-neutral-800/50 bg-[#0f1219]">
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
                                                const labelColor = WIRE_COLORS[conn.label?.toLowerCase()] || WIRE_COLORS.default;
                                                return (
                                                    <div key={conn.id} className="flex items-center justify-between bg-[#13161c] p-2.5 rounded border border-neutral-800/80">
                                                        <div className="text-xs text-neutral-300 truncate pr-2 flex items-center">
                                                            From: <span className="font-medium text-white ml-1">{fromNode?.label || "Unknown"}</span>
                                                            <span className="ml-2 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded" style={{color: labelColor, border: `1px solid ${labelColor}40`, background: `${labelColor}15`}}>{conn.label}</span>
                                                        </div>
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
                                                const labelColor = WIRE_COLORS[conn.label?.toLowerCase()] || WIRE_COLORS.default;
                                                return (
                                                    <div key={conn.id} className="flex items-center justify-between bg-[#13161c] p-2.5 rounded border border-neutral-800/80">
                                                        <div className="text-xs text-neutral-300 truncate pr-2 flex items-center">
                                                            To: <span className="font-medium text-white ml-1">{toNode?.label || "Unknown"}</span>
                                                            <span className="ml-2 text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded" style={{color: labelColor, border: `1px solid ${labelColor}40`, background: `${labelColor}15`}}>{conn.label}</span>
                                                        </div>
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
                                Select a component from the Canvas to view its details and manage connections.
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
