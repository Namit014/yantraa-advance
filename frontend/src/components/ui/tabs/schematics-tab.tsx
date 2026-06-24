"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
    MousePointer2, Hand, Type, Minus, Square, Circle, GitMerge,
    Undo2, Redo2, ZoomIn, ZoomOut, Trash2, Download, Grid3X3,
    Cpu, Zap, ToggleLeft, Radio, Activity, ChevronDown, Plus,
    BrainCircuit, AlertCircle, CheckCircle, AlertTriangle, Battery,
    RotateCcw
} from "lucide-react";
import { useSchematicStore, SchematicElement, Point } from "../../schematic/useSchematicStore";

type Tool = "select" | "pan" | "text" | "line" | "rect" | "circle" | "connect" | "component";

const COMPONENT_SYMBOLS: Record<string, { label: string; icon: React.ElementType<any>; draw: (ctx: CanvasRenderingContext2D, x: number, y: number, scale: number) => void }> = {
    resistor: {
        label: "Resistor", icon: Activity,
        draw: (ctx, x, y, s) => {
            ctx.beginPath();
            ctx.moveTo(x - 30 * s, y); ctx.lineTo(x - 15 * s, y);
            ctx.rect(x - 15 * s, y - 6 * s, 30 * s, 12 * s);
            ctx.moveTo(x + 15 * s, y); ctx.lineTo(x + 30 * s, y);
            ctx.stroke();
        }
    },
    capacitor: {
        label: "Capacitor", icon: Zap,
        draw: (ctx, x, y, s) => {
            ctx.beginPath();
            ctx.moveTo(x - 30 * s, y); ctx.lineTo(x - 4 * s, y);
            ctx.moveTo(x - 4 * s, y - 12 * s); ctx.lineTo(x - 4 * s, y + 12 * s);
            ctx.moveTo(x + 4 * s, y - 12 * s); ctx.lineTo(x + 4 * s, y + 12 * s);
            ctx.moveTo(x + 4 * s, y); ctx.lineTo(x + 30 * s, y);
            ctx.stroke();
        }
    },
    ic: {
        label: "IC / MCU", icon: Cpu,
        draw: (ctx, x, y, s) => {
            ctx.beginPath();
            ctx.rect(x - 20 * s, y - 20 * s, 40 * s, 40 * s);
            ctx.stroke();
            ctx.font = `${10 * s}px monospace`;
            ctx.fillStyle = ctx.strokeStyle as string;
            ctx.textAlign = "center";
            ctx.fillText("IC", x, y + 4 * s);
        }
    },
    led: {
        label: "LED", icon: Radio,
        draw: (ctx, x, y, s) => {
            ctx.beginPath();
            ctx.moveTo(x - 30 * s, y); ctx.lineTo(x - 10 * s, y);
            ctx.moveTo(x - 10 * s, y - 12 * s); ctx.lineTo(x + 10 * s, y);
            ctx.lineTo(x - 10 * s, y + 12 * s); ctx.closePath();
            ctx.moveTo(x + 10 * s, y - 12 * s); ctx.lineTo(x + 10 * s, y + 12 * s);
            ctx.moveTo(x + 10 * s, y); ctx.lineTo(x + 30 * s, y);
            ctx.stroke();
        }
    },
    switch: {
        label: "Switch", icon: ToggleLeft,
        draw: (ctx, x, y, s) => {
            ctx.beginPath();
            ctx.moveTo(x - 30 * s, y); ctx.lineTo(x - 10 * s, y);
            ctx.arc(x - 10 * s, y, 3 * s, 0, Math.PI * 2);
            ctx.moveTo(x - 8 * s, y); ctx.lineTo(x + 10 * s, y - 12 * s);
            ctx.arc(x + 10 * s, y, 3 * s, 0, Math.PI * 2);
            ctx.moveTo(x + 10 * s, y); ctx.lineTo(x + 30 * s, y);
            ctx.stroke();
        }
    }
};

function generateId() { return Math.random().toString(36).slice(2, 10); }
function snapToGrid(val: number, gridSize: number) { return Math.round(val / gridSize) * gridSize; }

interface SchematicsTabProps {
    designData?: any;
    currentQuery?: string;
}

export function SchematicsTab({ designData, currentQuery }: SchematicsTabProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const { 
        elements, setElements, pushHistory, undo, redo, historyIdx, history,
        generate, regenerate, isGenerating, generatingStep, 
        ercIssues, powerBudget, confidence, assumptions, fallbackUsed
    } = useSchematicStore();

    const [tool, setTool] = useState<Tool>("select");
    const [zoom, setZoom] = useState(1);
    const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
    const [showGrid, setShowGrid] = useState(true);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [showComponentMenu, setShowComponentMenu] = useState(false);
    const [selectedComponent, setSelectedComponent] = useState<string>("resistor");
    
    // UI State for panels
    const [showAssumptions, setShowAssumptions] = useState(false);
    const [showErcPanel, setShowErcPanel] = useState(false);
    const [showConfirmRegen, setShowConfirmRegen] = useState(false);

    // Drawing state
    const isDrawing = useRef(false);
    const isPanning = useRef(false);
    const startPoint = useRef<Point>({ x: 0, y: 0 });
    const currentElement = useRef<SchematicElement | null>(null);
    const panStart = useRef<Point>({ x: 0, y: 0 });
    const wirePoints = useRef<Point[]>([]);

    const GRID = 20;
    const STROKE = "#1a1a1a";

    const toWorld = useCallback((screenX: number, screenY: number): Point => {
        const canvas = canvasRef.current!;
        const rect = canvas.getBoundingClientRect();
        return {
            x: (screenX - rect.left - pan.x) / zoom,
            y: (screenY - rect.top - pan.y) / zoom,
        };
    }, [pan, zoom]);

    const deleteSelected = useCallback(() => {
        if (selectedIds.size === 0) return;
        const next = elements.filter(e => !selectedIds.has(e.id));
        pushHistory(next);
        setSelectedIds(new Set());
    }, [elements, selectedIds, pushHistory]);

    // Draw loop
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d")!;
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, w, h);

        ctx.save();
        ctx.translate(pan.x, pan.y);
        ctx.scale(zoom, zoom);

        if (showGrid) {
            const startX = Math.floor(-pan.x / zoom / GRID) * GRID;
            const startY = Math.floor(-pan.y / zoom / GRID) * GRID;
            const endX = startX + w / zoom + GRID * 2;
            const endY = startY + h / zoom + GRID * 2;

            ctx.fillStyle = "#c8c8c8";
            for (let gx = startX; gx < endX; gx += GRID) {
                for (let gy = startY; gy < endY; gy += GRID) {
                    ctx.beginPath();
                    ctx.arc(gx, gy, 0.8 / zoom, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
        }

        // Draw elements
        for (const el of elements) {
            ctx.save();
            ctx.strokeStyle = selectedIds.has(el.id) || el.highlightErc ? "#ef4444" : (selectedIds.has(el.id) ? "#3b82f6" : el.color);
            ctx.fillStyle = selectedIds.has(el.id) ? "#3b82f650" : "transparent";
            ctx.lineWidth = el.strokeWidth / zoom;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";

            if (el.type === "line") {
                ctx.beginPath(); ctx.moveTo(el.x, el.y); ctx.lineTo(el.x2!, el.y2!); ctx.stroke();
            } else if (el.type === "rect") {
                ctx.beginPath(); ctx.rect(el.x, el.y, el.width!, el.height!); ctx.stroke();
                if (selectedIds.has(el.id)) ctx.fill();
            } else if (el.type === "circle") {
                ctx.beginPath(); ctx.arc(el.x, el.y, el.radius!, 0, Math.PI * 2); ctx.stroke();
                if (selectedIds.has(el.id)) ctx.fill();
            } else if (el.type === "text") {
                ctx.fillStyle = el.color; ctx.font = `${14 / zoom}px 'Inter', sans-serif`;
                ctx.fillText(el.text || "", el.x, el.y);
            } else if (el.type === "wire") {
                if (el.points && el.points.length >= 2) {
                    ctx.beginPath(); ctx.moveTo(el.points[0].x, el.points[0].y);
                    for (let i = 1; i < el.points.length; i++) ctx.lineTo(el.points[i].x, el.points[i].y);
                    ctx.stroke();
                    for (const pt of el.points) {
                        ctx.beginPath(); ctx.arc(pt.x, pt.y, 2.5 / zoom, 0, Math.PI * 2);
                        ctx.fillStyle = el.color; ctx.fill();
                    }
                }
            } else if (el.type === "component") {
                ctx.strokeStyle = selectedIds.has(el.id) ? "#3b82f6" : STROKE;
                ctx.lineWidth = 1.5 / zoom;
                const sym = COMPONENT_SYMBOLS[el.componentType || "resistor"];
                if (sym) sym.draw(ctx, el.x, el.y, 1 / zoom * zoom);
            } else if (el.type === "ic_block") {
                // Systematic default renderer for parts-db entries
                const bw = 100;
                const bh = 140; // rough size, can be calculated dynamically based on pins
                
                ctx.strokeStyle = el.highlightErc ? "#ef4444" : (selectedIds.has(el.id) ? "#3b82f6" : STROKE);
                ctx.lineWidth = 2 / zoom;
                ctx.fillStyle = "#fafafa";
                ctx.fillRect(el.x - bw/2, el.y - bh/2, bw, bh);
                ctx.strokeRect(el.x - bw/2, el.y - bh/2, bw, bh);
                
                ctx.fillStyle = "#1a1a1a";
                ctx.font = `bold ${12 / zoom}px 'Inter', sans-serif`;
                ctx.textAlign = "center";
                ctx.fillText(el.designator || el.partId || "IC", el.x, el.y - bh/2 + 20);
                
                ctx.font = `${10 / zoom}px monospace`;
                // Draw pin stubs (simplified)
                if (el.pinStubs) {
                    for (const stub of el.pinStubs) {
                        ctx.fillStyle = "#666";
                        if (stub.side === "left") {
                            ctx.beginPath(); ctx.moveTo(el.x - bw/2, el.y - bh/2 + stub.order * 15 + 20); ctx.lineTo(el.x - bw/2 - 10, el.y - bh/2 + stub.order * 15 + 20); ctx.stroke();
                            ctx.textAlign = "left"; ctx.fillText(stub.name, el.x - bw/2 + 5, el.y - bh/2 + stub.order * 15 + 23);
                        } else if (stub.side === "right") {
                            ctx.beginPath(); ctx.moveTo(el.x + bw/2, el.y - bh/2 + stub.order * 15 + 20); ctx.lineTo(el.x + bw/2 + 10, el.y - bh/2 + stub.order * 15 + 20); ctx.stroke();
                            ctx.textAlign = "right"; ctx.fillText(stub.name, el.x + bw/2 - 5, el.y - bh/2 + stub.order * 15 + 23);
                        }
                    }
                }
            }

            // Selection box
            if (selectedIds.has(el.id) && el.type !== "text" && el.type !== "component" && el.type !== "ic_block") {
                ctx.setLineDash([4 / zoom, 4 / zoom]); ctx.strokeStyle = "#3b82f6"; ctx.lineWidth = 1 / zoom;
                const pad = 6 / zoom;
                if (el.type === "line") {
                    const minX = Math.min(el.x, el.x2!) - pad; const minY = Math.min(el.y, el.y2!) - pad;
                    const maxX = Math.max(el.x, el.x2!) + pad; const maxY = Math.max(el.y, el.y2!) + pad;
                    ctx.strokeRect(minX, minY, maxX - minX, maxY - minY);
                } else if (el.type === "rect") {
                    ctx.strokeRect(el.x - pad, el.y - pad, (el.width || 0) + pad * 2, (el.height || 0) + pad * 2);
                } else if (el.type === "circle") {
                    ctx.beginPath(); ctx.arc(el.x, el.y, (el.radius || 0) + pad, 0, Math.PI * 2); ctx.stroke();
                }
                ctx.setLineDash([]);
            }

            ctx.restore();
        }

        // Live preview
        if (currentElement.current) {
            const el = currentElement.current;
            ctx.save();
            ctx.strokeStyle = "#3b82f6"; ctx.lineWidth = 1.5 / zoom;
            ctx.setLineDash([6 / zoom, 3 / zoom]); ctx.lineCap = "round";

            if (el.type === "line") {
                ctx.beginPath(); ctx.moveTo(el.x, el.y); ctx.lineTo(el.x2!, el.y2!); ctx.stroke();
            } else if (el.type === "rect") {
                ctx.strokeRect(el.x, el.y, el.width!, el.height!);
            } else if (el.type === "circle") {
                ctx.beginPath(); ctx.arc(el.x, el.y, el.radius!, 0, Math.PI * 2); ctx.stroke();
            } else if (el.type === "wire") {
                ctx.setLineDash([]); ctx.strokeStyle = "#1a1a1a";
                if (el.points && el.points.length >= 2) {
                    ctx.beginPath(); ctx.moveTo(el.points[0].x, el.points[0].y);
                    for (let i = 1; i < el.points.length; i++) ctx.lineTo(el.points[i].x, el.points[i].y);
                    ctx.stroke();
                }
            }
            ctx.restore();
        }

        ctx.restore();
    }, [elements, pan, zoom, showGrid, selectedIds]);

    useEffect(() => {
        const container = containerRef.current;
        const canvas = canvasRef.current;
        if (!container || !canvas) return;

        const ro = new ResizeObserver(() => {
            canvas.width = container.clientWidth;
            canvas.height = container.clientHeight;
        });
        ro.observe(container);
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        return () => ro.disconnect();
    }, []);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === "Delete" || e.key === "Backspace") deleteSelected();
            if ((e.ctrlKey || e.metaKey) && e.key === "z") { e.preventDefault(); undo(); }
            if ((e.ctrlKey || e.metaKey) && e.key === "y") { e.preventDefault(); redo(); }
            if (e.key === "v") setTool("select");
            if (e.key === "h") setTool("pan");
            if (e.key === "l") setTool("line");
            if (e.key === "r") setTool("rect");
            if (e.key === "c") setTool("circle");
            if (e.key === "t") setTool("text");
            if (e.key === "w") setTool("connect");
            if (e.key === "Escape") { setSelectedIds(new Set()); wirePoints.current = []; currentElement.current = null; }
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, [deleteSelected, undo, redo]);

    const getPos = (e: React.MouseEvent) => {
        const world = toWorld(e.clientX, e.clientY);
        return { x: snapToGrid(world.x, GRID), y: snapToGrid(world.y, GRID) };
    };

    const onMouseDown = (e: React.MouseEvent) => {
        if (e.button !== 0 && e.button !== 1) return;
        const pos = getPos(e);

        if (tool === "pan" || e.button === 1) {
            isPanning.current = true;
            panStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
            return;
        }

        if (tool === "select") {
            const hitId = [...elements].reverse().find(el => {
                if (el.type === "line") {
                    const dx = el.x2! - el.x, dy = el.y2! - el.y; const len = Math.sqrt(dx * dx + dy * dy);
                    if (len === 0) return false;
                    const t = ((pos.x - el.x) * dx + (pos.y - el.y) * dy) / (len * len);
                    const clamped = Math.max(0, Math.min(1, t));
                    const nearX = el.x + clamped * dx - pos.x, nearY = el.y + clamped * dy - pos.y;
                    return Math.sqrt(nearX * nearX + nearY * nearY) < 8 / zoom;
                } else if (el.type === "rect" || el.type === "ic_block") {
                    const bw = el.type === "ic_block" ? 100 : el.width!;
                    const bh = el.type === "ic_block" ? 140 : el.height!;
                    const ex = el.type === "ic_block" ? el.x - bw/2 : el.x;
                    const ey = el.type === "ic_block" ? el.y - bh/2 : el.y;
                    return pos.x >= ex && pos.x <= ex + bw && pos.y >= ey && pos.y <= ey + bh;
                } else if (el.type === "circle") {
                    const dx = pos.x - el.x, dy = pos.y - el.y;
                    return Math.sqrt(dx * dx + dy * dy) <= (el.radius! + 8 / zoom);
                } else if (el.type === "component") {
                    return Math.abs(pos.x - el.x) < 35 && Math.abs(pos.y - el.y) < 20;
                }
                return false;
            })?.id;

            if (hitId) {
                if (e.shiftKey) {
                    setSelectedIds(prev => { const next = new Set(prev); next.has(hitId) ? next.delete(hitId) : next.add(hitId); return next; });
                } else { setSelectedIds(new Set([hitId])); }
            } else { setSelectedIds(new Set()); }
            return;
        }

        if (tool === "text") {
            const label = prompt("Enter text label:");
            if (!label) return;
            pushHistory([...elements, { id: generateId(), type: "text", x: pos.x, y: pos.y, text: label, color: STROKE, strokeWidth: 1 }]);
            return;
        }

        if (tool === "connect") {
            wirePoints.current = [...wirePoints.current, pos];
            currentElement.current = { id: generateId(), type: "wire", x: pos.x, y: pos.y, color: STROKE, strokeWidth: 1.5, points: [...wirePoints.current] };
            return;
        }

        if (tool === "component") {
            pushHistory([...elements, { id: generateId(), type: "component", x: pos.x, y: pos.y, componentType: selectedComponent, color: STROKE, strokeWidth: 1.5 }]);
            return;
        }

        isDrawing.current = true;
        startPoint.current = pos;
        if (tool === "line") currentElement.current = { id: generateId(), type: "line", x: pos.x, y: pos.y, x2: pos.x, y2: pos.y, color: STROKE, strokeWidth: 1.5 };
        else if (tool === "rect") currentElement.current = { id: generateId(), type: "rect", x: pos.x, y: pos.y, width: 0, height: 0, color: STROKE, strokeWidth: 1.5 };
        else if (tool === "circle") currentElement.current = { id: generateId(), type: "circle", x: pos.x, y: pos.y, radius: 0, color: STROKE, strokeWidth: 1.5 };
    };

    const onMouseMove = (e: React.MouseEvent) => {
        const pos = getPos(e);
        if (isPanning.current) { setPan({ x: e.clientX - panStart.current.x, y: e.clientY - panStart.current.y }); return; }
        if (!isDrawing.current && tool !== "connect") return;

        if (tool === "connect" && currentElement.current && wirePoints.current.length > 0) {
            currentElement.current = { ...currentElement.current, points: [...wirePoints.current, pos] };
            setElements([...elements]); // Force preview re-render
            return;
        }

        if (!currentElement.current) return;
        if (tool === "line") currentElement.current = { ...currentElement.current, x2: pos.x, y2: pos.y };
        else if (tool === "rect") currentElement.current = { ...currentElement.current, width: pos.x - startPoint.current.x, height: pos.y - startPoint.current.y };
        else if (tool === "circle") {
            const dx = pos.x - startPoint.current.x, dy = pos.y - startPoint.current.y;
            currentElement.current = { ...currentElement.current, radius: Math.sqrt(dx * dx + dy * dy) };
        }
        setElements([...elements]);
    };

    const onMouseUp = (e: React.MouseEvent) => {
        if (isPanning.current) { isPanning.current = false; return; }
        if (!isDrawing.current) return;
        isDrawing.current = false;

        if (currentElement.current) {
            const el = currentElement.current;
            let valid = true;
            if (el.type === "line" && Math.abs(el.x2! - el.x) < 2 && Math.abs(el.y2! - el.y) < 2) valid = false;
            if (el.type === "rect" && Math.abs(el.width!) < 4 && Math.abs(el.height!) < 4) valid = false;
            if (el.type === "circle" && el.radius! < 4) valid = false;
            if (valid) pushHistory([...elements, el]);
            currentElement.current = null;
        }
    };

    const onDoubleClick = (e: React.MouseEvent) => {
        if (tool === "connect" && wirePoints.current.length > 0) {
            pushHistory([...elements, { id: generateId(), type: "wire", x: wirePoints.current[0].x, y: wirePoints.current[0].y, color: STROKE, strokeWidth: 1.5, points: wirePoints.current }]);
            wirePoints.current = [];
            currentElement.current = null;
        }
    };

    const onWheel = (e: React.WheelEvent) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.1 : 0.9;
        const rect = canvasRef.current!.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        setZoom(prev => {
            const newZoom = Math.max(0.2, Math.min(5, prev * factor));
            setPan(p => ({ x: mouseX - (mouseX - p.x) * (newZoom / prev), y: mouseY - (mouseY - p.y) * (newZoom / prev) }));
            return newZoom;
        });
    };

    const handleGenerate = () => {
        if (!designData) return;
        if (elements.length > 0 && !fallbackUsed) {
            setShowConfirmRegen(true);
        } else {
            generate(designData, currentQuery || "");
        }
    };

    const exportSVG = () => {
        const svg = `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="1500" style="background:#fff">\n</svg>`;
        const blob = new Blob([svg], { type: "image/svg+xml" });
        const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "schematic.svg"; a.click();
    };

    const getCursor = () => {
        if (isPanning.current) return "grabbing";
        if (tool === "pan") return "grab";
        if (tool === "select") return "default";
        return "crosshair";
    };

    return (
        <div className="w-full h-full flex flex-col bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden text-gray-800">
            {/* Toolbar */}
            <div className="flex items-center gap-1 p-2 border-b border-gray-100 bg-gray-50/50">
                <div className="flex items-center bg-white border border-gray-200 rounded-lg p-1 shadow-sm">
                    <button onClick={() => setTool("select")} className={`p-1.5 rounded-md transition-all ${tool === "select" ? "bg-blue-100 text-blue-700" : "hover:bg-gray-100 text-gray-600"}`} title="Select (V)"><MousePointer2 className="w-4 h-4" /></button>
                    <button onClick={() => setTool("pan")} className={`p-1.5 rounded-md transition-all ${tool === "pan" ? "bg-blue-100 text-blue-700" : "hover:bg-gray-100 text-gray-600"}`} title="Pan (H)"><Hand className="w-4 h-4" /></button>
                </div>
                <div className="h-6 w-px bg-gray-200 mx-1" />
                <div className="flex items-center bg-white border border-gray-200 rounded-lg p-1 shadow-sm">
                    <button onClick={() => setTool("line")} className={`p-1.5 rounded-md transition-all ${tool === "line" ? "bg-blue-100 text-blue-700" : "hover:bg-gray-100 text-gray-600"}`} title="Line (L)"><Minus className="w-4 h-4" /></button>
                    <button onClick={() => setTool("rect")} className={`p-1.5 rounded-md transition-all ${tool === "rect" ? "bg-blue-100 text-blue-700" : "hover:bg-gray-100 text-gray-600"}`} title="Rectangle (R)"><Square className="w-4 h-4" /></button>
                    <button onClick={() => setTool("circle")} className={`p-1.5 rounded-md transition-all ${tool === "circle" ? "bg-blue-100 text-blue-700" : "hover:bg-gray-100 text-gray-600"}`} title="Circle (C)"><Circle className="w-4 h-4" /></button>
                    <button onClick={() => setTool("text")} className={`p-1.5 rounded-md transition-all ${tool === "text" ? "bg-blue-100 text-blue-700" : "hover:bg-gray-100 text-gray-600"}`} title="Text (T)"><Type className="w-4 h-4" /></button>
                    <button onClick={() => setTool("connect")} className={`p-1.5 rounded-md transition-all ${tool === "connect" ? "bg-blue-100 text-blue-700" : "hover:bg-gray-100 text-gray-600"}`} title="Wire Connect (W)"><GitMerge className="w-4 h-4" /></button>
                </div>
                <div className="h-6 w-px bg-gray-200 mx-1" />
                <div className="relative">
                    <button onClick={() => setShowComponentMenu(!showComponentMenu)} className={`flex items-center gap-1 p-1.5 rounded-md border shadow-sm transition-all ${tool === "component" ? "bg-blue-100 border-blue-200 text-blue-700" : "bg-white border-gray-200 hover:bg-gray-50 text-gray-700"}`}>
                        <div className="flex items-center gap-1.5 px-1">
                            {(() => { const Icon: any = COMPONENT_SYMBOLS[selectedComponent]?.icon || Cpu; return <Icon className="w-4 h-4" />; })()}
                            <span className="text-xs font-medium pr-1">{COMPONENT_SYMBOLS[selectedComponent]?.label}</span>
                        </div>
                        <ChevronDown className="w-3 h-3 text-gray-400" />
                    </button>
                    {showComponentMenu && (
                        <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-xl py-1 z-50">
                            {Object.entries(COMPONENT_SYMBOLS).map(([key, sym]) => {
                                const Icon: any = sym.icon;
                                return (
                                <button key={key} onClick={() => { setSelectedComponent(key); setTool("component"); setShowComponentMenu(false); }} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition-colors">
                                    <Icon className="w-4 h-4" /> {sym.label}
                                </button>
                                );
                            })}
                        </div>
                    )}
                </div>

                <div className="flex-1 flex justify-center">
                    <button 
                        onClick={handleGenerate}
                        disabled={!designData || isGenerating}
                        className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-4 py-1.5 rounded-full text-sm font-medium shadow-md transition-all disabled:opacity-50"
                    >
                        {isGenerating ? <RotateCcw className="w-4 h-4 animate-spin" /> : <BrainCircuit className="w-4 h-4" />}
                        {elements.length > 0 ? "Regenerate AI Schematic" : "Generate AI Schematic"}
                    </button>
                </div>

                <div className="flex items-center bg-white border border-gray-200 rounded-lg p-1 shadow-sm">
                    <button onClick={undo} disabled={historyIdx <= 0} className="p-1.5 rounded-md text-gray-600 hover:bg-gray-100 disabled:opacity-30"><Undo2 className="w-4 h-4" /></button>
                    <button onClick={redo} disabled={historyIdx >= history.length - 1} className="p-1.5 rounded-md text-gray-600 hover:bg-gray-100 disabled:opacity-30"><Redo2 className="w-4 h-4" /></button>
                </div>
                <div className="h-6 w-px bg-gray-200 mx-1" />
                <button onClick={() => setShowGrid(!showGrid)} className={`p-2 rounded-lg transition-all ${showGrid ? "text-blue-600 bg-blue-50" : "text-gray-400 hover:bg-gray-100"}`}><Grid3X3 className="w-4 h-4" /></button>
                <button onClick={deleteSelected} disabled={selectedIds.size === 0} className="p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-30"><Trash2 className="w-4 h-4" /></button>
                <button onClick={exportSVG} className="p-2 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100"><Download className="w-4 h-4" /></button>
            </div>

            {/* Canvas area */}
            <div ref={containerRef} className="flex-1 relative overflow-hidden bg-[#fafafa]" style={{ cursor: getCursor() }}>
                <canvas
                    ref={canvasRef}
                    className="absolute inset-0 w-full h-full"
                    onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp}
                    onDoubleClick={onDoubleClick} onWheel={onWheel} onContextMenu={e => e.preventDefault()}
                />

                {/* AI Loading Overlay */}
                {isGenerating && (
                    <div className="absolute inset-0 bg-white/70 backdrop-blur-sm flex flex-col items-center justify-center z-40">
                        <div className="bg-white border border-indigo-100 shadow-2xl rounded-2xl p-6 w-80 max-w-full">
                            <div className="flex items-center gap-3 mb-4">
                                <BrainCircuit className="w-6 h-6 text-indigo-600 animate-pulse" />
                                <h3 className="font-semibold text-gray-800">AI Synthesis in Progress</h3>
                            </div>
                            <div className="space-y-3 font-mono text-sm">
                                <div className="flex items-center gap-2 text-gray-600">
                                    <CheckCircle className="w-4 h-4 text-green-500" /> Reading design data
                                </div>
                                <div className="flex items-center gap-2 text-indigo-600 font-medium">
                                    <RotateCcw className="w-4 h-4 animate-spin" /> {generatingStep}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Confirm Regenerate Dialog */}
                {showConfirmRegen && (
                    <div className="absolute inset-0 bg-black/20 flex items-center justify-center z-50">
                        <div className="bg-white p-6 rounded-xl shadow-xl max-w-md">
                            <h3 className="font-bold text-lg text-gray-900 mb-2">Overwrite canvas?</h3>
                            <p className="text-gray-600 text-sm mb-6">You have elements on the canvas. Regenerating the AI schematic will replace your current design. This action can be undone.</p>
                            <div className="flex gap-3 justify-end">
                                <button onClick={() => setShowConfirmRegen(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
                                <button onClick={() => { setShowConfirmRegen(false); regenerate(designData, currentQuery || "", true); }} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Regenerate</button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Side Panels */}
                <div className="absolute top-4 right-4 flex flex-col gap-2 w-64 z-30 pointer-events-none">
                    {/* Assumptions Panel */}
                    {assumptions.length > 0 && (
                        <div className="bg-white border border-blue-100 shadow-lg rounded-xl p-3 pointer-events-auto">
                            <div className="flex items-center justify-between mb-2 cursor-pointer" onClick={() => setShowAssumptions(!showAssumptions)}>
                                <h4 className="text-xs font-bold text-blue-800 uppercase tracking-wide flex items-center gap-1.5"><BrainCircuit className="w-3.5 h-3.5"/> Engine Assumptions</h4>
                                <ChevronDown className={`w-4 h-4 text-blue-400 transition-transform ${showAssumptions ? 'rotate-180' : ''}`} />
                            </div>
                            {showAssumptions && (
                                <ul className="space-y-1.5">
                                    {assumptions.map((a, i) => (
                                        <li key={i} className="text-[11px] text-gray-600 leading-tight flex gap-1.5"><div className="w-1 h-1 rounded-full bg-blue-400 mt-1 shrink-0" />{a}</li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    )}
                    
                    {/* ERC Panel */}
                    {showErcPanel && ercIssues.length > 0 && (
                        <div className="bg-white border border-red-100 shadow-lg rounded-xl p-3 pointer-events-auto">
                            <div className="flex items-center justify-between mb-2 cursor-pointer" onClick={() => setShowErcPanel(false)}>
                                <h4 className="text-xs font-bold text-red-800 uppercase tracking-wide flex items-center gap-1.5"><AlertCircle className="w-3.5 h-3.5"/> ERC Violations</h4>
                                <ChevronDown className="w-4 h-4 text-red-400 rotate-180" />
                            </div>
                            <ul className="space-y-2 max-h-48 overflow-y-auto">
                                {ercIssues.map((issue, i) => (
                                    <li key={i} className="text-[11px] leading-tight flex gap-1.5 p-1.5 bg-red-50 rounded">
                                        {issue.severity === 'error' ? <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0" /> : <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />}
                                        <span className="text-gray-800">{issue.message}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
                
                {/* Empty state */}
                {elements.length === 0 && !isGenerating && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <div className="flex flex-col items-center gap-3 opacity-40">
                            <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center"><BrainCircuit className="w-8 h-8 text-blue-500" /></div>
                            <p className="text-gray-500 text-sm font-medium">Ready for AI Synthesis</p>
                            <p className="text-gray-400 text-xs">Click Generate to build schematic from your design</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Status bar */}
            <div className="flex items-center gap-4 px-4 py-2 border-t border-gray-100 bg-gray-50 text-xs text-gray-500 font-mono">
                {fallbackUsed && <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full font-sans font-medium flex items-center gap-1"><AlertTriangle className="w-3 h-3"/> Limited Mode</span>}
                
                <button onClick={() => setShowErcPanel(!showErcPanel)} className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full transition-colors ${ercIssues.length > 0 ? (ercIssues.some(i => i.severity === 'error') ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-amber-100 text-amber-700 hover:bg-amber-200') : 'bg-green-100 text-green-700'}`}>
                    {ercIssues.length === 0 ? <CheckCircle className="w-3.5 h-3.5" /> : (ercIssues.some(i => i.severity === 'error') ? <AlertCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />)}
                    ERC: {ercIssues.length} issues
                </button>

                {powerBudget && (
                    <div className="flex items-center gap-1.5 px-2 py-0.5 bg-gray-200 text-gray-700 rounded-full">
                        <Battery className="w-3.5 h-3.5" /> {powerBudget.total_mA}mA max
                    </div>
                )}
                
                {confidence && (
                    <div className="flex items-center gap-1.5 text-indigo-600 font-medium">
                        Confidence: {confidence.overall}%
                    </div>
                )}

                <div className="flex-1" />
                <span>Grid: {GRID}px</span>
                <span>Zoom: {Math.round(zoom * 100)}%</span>
            </div>
        </div>
    );
}
