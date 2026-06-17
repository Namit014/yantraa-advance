"use client";

import {
  MousePointer2,
  RotateCcw,
  Maximize2,
  Move,
  Trash2,
  Minus,
  Plus,
  Maximize,
  Lock,
  Crosshair,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CONNECTION_TYPES } from "./component-data";

interface WorkspaceToolbarProps {
  activeTool: string;
  onToolChange: (tool: string) => void;
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomFit: () => void;
}

const TOOLS = [
  { id: "select", icon: MousePointer2, label: "Select" },
  { id: "undo", icon: RotateCcw, label: "Undo" },
  { id: "fullscreen", icon: Maximize2, label: "Fullscreen" },
  { id: "move", icon: Move, label: "Pan" },
  { id: "delete", icon: Trash2, label: "Delete" },
];

export function WorkspaceToolbar({
  activeTool,
  onToolChange,
  zoom,
  onZoomIn,
  onZoomOut,
  onZoomFit,
}: WorkspaceToolbarProps) {
  return (
    <div className="absolute top-4 left-4 right-4 z-10 flex items-center justify-between pointer-events-none">
      {/* Left Tools Group */}
      <div className="flex items-center gap-1 bg-[#0c1220]/90 backdrop-blur-md border border-[#1a2744] rounded-xl p-1 pointer-events-auto">
        {TOOLS.map((tool) => (
          <button
            key={tool.id}
            onClick={() => onToolChange(tool.id)}
            title={tool.label}
            className={cn(
              "p-2.5 rounded-lg transition-all duration-150",
              activeTool === tool.id
                ? "bg-blue-600/20 text-blue-400"
                : "text-neutral-500 hover:text-white hover:bg-white/5"
            )}
          >
            <tool.icon className="w-4 h-4" />
          </button>
        ))}
      </div>

      {/* Center Zoom + Legend */}
      <div className="flex items-center gap-3 pointer-events-auto">
        {/* Zoom Controls */}
        <div className="flex items-center gap-1 bg-[#0c1220]/90 backdrop-blur-md border border-[#1a2744] rounded-xl p-1">
          <button
            onClick={onZoomOut}
            className="p-2 rounded-lg text-neutral-500 hover:text-white hover:bg-white/5 transition-colors"
          >
            <Minus className="w-3.5 h-3.5" />
          </button>
          <span className="text-xs text-neutral-300 font-medium min-w-[48px] text-center tabular-nums">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={onZoomIn}
            className="p-2 rounded-lg text-neutral-500 hover:text-white hover:bg-white/5 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 bg-[#0c1220]/90 backdrop-blur-md border border-[#1a2744] rounded-xl px-4 py-2">
          {CONNECTION_TYPES.map((type) => (
            <div key={type.name} className="flex items-center gap-1.5">
              <div className="flex items-center gap-0.5">
                <div
                  className="w-2.5 h-[2px] rounded-full"
                  style={{ backgroundColor: type.color }}
                />
                <div
                  className="w-1 h-[2px] rounded-full"
                  style={{ backgroundColor: type.color }}
                />
                <div
                  className="w-2.5 h-[2px] rounded-full"
                  style={{ backgroundColor: type.color }}
                />
              </div>
              <span className="text-[10px] text-neutral-400">{type.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right Tools */}
      <div className="flex items-center gap-1 bg-[#0c1220]/90 backdrop-blur-md border border-[#1a2744] rounded-xl p-1 pointer-events-auto">
        <button
          onClick={onZoomFit}
          className="p-2.5 rounded-lg text-neutral-500 hover:text-white hover:bg-white/5 transition-colors"
          title="Fit to view"
        >
          <Maximize className="w-4 h-4" />
        </button>
        <button
          className="p-2.5 rounded-lg text-neutral-500 hover:text-white hover:bg-white/5 transition-colors"
          title="Lock canvas"
        >
          <Lock className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

interface MinimapProps {
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onCenter: () => void;
}

export function Minimap({ zoom, onZoomIn, onZoomOut, onCenter }: MinimapProps) {
  return (
    <div className="absolute bottom-4 left-4 z-10 flex items-end gap-2">
      {/* Minimap */}
      <div className="w-[120px] h-[80px] bg-[#0c1220]/90 backdrop-blur-md border border-[#1a2744] rounded-xl overflow-hidden">
        <div className="w-full h-full relative p-2">
          {/* Mini grid */}
          <div
            className="w-full h-full rounded border border-blue-500/30 bg-blue-500/5"
            style={{
              backgroundImage: `
                linear-gradient(to right, rgba(59,130,246,0.1) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(59,130,246,0.1) 1px, transparent 1px)
              `,
              backgroundSize: "8px 8px",
            }}
          >
            {/* Viewport indicator */}
            <div
              className="absolute border-2 border-blue-500/60 rounded bg-blue-500/5"
              style={{
                width: `${Math.min(100, 100 / zoom)}%`,
                height: `${Math.min(100, 100 / zoom)}%`,
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
              }}
            />
          </div>
        </div>
      </div>

      {/* Minimap Controls */}
      <div className="flex flex-col gap-1 bg-[#0c1220]/90 backdrop-blur-md border border-[#1a2744] rounded-xl p-1">
        <button
          onClick={onCenter}
          className="p-1.5 rounded-lg text-neutral-500 hover:text-white hover:bg-white/5 transition-colors"
          title="Center view"
        >
          <Crosshair className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={onZoomIn}
          className="p-1.5 rounded-lg text-neutral-500 hover:text-white hover:bg-white/5 transition-colors"
          title="Zoom in"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={onZoomOut}
          className="p-1.5 rounded-lg text-neutral-500 hover:text-white hover:bg-white/5 transition-colors"
          title="Zoom out"
        >
          <Minus className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
