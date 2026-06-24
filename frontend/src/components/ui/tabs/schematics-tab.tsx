"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
    MousePointer2,
    Hand,
    Type,
    Minus,
    Square,
    Circle,
    GitMerge,
    Undo2,
    Redo2,
    ZoomIn,
    ZoomOut,
    Trash2,
    Download,
    Grid3X3,
    Cpu,
    Zap,
    ToggleLeft,
    Radio,
    Activity,
    ChevronDown,
    Plus,
} from "lucide-react";

type Tool = "select" | "pan" | "text" | "line" | "rect" | "circle" | "connect" | "component";

interface Point {
    x: number;
    y: number;
}

interface SchematicElement {
    id: string;
    type: "line" | "rect" | "circle" | "text" | "wire" | "component";
    x: number;
    y: number;
    x2?: number;
    y2?: number;
    width?: number;
    height?: number;
    radius?: number;
    text?: string;
    color: string;
    strokeWidth: number;
    componentType?: string;
    selected?: boolean;
    points?: Point[];
}

const COMPONENT_SYMBOLS: Record<string, { label: string; icon: React.ElementType; draw: (ctx: CanvasRenderingContext2D, x: number, y: number, scale: number) => void }> = {
    resistor: {
        label: "Resistor",
        icon: Activity,
        draw: (ctx, x, y, s) => {
            ctx.beginPath();
            ctx.moveTo(x - 30 * s, y);
            ctx.lineTo(x - 15 * s, y);
            ctx.rect(x - 15 * s, y - 6 * s, 30 * s, 12 * s);
            ctx.moveTo(x + 15 * s, y);
            ctx.lineTo(x + 30 * s, y);
            ctx.stroke();
        }
    },
    capacitor: {
        label: "Capacitor",
        icon: Zap,
        draw: (ctx, x, y, s) => {
            ctx.beginPath();
            ctx.moveTo(x - 30 * s, y);
            ctx.lineTo(x - 4 * s, y);
            ctx.moveTo(x - 4 * s, y - 12 * s);
            ctx.lineTo(x - 4 * s, y + 12 * s);
            ctx.moveTo(x + 4 * s, y - 12 * s);
            ctx.lineTo(x + 4 * s, y + 12 * s);
            ctx.moveTo(x + 4 * s, y);
            ctx.lineTo(x + 30 * s, y);
            ctx.stroke();
        }
    },
    ic: {
        label: "IC / MCU",
        icon: Cpu,
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
        label: "LED",
        icon: Radio,
        draw: (ctx, x, y, s) => {
            ctx.beginPath();
            ctx.moveTo(x - 30 * s, y);
            ctx.lineTo(x - 10 * s, y);
            ctx.moveTo(x - 10 * s, y - 12 * s);
            ctx.lineTo(x + 10 * s, y);
            ctx.lineTo(x - 10 * s, y + 12 * s);
            ctx.closePath();
            ctx.moveTo(x + 10 * s, y - 12 * s);
            ctx.lineTo(x + 10 * s, y + 12 * s);
            ctx.moveTo(x + 10 * s, y);
            ctx.lineTo(x + 30 * s, y);
            ctx.stroke();
        }
    },
    switch: {
        label: "Switch",
        icon: ToggleLeft,
        draw: (ctx, x, y, s) => {
            ctx.beginPath();
            ctx.moveTo(x - 30 * s, y);
            ctx.lineTo(x - 10 * s, y);
            ctx.arc(x - 10 * s, y, 3 * s, 0, Math.PI * 2);
            ctx.moveTo(x - 8 * s, y);
            ctx.lineTo(x + 10 * s, y - 12 * s);
            ctx.arc(x + 10 * s, y, 3 * s, 0, Math.PI * 2);
            ctx.moveTo(x + 10 * s, y);
            ctx.lineTo(x + 30 * s, y);
            ctx.stroke();
        }
    }
};

function generateId() {
    return Math.random().toString(36).slice(2, 10);
}

function snapToGrid(val: number, gridSize: number) {
    return Math.round(val / gridSize) * gridSize;
}

export function SchematicsTab() {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const [tool, setTool] = useState<Tool>("select");
    const [elements, setElements] = useState<SchematicElement[]>([]);
    const [history, setHistory] = useState<SchematicElement[][]>([[]]);
    const [historyIdx, setHistoryIdx] = useState(0);
    const [zoom, setZoom] = useState(1);
    const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
    const [showGrid, setShowGrid] = useState(true);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [showComponentMenu, setShowComponentMenu] = useState(false);
    const [selectedComponent, setSelectedComponent] = useState<string>("resistor");

    // Drawing state (refs to avoid stale closures in canvas event handlers)
    const isDrawing = useRef(false);
    const isPanning = useRef(false);
    const startPoint = useRef<Point>({ x: 0, y: 0 });
    const currentElement = useRef<SchematicElement | null>(null);
    const lastPan = useRef<Point>({ x: 0, y: 0 });
    const panStart = useRef<Point>({ x: 0, y: 0 });
    const wirePoints = useRef<Point[]>([]);

    const GRID = 20;
    const STROKE = "#1a1a1a";

    // Convert screen coords to canvas/world coords
    const toWorld = useCallback((screenX: number, screenY: number): Point => {
        const canvas = canvasRef.current!;
        const rect = canvas.getBoundingClientRect();
        return {
            x: (screenX - rect.left - pan.x) / zoom,
            y: (screenY - rect.top - pan.y) / zoom,
        };
    }, [pan, zoom]);

    // Push to undo history
    const pushHistory = useCallback((els: SchematicElement[]) => {
        setHistory(prev => {
            const truncated = prev.slice(0, historyIdx + 1);
            return [...truncated, els];
        });
        setHistoryIdx(prev => prev + 1);
    }, [historyIdx]);

    const undo = useCallback(() => {
        if (historyIdx <= 0) return;
        const newIdx = historyIdx - 1;
        setHistoryIdx(newIdx);
        setElements(history[newIdx]);
    }, [historyIdx, history]);

    const redo = useCallback(() => {
        if (historyIdx >= history.length - 1) return;
        const newIdx = historyIdx + 1;
        setHistoryIdx(newIdx);
        setElements(history[newIdx]);
    }, [historyIdx, history]);

    const deleteSelected = useCallback(() => {
        if (selectedIds.size === 0) return;
        const next = elements.filter(e => !selectedIds.has(e.id));
        setElements(next);
        pushHistory(next);
        setSelectedIds(new Set());
    }, [elements, selectedIds, pushHistory]);

    // Draw everything on canvas
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d")!;
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        // Background
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, w, h);

        ctx.save();
        ctx.translate(pan.x, pan.y);
        ctx.scale(zoom, zoom);

        // Dot grid
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
            ctx.strokeStyle = selectedIds.has(el.id) ? "#3b82f6" : el.color;
            ctx.fillStyle = selectedIds.has(el.id) ? "#3b82f650" : "transparent";
            ctx.lineWidth = el.strokeWidth / zoom;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";

            if (el.type === "line") {
                ctx.beginPath();
                ctx.moveTo(el.x, el.y);
                ctx.lineTo(el.x2!, el.y2!);
                ctx.stroke();
            } else if (el.type === "rect") {
                ctx.beginPath();
                ctx.rect(el.x, el.y, el.width!, el.height!);
                ctx.stroke();
                if (selectedIds.has(el.id)) ctx.fill();
            } else if (el.type === "circle") {
                ctx.beginPath();
                ctx.arc(el.x, el.y, el.radius!, 0, Math.PI * 2);
                ctx.stroke();
                if (selectedIds.has(el.id)) ctx.fill();
            } else if (el.type === "text") {
                ctx.fillStyle = el.color;
                ctx.font = `${14 / zoom}px 'Inter', sans-serif`;
                ctx.fillText(el.text || "", el.x, el.y);
            } else if (el.type === "wire") {
                if (el.points && el.points.length >= 2) {
                    ctx.beginPath();
                    ctx.moveTo(el.points[0].x, el.points[0].y);
                    for (let i = 1; i < el.points.length; i++) {
                        ctx.lineTo(el.points[i].x, el.points[i].y);
                    }
                    ctx.stroke();

                    // Draw junction dots
                    for (const pt of el.points) {
                        ctx.beginPath();
                        ctx.arc(pt.x, pt.y, 2.5 / zoom, 0, Math.PI * 2);
                        ctx.fillStyle = el.color;
                        ctx.fill();
                    }
                }
            } else if (el.type === "component") {
                ctx.strokeStyle = selectedIds.has(el.id) ? "#3b82f6" : STROKE;
                ctx.lineWidth = 1.5 / zoom;
                const sym = COMPONENT_SYMBOLS[el.componentType || "resistor"];
                if (sym) {
                    sym.draw(ctx, el.x, el.y, 1 / zoom * zoom); // draw at world scale
                }
            }

            // Selection bounding box
            if (selectedIds.has(el.id) && el.type !== "text" && el.type !== "component") {
                ctx.setLineDash([4 / zoom, 4 / zoom]);
                ctx.strokeStyle = "#3b82f6";
                ctx.lineWidth = 1 / zoom;
                const pad = 6 / zoom;
                if (el.type === "line") {
                    const minX = Math.min(el.x, el.x2!) - pad;
                    const minY = Math.min(el.y, el.y2!) - pad;
                    const maxX = Math.max(el.x, el.x2!) + pad;
                    const maxY = Math.max(el.y, el.y2!) + pad;
                    ctx.strokeRect(minX, minY, maxX - minX, maxY - minY);
                } else if (el.type === "rect") {
                    ctx.strokeRect(el.x - pad, el.y - pad, (el.width || 0) + pad * 2, (el.height || 0) + pad * 2);
                } else if (el.type === "circle") {
                    ctx.beginPath();
                    ctx.arc(el.x, el.y, (el.radius || 0) + pad, 0, Math.PI * 2);
                    ctx.stroke();
                }
                ctx.setLineDash([]);
            }

            ctx.restore();
        }

        // Live preview of currently drawn element
        if (currentElement.current) {
            const el = currentElement.current;
            ctx.save();
            ctx.strokeStyle = "#3b82f6";
            ctx.lineWidth = 1.5 / zoom;
            ctx.setLineDash([6 / zoom, 3 / zoom]);
            ctx.lineCap = "round";

            if (el.type === "line") {
                ctx.beginPath();
                ctx.moveTo(el.x, el.y);
                ctx.lineTo(el.x2!, el.y2!);
                ctx.stroke();
            } else if (el.type === "rect") {
                ctx.strokeRect(el.x, el.y, el.width!, el.height!);
            } else if (el.type === "circle") {
                ctx.beginPath();
                ctx.arc(el.x, el.y, el.radius!, 0, Math.PI * 2);
                ctx.stroke();
            } else if (el.type === "wire") {
                ctx.setLineDash([]);
                ctx.strokeStyle = "#1a1a1a";
                if (el.points && el.points.length >= 2) {
                    ctx.beginPath();
                    ctx.moveTo(el.points[0].x, el.points[0].y);
                    for (let i = 1; i < el.points.length; i++) {
                        ctx.lineTo(el.points[i].x, el.points[i].y);
                    }
                    ctx.stroke();
                }
            }

            ctx.restore();
        }

        ctx.restore();
    }, [elements, pan, zoom, showGrid, selectedIds]);

    // Resize canvas
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

    // Keyboard shortcuts
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

    // Mouse events
    const getPos = (e: React.MouseEvent) => {
        const world = toWorld(e.clientX, e.clientY);
        return { x: snapToGrid(world.x, GRID), y: snapToGrid(world.y, GRID) };
    };

    const onMouseDown = (e: React.MouseEvent) => {
        if (e.button !== 0) return;
        const pos = getPos(e);

        if (tool === "pan" || e.button === 1) {
            isPanning.current = true;
            panStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
            return;
        }

        if (tool === "select") {
            // Hit-test elements (reverse order for top-first)
            const hitId = [...elements].reverse().find(el => {
                if (el.type === "line") {
                    const dx = el.x2! - el.x, dy = el.y2! - el.y;
                    const len = Math.sqrt(dx * dx + dy * dy);
                    if (len === 0) return false;
                    const t = ((pos.x - el.x) * dx + (pos.y - el.y) * dy) / (len * len);
                    const clamped = Math.max(0, Math.min(1, t));
                    const nearX = el.x + clamped * dx - pos.x;
                    const nearY = el.y + clamped * dy - pos.y;
                    return Math.sqrt(nearX * nearX + nearY * nearY) < 8 / zoom;
                } else if (el.type === "rect") {
                    return pos.x >= el.x && pos.x <= el.x + el.width! && pos.y >= el.y && pos.y <= el.y + el.height!;
                } else if (el.type === "circle") {
                    const dx = pos.x - el.x, dy = pos.y - el.y;
                    return Math.sqrt(dx * dx + dy * dy) <= (el.radius! + 8 / zoom);
                } else if (el.type === "text") {
                    return pos.x >= el.x - 2 && pos.x <= el.x + 100 && pos.y >= el.y - 14 && pos.y <= el.y + 4;
                } else if (el.type === "component") {
                    return Math.abs(pos.x - el.x) < 35 && Math.abs(pos.y - el.y) < 20;
                }
                return false;
            })?.id;

            if (hitId) {
                if (e.shiftKey) {
                    setSelectedIds(prev => {
                        const next = new Set(prev);
                        next.has(hitId) ? next.delete(hitId) : next.add(hitId);
                        return next;
                    });
                } else {
                    setSelectedIds(new Set([hitId]));
                }
            } else {
                setSelectedIds(new Set());
            }
            return;
        }

        if (tool === "text") {
            const label = prompt("Enter text label:");
            if (!label) return;
            const newEl: SchematicElement = { id: generateId(), type: "text", x: pos.x, y: pos.y, text: label, color: STROKE, strokeWidth: 1 };
            const next = [...elements, newEl];
            setElements(next);
            pushHistory(next);
            return;
        }

        if (tool === "connect") {
            wirePoints.current = [...wirePoints.current, pos];
            currentElement.current = { id: generateId(), type: "wire", x: pos.x, y: pos.y, color: STROKE, strokeWidth: 1.5, points: [...wirePoints.current] };
            return;
        }

        if (tool === "component") {
            const newEl: SchematicElement = {
                id: generateId(), type: "component", x: pos.x, y: pos.y,
                componentType: selectedComponent, color: STROKE, strokeWidth: 1.5
            };
            const next = [...elements, newEl];
            setElements(next);
            pushHistory(next);
            return;
        }

        isDrawing.current = true;
        startPoint.current = pos;

        if (tool === "line") {
            currentElement.current = { id: generateId(), type: "line", x: pos.x, y: pos.y, x2: pos.x, y2: pos.y, color: STROKE, strokeWidth: 1.5 };
        } else if (tool === "rect") {
            currentElement.current = { id: generateId(), type: "rect", x: pos.x, y: pos.y, width: 0, height: 0, color: STROKE, strokeWidth: 1.5 };
        } else if (tool === "circle") {
            currentElement.current = { id: generateId(), type: "circle", x: pos.x, y: pos.y, radius: 0, color: STROKE, strokeWidth: 1.5 };
        }
    };

    const onMouseMove = (e: React.MouseEvent) => {
        const pos = getPos(e);

        if (isPanning.current) {
            setPan({ x: e.clientX - panStart.current.x, y: e.clientY - panStart.current.y });
            return;
        }

        if (!isDrawing.current && tool !== "connect") return;

        if (tool === "connect" && currentElement.current && wirePoints.current.length > 0) {
            const pts = [...wirePoints.current, pos];
            currentElement.current = { ...currentElement.current, points: pts };
            // Force re-render
            setElements(prev => [...prev]);
            return;
        }

        if (!currentElement.current) return;

        if (tool === "line") {
            currentElement.current = { ...currentElement.current, x2: pos.x, y2: pos.y };
        } else if (tool === "rect") {
            currentElement.current = {
                ...currentElement.current,
                width: pos.x - startPoint.current.x,
                height: pos.y - startPoint.current.y
            };
        } else if (tool === "circle") {
            const dx = pos.x - startPoint.current.x, dy = pos.y - startPoint.current.y;
            currentElement.current = { ...currentElement.current, radius: Math.sqrt(dx * dx + dy * dy) };
        }

        // Force re-render for live preview
        setElements(prev => [...prev]);
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

            if (valid) {
                const next = [...elements, el];
                setElements(next);
                pushHistory(next);
            }
            currentElement.current = null;
        }
    };

    const onDoubleClick = (e: React.MouseEvent) => {
        // Finish wire on double click
        if (tool === "connect" && wirePoints.current.length > 0) {
            const el: SchematicElement = {
                id: generateId(), type: "wire", x: wirePoints.current[0].x, y: wirePoints.current[0].y,
                color: STROKE, strokeWidth: 1.5, points: wirePoints.current
            };
            const next = [...elements, el];
            setElements(next);
            pushHistory(next);
            wirePoints.current = [];
            currentElement.current = null;
        }
    };

    const onWheel = (e: React.WheelEvent) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.1 : 0.9;
        const canvas = canvasRef.current!;
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        setZoom(prev => {
            const newZoom = Math.max(0.2, Math.min(5, prev * factor));
            setPan(p => ({
                x: mouseX - (mouseX - p.x) * (newZoom / prev),
                y: mouseY - (mouseY - p.y) * (newZoom / prev),
            }));
            return newZoom;
        });
    };

    const exportSVG = () => {
        // Basic SVG export
        const lines = elements.map(el => {
            if (el.type === "line") return `<line x1="${el.x}" y1="${el.y}" x2="${el.x2}" y2="${el.y2}" stroke="${el.color}" stroke-width="${el.strokeWidth}" stroke-linecap="round"/>`;
            if (el.type === "rect") return `<rect x="${el.x}" y="${el.y}" width="${el.width}" height="${el.height}" fill="none" stroke="${el.color}" stroke-width="${el.strokeWidth}"/>`;
            if (el.type === "circle") return `<circle cx="${el.x}" cy="${el.y}" r="${el.radius}" fill="none" stroke="${el.color}" stroke-width="${el.strokeWidth}"/>`;
            if (el.type === "text") return `<text x="${el.x}" y="${el.y}" font-family="monospace" font-size="14" fill="${el.color}">${el.text}</text>`;
            return "";
        }).join("\n");

        const svg = `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="1500" style="background:#fff">\n${lines}\n</svg>`;
        const blob = new Blob([svg], { type: "image/svg+xml" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "schematic.svg";
        a.click();
    };

    const zoomIn = () => setZoom(z => Math.min(5, parseFloat((z * 1.2).toFixed(2))));
    const zoomOut = () => setZoom(z => Math.max(0.2, parseFloat((z / 1.2).toFixed(2))));

    const TOOLS: { id: Tool; icon: React.ElementType; label: string; key: string }[] = [
        { id: "select", icon: MousePointer2, label: "Select (V)", key: "V" },
        { id: "pan", icon: Hand, label: "Pan (H)", key: "H" },
        { id: "text", icon: Type, label: "Text (T)", key: "T" },
        { id: "line", icon: Minus, label: "Line (L)", key: "L" },
        { id: "rect", icon: Square, label: "Rectangle (R)", key: "R" },
        { id: "circle", icon: Circle, label: "Circle (C)", key: "C" },
        { id: "connect", icon: GitMerge, label: "Wire (W)", key: "W" },
    ];

    const getCursor = () => {
        if (tool === "pan") return "grab";
        if (tool === "select") return "default";
        if (tool === "text") return "text";
        return "crosshair";
    };

    return (
        <div className="w-full h-full flex flex-col bg-white relative select-none">
            {/* Top Toolbar */}
            <div className="flex items-center gap-1 px-4 py-2 border-b border-gray-200 bg-white/95 backdrop-blur-sm shadow-sm z-10 flex-wrap">
                {/* Tool buttons */}
                <div className="flex items-center gap-0.5 bg-gray-100 rounded-lg p-1">
                    {TOOLS.map(t => (
                        <button
                            key={t.id}
                            onClick={() => setTool(t.id)}
                            title={t.label}
                            className={`p-2 rounded-md transition-all duration-150 ${tool === t.id
                                ? "bg-white text-gray-900 shadow-sm ring-1 ring-gray-200"
                                : "text-gray-500 hover:text-gray-800 hover:bg-white/70"
                                }`}
                        >
                            <t.icon className="w-4 h-4" />
                        </button>
                    ))}
                </div>

                {/* Component button */}
                <div className="relative">
                    <button
                        onClick={() => setShowComponentMenu(v => !v)}
                        title="Place Component"
                        className={`flex items-center gap-1 px-3 py-2 rounded-lg transition-all duration-150 text-sm font-medium ${tool === "component"
                            ? "bg-blue-600 text-white shadow"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                            }`}
                    >
                        <Cpu className="w-4 h-4" />
                        <span className="hidden sm:inline">Component</span>
                        <ChevronDown className="w-3 h-3" />
                    </button>
                    {showComponentMenu && (
                        <div className="absolute top-full left-0 mt-1 w-44 bg-white border border-gray-200 rounded-xl shadow-xl z-50 overflow-hidden">
                            {Object.entries(COMPONENT_SYMBOLS).map(([key, sym]) => (
                                <button
                                    key={key}
                                    onClick={() => {
                                        setSelectedComponent(key);
                                        setTool("component");
                                        setShowComponentMenu(false);
                                    }}
                                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition-colors"
                                >
                                    <sym.icon className="w-4 h-4" />
                                    {sym.label}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                <div className="w-px h-6 bg-gray-200 mx-1" />

                {/* Divider + Undo/Redo */}
                <button
                    onClick={undo}
                    disabled={historyIdx <= 0}
                    title="Undo (Ctrl+Z)"
                    className="p-2 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-100 disabled:opacity-30 transition-all"
                >
                    <Undo2 className="w-4 h-4" />
                </button>
                <button
                    onClick={redo}
                    disabled={historyIdx >= history.length - 1}
                    title="Redo (Ctrl+Y)"
                    className="p-2 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-100 disabled:opacity-30 transition-all"
                >
                    <Redo2 className="w-4 h-4" />
                </button>

                <div className="w-px h-6 bg-gray-200 mx-1" />

                {/* Grid toggle */}
                <button
                    onClick={() => setShowGrid(v => !v)}
                    title="Toggle Grid"
                    className={`p-2 rounded-lg transition-all ${showGrid ? "text-blue-600 bg-blue-50" : "text-gray-400 hover:bg-gray-100"}`}
                >
                    <Grid3X3 className="w-4 h-4" />
                </button>

                {/* Delete */}
                <button
                    onClick={deleteSelected}
                    disabled={selectedIds.size === 0}
                    title="Delete selected (Del)"
                    className="p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-30 transition-all"
                >
                    <Trash2 className="w-4 h-4" />
                </button>

                {/* Export */}
                <button
                    onClick={exportSVG}
                    title="Export as SVG"
                    className="p-2 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-all"
                >
                    <Download className="w-4 h-4" />
                </button>

                <div className="flex-1" />

                {/* Zoom controls */}
                <div className="flex items-center gap-1 bg-gray-100 rounded-lg px-2 py-1">
                    <button onClick={zoomOut} title="Zoom Out" className="p-1 rounded hover:bg-white transition-all text-gray-600">
                        <ZoomOut className="w-4 h-4" />
                    </button>
                    <span className="text-xs font-mono text-gray-600 w-12 text-center select-none">
                        {Math.round(zoom * 100)}%
                    </span>
                    <button onClick={zoomIn} title="Zoom In" className="p-1 rounded hover:bg-white transition-all text-gray-600">
                        <ZoomIn className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Canvas area */}
            <div
                ref={containerRef}
                className="flex-1 relative overflow-hidden"
                style={{ cursor: getCursor() }}
            >
                <canvas
                    ref={canvasRef}
                    className="absolute inset-0 w-full h-full"
                    onMouseDown={onMouseDown}
                    onMouseMove={onMouseMove}
                    onMouseUp={onMouseUp}
                    onDoubleClick={onDoubleClick}
                    onWheel={onWheel}
                    onContextMenu={e => e.preventDefault()}
                />

                {/* Tool hint */}
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 pointer-events-none">
                    <div className="bg-gray-900/70 backdrop-blur-md text-white text-xs px-3 py-1.5 rounded-full font-mono opacity-75">
                        {tool === "select" && "Click to select · Shift+Click for multi-select · Del to delete"}
                        {tool === "pan" && "Click & drag to pan · Scroll to zoom"}
                        {tool === "line" && "Click & drag to draw a line · L key"}
                        {tool === "rect" && "Click & drag to draw a rectangle · R key"}
                        {tool === "circle" && "Click & drag from center · C key"}
                        {tool === "text" && "Click to place text label · T key"}
                        {tool === "connect" && "Click to add wire points · Double-click to finish · W key"}
                        {tool === "component" && `Placing ${COMPONENT_SYMBOLS[selectedComponent]?.label} · Click to place`}
                    </div>
                </div>

                {/* Empty state prompt */}
                {elements.length === 0 && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <div className="flex flex-col items-center gap-3 opacity-40">
                            <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center">
                                <Activity className="w-8 h-8 text-gray-400" />
                            </div>
                            <p className="text-gray-400 text-sm font-medium">Start drawing your schematic</p>
                            <p className="text-gray-300 text-xs">Select a tool from the toolbar above</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Status bar */}
            <div className="flex items-center gap-4 px-4 py-1.5 border-t border-gray-100 bg-gray-50 text-xs text-gray-400 font-mono">
                <span>{elements.length} element{elements.length !== 1 ? "s" : ""}</span>
                {selectedIds.size > 0 && <span className="text-blue-500">{selectedIds.size} selected</span>}
                <div className="flex-1" />
                <span>Grid: {GRID}px</span>
                <span>Zoom: {Math.round(zoom * 100)}%</span>
                {tool === "component" && <span className="text-purple-500">Component: {COMPONENT_SYMBOLS[selectedComponent]?.label}</span>}
            </div>
        </div>
    );
}
