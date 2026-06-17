"use client";

import { useRef, useState, useCallback } from "react";
import { Plus, X, GripVertical } from "lucide-react";
import { cn } from "@/lib/utils";

export interface PlacedComponent {
  id: string;
  componentId: string;
  name: string;
  icon: string;
  x: number;
  y: number;
}

interface WorkspaceCanvasProps {
  components: PlacedComponent[];
  onDropComponent: (componentId: string, name: string, icon: string, x: number, y: number) => void;
  onMoveComponent: (id: string, x: number, y: number) => void;
  onRemoveComponent: (id: string) => void;
  zoom: number;
  pan: { x: number; y: number };
  onPanChange: (pan: { x: number; y: number }) => void;
  onZoomChange: (zoom: number) => void;
  activeTool: string;
}

export function WorkspaceCanvas({
  components,
  onDropComponent,
  onMoveComponent,
  onRemoveComponent,
  zoom,
  pan,
  onPanChange,
  onZoomChange,
  activeTool,
}: WorkspaceCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [draggingComponent, setDraggingComponent] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  const getCanvasPosition = useCallback(
    (clientX: number, clientY: number) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return { x: 0, y: 0 };
      return {
        x: (clientX - rect.left - pan.x) / zoom,
        y: (clientY - rect.top - pan.y) / zoom,
      };
    },
    [pan, zoom]
  );

  // Handle drag & drop from sidebar
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const componentId = e.dataTransfer.getData("component-id");
    const componentName = e.dataTransfer.getData("component-name");
    const componentIcon = e.dataTransfer.getData("component-icon");
    if (!componentId) return;

    const pos = getCanvasPosition(e.clientX, e.clientY);
    onDropComponent(componentId, componentName, componentIcon, pos.x, pos.y);
  };

  // Canvas panning
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target !== canvasRef.current && !(e.target as HTMLElement).classList.contains("canvas-grid")) return;
    if (activeTool === "move" || e.button === 1) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      onPanChange({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      });
    }
    if (draggingComponent) {
      const pos = getCanvasPosition(e.clientX, e.clientY);
      onMoveComponent(draggingComponent, pos.x - dragOffset.x, pos.y - dragOffset.y);
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setDraggingComponent(null);
  };

  const handleWheel = (e: React.WheelEvent) => {
    const delta = e.deltaY > 0 ? -0.05 : 0.05;
    onZoomChange(Math.max(0.2, Math.min(3, zoom + delta)));
  };

  const handleComponentMouseDown = (e: React.MouseEvent, comp: PlacedComponent) => {
    e.stopPropagation();
    const pos = getCanvasPosition(e.clientX, e.clientY);
    setDraggingComponent(comp.id);
    setDragOffset({ x: pos.x - comp.x, y: pos.y - comp.y });
  };

  return (
    <div
      ref={canvasRef}
      className={cn(
        "flex-1 relative overflow-hidden",
        "bg-[#080d19]",
        isPanning ? "cursor-grabbing" : activeTool === "move" ? "cursor-grab" : "cursor-default"
      )}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* Grid */}
      <div
        className="canvas-grid absolute inset-0"
        style={{
          backgroundImage: `
            radial-gradient(circle, rgba(59,130,246,0.08) 1px, transparent 1px)
          `,
          backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
          backgroundPosition: `${pan.x}px ${pan.y}px`,
        }}
      />

      {/* Transform layer */}
      <div
        className="absolute inset-0"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: "0 0",
        }}
      >
        {/* Placed Components */}
        {components.map((comp) => (
          <div
            key={comp.id}
            className={cn(
              "absolute group",
              "bg-[#111a2e] border border-[#1e3058] rounded-xl",
              "hover:border-blue-500/50 hover:shadow-[0_0_20px_rgba(59,130,246,0.15)]",
              "transition-shadow duration-150",
              draggingComponent === comp.id && "border-blue-500 shadow-[0_0_25px_rgba(59,130,246,0.25)]"
            )}
            style={{
              left: comp.x,
              top: comp.y,
              width: 140,
              minHeight: 80,
            }}
            onMouseDown={(e) => handleComponentMouseDown(e, comp)}
          >
            {/* Component drag handle */}
            <div className="flex items-center gap-1 px-2 py-1.5 border-b border-[#1e3058]/50">
              <GripVertical className="w-3 h-3 text-neutral-600 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab" />
              <span className="text-[10px] text-neutral-400 font-medium truncate flex-1">
                {comp.name}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveComponent(comp.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-500/20 text-neutral-500 hover:text-red-400 transition-all"
              >
                <X className="w-3 h-3" />
              </button>
            </div>

            {/* Component body */}
            <div className="flex items-center justify-center py-3">
              <span className="text-2xl">{comp.icon}</span>
            </div>

            {/* Connection ports */}
            <div className="absolute -left-1.5 top-1/2 w-3 h-3 rounded-full bg-[#1e3058] border-2 border-blue-500/40 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-500 hover:scale-125 cursor-crosshair" />
            <div className="absolute -right-1.5 top-1/2 w-3 h-3 rounded-full bg-[#1e3058] border-2 border-blue-500/40 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-500 hover:scale-125 cursor-crosshair" />
            <div className="absolute left-1/2 -top-1.5 w-3 h-3 rounded-full bg-[#1e3058] border-2 border-blue-500/40 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-500 hover:scale-125 cursor-crosshair" />
            <div className="absolute left-1/2 -bottom-1.5 w-3 h-3 rounded-full bg-[#1e3058] border-2 border-blue-500/40 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-500 hover:scale-125 cursor-crosshair" />
          </div>
        ))}
      </div>

      {/* Empty State */}
      {components.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="flex flex-col items-center gap-5 text-center pointer-events-auto">
            {/* Robot arm illustration */}
            <div className="w-[120px] h-[120px] border-2 border-dashed border-neutral-700/50 rounded-2xl flex items-center justify-center">
              <svg
                width="64"
                height="64"
                viewBox="0 0 64 64"
                fill="none"
                className="text-neutral-600"
              >
                <path
                  d="M32 56V40M32 40l-8-12M32 40l8-12M24 28l-4-12M40 28l4-12M20 16l-4-8M44 16l4-8"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle cx="32" cy="40" r="3" stroke="currentColor" strokeWidth="2" />
                <circle cx="24" cy="28" r="2" stroke="currentColor" strokeWidth="2" />
                <circle cx="40" cy="28" r="2" stroke="currentColor" strokeWidth="2" />
                <circle cx="20" cy="16" r="2" stroke="currentColor" strokeWidth="2" />
                <circle cx="44" cy="16" r="2" stroke="currentColor" strokeWidth="2" />
                <circle cx="16" cy="8" r="2" stroke="currentColor" strokeWidth="2" />
                <circle cx="48" cy="8" r="2" stroke="currentColor" strokeWidth="2" />
                <rect x="24" y="54" width="16" height="4" rx="2" stroke="currentColor" strokeWidth="2" />
              </svg>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-1">
                Add Components to Start
              </h3>
              <p className="text-sm text-neutral-500 max-w-[260px] leading-relaxed">
                Drag components from the right panel and connect them to build your robot system.
              </p>
            </div>

            <button
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-xl transition-colors shadow-[0_0_20px_rgba(59,130,246,0.3)]"
            >
              <Plus className="w-4 h-4" />
              Add First Component
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
