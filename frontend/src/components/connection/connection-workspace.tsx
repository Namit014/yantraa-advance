"use client";

import { useCallback, useMemo, useEffect, useState, useRef } from "react";
import { useShallow } from "zustand/react/shallow";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  getSmoothStepPath,
  ConnectionLineType,
  type NodeChange,
  type EdgeChange,
  type Connection,
  type NodeTypes,
  type EdgeTypes,
  type Edge,
  type EdgeProps,
  EdgeLabelRenderer,
  BaseEdge,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Sparkles, Loader2, AlertCircle, Zap, ChevronRight, Check, Save, Plus } from "lucide-react";
import { ComponentSilhouette } from "./ComponentSilhouette";
import { ConnectionSidebar } from "./ConnectionSidebar";
import {
  useConnectionStore,
  WIRE_COLORS,
  type CircuitNodeData,
  type WireData,
  type NodeShape,
  type CircuitNode,
  type CircuitEdge,
} from "./useConnectionStore";
import { COMPONENT_CATEGORIES } from "./component-data";

// ─── Wire color legend ─────────────────────────────────────────────────────────

type WireType = "power" | "ground" | "signal" | "data" | "pwm" | "can";

const LEGEND: { type: WireType; label: string }[] = [
  { type: "power", label: "Power" },
  { type: "ground", label: "Ground" },
  { type: "signal", label: "Signal" },
  { type: "data", label: "I²C/UART" },
];

// ─── Custom Circuit Node ───────────────────────────────────────────────────────

function CircuitNodeComponent({ data }: { data: CircuitNodeData }) {
  const ports = (data.ports as CircuitNodeData["ports"]) ?? [];

  const posMap: Record<string, Position> = {
    top: Position.Top,
    bottom: Position.Bottom,
    left: Position.Left,
    right: Position.Right,
  };

  return (
    <div
      style={{
        position: "relative",
        borderRadius: 10,
        border: "1px solid rgba(42, 90, 90, 0.5)",
        backgroundColor: "transparent",
        minWidth: 180,
      }}
    >
      {/*
       * Render every port as BOTH a "source" handle AND a "target" handle,
       * both with id={port.id}. This is the critical fix for React Flow
       * error #008: edges reference sourceHandle/targetHandle by the bare
       * port id. React Flow distinguishes source vs target handles by their
       * `type` prop internally, so the same id on both types is valid and
       * lets any port id be used as either end of a wire.
       */}
      {ports.flatMap((port) => {
        const rfPos = posMap[port.side] ?? Position.Right;
        const sharedStyle: React.CSSProperties = {
          width: 12,
          height: 12,
          background: "#1e3a5f",
          border: "2px solid #3b82f6",
          zIndex: 20,
          cursor: "crosshair",
          ...(port.side === "top" || port.side === "bottom"
            ? { left: `${port.offsetPercent}%`, transform: "translateX(-50%)" }
            : { top: `${port.offsetPercent}%`, transform: "translateY(-50%)" }),
        };
        const handleClass = "flex items-center justify-center hover:scale-150 hover:bg-blue-400 hover:border-white transition-all duration-200 shadow-md group";
        return [
          // source handle — id matches edge.sourceHandle
          <Handle
            key={`${port.id}-src`}
            id={port.id}
            type="source"
            position={rfPos}
            style={sharedStyle}
            className={handleClass}
            isConnectable
          >
            <Plus size={8} className="text-white opacity-0 group-hover:opacity-100 transition-opacity" />
          </Handle>,
          // target handle — same id matches edge.targetHandle
          <Handle
            key={`${port.id}-tgt`}
            id={port.id}
            type="target"
            position={rfPos}
            style={sharedStyle}
            className={handleClass}
            isConnectable
          >
            <Plus size={8} className="text-white opacity-0 group-hover:opacity-100 transition-opacity" />
          </Handle>,
        ];
      })}

      {/* Fallback source/target for generic drag-connect (hidden) */}
      <Handle type="target" position={Position.Left}  id="left-default"  style={{ opacity: 0, left: 0,  width: 10, height: 10, zIndex: -1 }} />
      <Handle type="source" position={Position.Right} id="right-default" style={{ opacity: 0, right: 0, width: 10, height: 10, zIndex: -1 }} />

      {/* SVG silhouette */}
      <ComponentSilhouette
        shape={(data.shape as NodeShape) ?? "generic-board"}
        ports={ports}
        label={(data.label as string) ?? "Component"}
      />
    </div>
  );
}

// ─── Custom Wire Edge ──────────────────────────────────────────────────────────

function CircuitWireComponent(props: EdgeProps) {
  const {
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    data,
    selected,
    markerEnd,
  } = props;

  const wireData = data as WireData | undefined;
  const color = wireData?.color ?? "#4488FF";
  const label = wireData?.label ?? "";
  const setSelectedEdge = useConnectionStore((s) => s.setSelectedEdge);

  // getSmoothStepPath with borderRadius:16 gives clean smoothstep routing
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 16,
  });

  return (
    <>
      {/* Wide invisible hit zone */}
      <path
        d={edgePath}
        strokeWidth={16}
        fill="none"
        stroke="transparent"
        onClick={() => setSelectedEdge(id)}
        style={{ cursor: "pointer" }}
      />
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: color,
          strokeWidth: selected ? 2.5 : 1.5,
          filter: selected
            ? `drop-shadow(0 0 6px ${color})`
            : `drop-shadow(0 0 3px ${color}88)`,
          cursor: "pointer",
          transition: "stroke-width 0.15s, filter 0.15s",
        }}
      />
      {/* Label pill */}
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: "none",
              zIndex: 10,
              backgroundColor: `${color}22`,
              border: `1px solid ${color}66`,
              borderRadius: 10,
              padding: "2px 7px",
              color: color,
              fontSize: 9,
              fontFamily: "monospace",
              fontWeight: 700,
              letterSpacing: "0.04em",
              whiteSpace: "nowrap",
              backdropFilter: "blur(4px)",
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

// ─── Inner flow (must be child of ReactFlowProvider) ──────────────────────────

function FlowCanvas({ currentQuery, designData }: { currentQuery?: string; designData?: any }) {
  const nodeTypes = useMemo<NodeTypes>(() => ({
    circuitNode: CircuitNodeComponent as unknown as NodeTypes[string],
  }), []);

  const edgeTypes = useMemo<EdgeTypes>(() => ({
    circuitWire: CircuitWireComponent as unknown as EdgeTypes[string],
  }), []);

  // ── Bug 1 fix: useShallow prevents new object ref on every render ──
  const {
    storeNodes,
    storeEdges,
    setStoreNodes,
    setStoreEdges,
    setSelectedEdge,
    sidebarOpen,
    setSidebarOpen,
    isGenerating,
    error,
    prompt,
    setPrompt,
    generate,
    loadDesignData,
    saveState,
    setSaveState,
    saveGraph,
    loadGraph,
    isValidConnection,
  } = useConnectionStore(
    useShallow((s) => ({
      storeNodes: s.nodes,
      storeEdges: s.edges,
      setStoreNodes: s.setNodes,
      setStoreEdges: s.setEdges,
      setSelectedEdge: s.setSelectedEdge,
      sidebarOpen: s.sidebarOpen,
      setSidebarOpen: s.setSidebarOpen,
      isGenerating: s.isGenerating,
      error: s.error,
      prompt: s.prompt,
      setPrompt: s.setPrompt,
      generate: s.generate,
      loadDesignData: s.loadDesignData,
      saveState: s.saveState,
      setSaveState: s.setSaveState,
      saveGraph: s.saveGraph,
      loadGraph: s.loadGraph,
      isValidConnection: s.isValidConnection,
    }))
  );

  // ── Bug 2 fix: plain useState + applyNodeChanges keeps RF as source of truth ──
  // The store is only written on drag-end, not on every pixel moved.
  const [rfNodes, setRfNodes] = useState<CircuitNode[]>([]);
  const [rfEdges, setRfEdges] = useState<CircuitEdge[]>([]);

  // Sync store → local RF state only when the store array reference changes
  // (i.e. after generate() completes), not on every drag event.
  useEffect(() => { setRfNodes(storeNodes as CircuitNode[]); }, [storeNodes]);
  useEffect(() => {
    // ── Edge #008 validation ──────────────────────────────────────────────────
    // React Flow error #008 fires when an edge references a sourceHandle or
    // targetHandle id that doesn't exist on the node. Both source and target
    // handles now share the same id={port.id}, so we validate against the
    // node's ports array for both ends and drop any unresolvable edges.
    const nodeMap = new Map(
      (storeNodes as CircuitNode[]).map((n) => [n.id, n])
    );

    const validEdges = (storeEdges as CircuitEdge[]).filter((edge) => {
      if (!edge.sourceHandle && !edge.targetHandle) return true;

      const srcNode = nodeMap.get(edge.source);
      const tgtNode = nodeMap.get(edge.target);
      const srcPorts = (srcNode?.data?.ports as { id: string }[] | undefined) ?? [];
      const tgtPorts = (tgtNode?.data?.ports as { id: string }[] | undefined) ?? [];

      const srcOk = !edge.sourceHandle || srcPorts.some((p) => p.id === edge.sourceHandle);
      const tgtOk = !edge.targetHandle || tgtPorts.some((p) => p.id === edge.targetHandle);

      if (!srcOk || !tgtOk) {
        console.warn(
          `[ConnectionWorkspace] Dropping edge "${edge.id}" — handle not found.`,
          { sourceHandle: edge.sourceHandle, srcOk, targetHandle: edge.targetHandle, tgtOk }
        );
        return false;
      }
      return true;
    });

    setRfEdges(validEdges);
  }, [storeEdges, storeNodes]);

  // onNodesChange: apply RF built-in change logic; does NOT write to Zustand store
  const onNodesChange = useCallback(
    (changes: NodeChange<CircuitNode>[]) =>
      setRfNodes((nds) => applyNodeChanges(changes, nds) as CircuitNode[]),
    []
  );

  // onEdgesChange: same pattern for edges
  const onEdgesChange = useCallback(
    (changes: EdgeChange<CircuitEdge>[]) =>
      setRfEdges((eds) => applyEdgeChanges(changes, eds) as CircuitEdge[]),
    []
  );

  // Write node positions back to the Zustand store only when drag ends
  const onNodeDragStop = useCallback(
    (_event: MouseEvent | TouchEvent, node: CircuitNode) => {
      setStoreNodes((prev) =>
        prev.map((n) => (n.id === node.id ? { ...n, position: node.position } : n))
      );
    },
    [setStoreNodes]
  );

  // Manual connect handler
  const handleConnect = useCallback(
    (params: Connection) => {
      const newEdge: CircuitEdge = {
        id: `wire-${Date.now()}`,
        source: params.source ?? "",
        target: params.target ?? "",
        sourceHandle: params.sourceHandle ?? undefined,
        targetHandle: params.targetHandle ?? undefined,
        type: "circuitWire",
        label: "signal",
        data: {
          from: { nodeId: params.source ?? "", portId: params.sourceHandle ?? "" },
          to: { nodeId: params.target ?? "", portId: params.targetHandle ?? "" },
          color: WIRE_COLORS.signal,
          label: "signal",
          wireType: "signal" as WireType,
        },
        style: { stroke: WIRE_COLORS.signal, strokeWidth: 2 },
      };
      setRfEdges((prev) => addEdge(newEdge, prev) as CircuitEdge[]);
      setStoreEdges([...storeEdges, newEdge]);
    },
    [setRfEdges, setStoreEdges, storeEdges]
  );

  const handleEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      setSelectedEdge(edge.id);
    },
    [setSelectedEdge]
  );

  // Component list for generate API
  const libraryComponents = useMemo(
    () =>
      COMPONENT_CATEGORIES.flatMap((cat) =>
        cat.items.map((item) => ({
          id: item.id,
          name: item.name,
          type: cat.name.toLowerCase(),
        }))
      ),
    []
  );

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim() || isGenerating) return;
    const subsystems = designData?.subsystems || null;
    await generate(libraryComponents, prompt, subsystems);
  }, [prompt, isGenerating, generate, libraryComponents, designData]);

  // Load designData when it arrives
  useEffect(() => {
    if (designData) {
      loadDesignData(designData);
    }
  }, [designData, loadDesignData]);

  // Load from local storage on mount
  useEffect(() => {
    if (!designData) {
      loadGraph();
    }
  }, [loadGraph, designData]);

  // Auto-generate when currentQuery arrives from chat
  const lastAutoQuery = useRef<string>("");
  useEffect(() => {
    if (designData) return;
    if (
      currentQuery &&
      currentQuery.trim() &&
      currentQuery !== lastAutoQuery.current &&
      !isGenerating
    ) {
      lastAutoQuery.current = currentQuery;
      setPrompt(currentQuery);
      generate(libraryComponents, currentQuery, null);
    }
  }, [currentQuery, isGenerating, generate, libraryComponents, setPrompt, designData]);

  // Auto-save mechanism
  useEffect(() => {
    if (saveState === "unsaved") {
      setSaveState("saving");
      const timeout = setTimeout(() => {
        saveGraph();
      }, 1000);
      return () => clearTimeout(timeout);
    }
  }, [saveState, setSaveState, saveGraph]);

  // nodeTypes and edgeTypes are now defined at the module level

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        backgroundColor: "#06080f",
        borderRadius: 12,
        overflow: "hidden",
        border: "1px solid #1a2744",
        position: "relative",
      }}
    >
      {/* ── Top bar ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 14px",
          borderBottom: "1px solid #1a2744",
          backgroundColor: "#080d1a",
          flexShrink: 0,
          flexWrap: "wrap",
          rowGap: 8,
        }}
      >
        {/* Prompt input */}
        <div
          style={{
            flex: 1,
            minWidth: 180,
            display: "flex",
            alignItems: "center",
            gap: 8,
            backgroundColor: "#0d1528",
            border: "1px solid #1a2744",
            borderRadius: 8,
            padding: "6px 12px",
          }}
        >
          <Sparkles size={13} style={{ color: "#4488ff", flexShrink: 0 }} />
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
            placeholder="Describe your circuit… e.g. Arduino + L298N + IR sensors"
            style={{
              flex: 1,
              background: "none",
              border: "none",
              outline: "none",
              color: "white",
              fontSize: 12,
              fontFamily: "monospace",
            }}
          />
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={isGenerating || !prompt.trim()}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 7,
            padding: "7px 16px",
            borderRadius: 8,
            border: "1px solid",
            borderColor: isGenerating || !prompt.trim() ? "#1a2744" : "#3b82f6",
            backgroundColor: isGenerating || !prompt.trim() ? "#0d1528" : "#1e3a5f",
            color: isGenerating || !prompt.trim() ? "#374151" : "#60a5fa",
            fontSize: 12,
            fontFamily: "monospace",
            fontWeight: 700,
            cursor: isGenerating || !prompt.trim() ? "not-allowed" : "pointer",
            transition: "all 0.2s",
            whiteSpace: "nowrap",
          }}
          onMouseEnter={(e) => {
            if (!isGenerating && prompt.trim()) {
              e.currentTarget.style.backgroundColor = "#2563eb";
              e.currentTarget.style.color = "white";
            }
          }}
          onMouseLeave={(e) => {
            if (!isGenerating && prompt.trim()) {
              e.currentTarget.style.backgroundColor = "#1e3a5f";
              e.currentTarget.style.color = "#60a5fa";
            }
          }}
        >
          {isGenerating ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
          {isGenerating ? "Generating…" : "Generate"}
        </button>

        {/* Wire legend */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          {LEGEND.map((l) => (
            <div key={l.type} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div
                style={{
                  width: 18,
                  height: 2,
                  backgroundColor: WIRE_COLORS[l.type],
                  borderRadius: 1,
                  boxShadow: `0 0 4px ${WIRE_COLORS[l.type]}88`,
                }}
              />
              <span style={{ color: WIRE_COLORS[l.type], fontSize: 9, fontFamily: "monospace", opacity: 0.85 }}>
                {l.label}
              </span>
            </div>
          ))}
        </div>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          {/* Save indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, color: saveState === "saved" ? "#4ade80" : saveState === "saving" ? "#fbbf24" : "#9ca3af", fontSize: 11, fontFamily: "monospace", opacity: 0.9 }}>
            {saveState === "saved" ? <Check size={13} /> : saveState === "saving" ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            {saveState === "saved" ? "Saved" : saveState === "saving" ? "Saving..." : "Unsaved"}
          </div>

          {/* Sidebar toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            padding: "6px 10px",
            borderRadius: 6,
            border: "1px solid #1a2744",
            backgroundColor: sidebarOpen ? "#1e3a5f" : "#0d1528",
            color: sidebarOpen ? "#60a5fa" : "#6b7280",
            fontSize: 11,
            fontFamily: "monospace",
            cursor: "pointer",
            transition: "all 0.15s",
          }}
        >
          <ChevronRight
            size={13}
            style={{
              transform: sidebarOpen ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.2s",
            }}
          />
          Panel
        </button>
        </div>
      </div>

      {/* ── Error banner ── */}
      {error && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 16px",
            backgroundColor: "#2d1010",
            borderBottom: "1px solid #7f1d1d",
            color: "#f87171",
            fontSize: 11,
            fontFamily: "monospace",
          }}
        >
          <AlertCircle size={13} />
          {error} — using fallback layout
        </div>
      )}

      {/* ── Main canvas area + sidebar ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", position: "relative" }}>
      <div style={{ flex: 1, position: "relative", width: "100%", height: "100%", minHeight: 400 }}>
          {/* Empty state */}
          {rfNodes.length === 0 && !isGenerating && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 5,
                pointerEvents: "none",
                gap: 14,
              }}
            >
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: "50%",
                  border: "2px dashed #1a2744",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Sparkles size={28} style={{ color: "#1a2744" }} />
              </div>
              <div style={{ textAlign: "center", maxWidth: 300 }}>
                <p style={{ color: "#60a5fa", fontSize: 14, fontFamily: "monospace", fontWeight: 600 }}>
                  Canvas is Empty
                </p>
                <p style={{ color: "#6b7280", fontSize: 12, fontFamily: "monospace", marginTop: 8, lineHeight: 1.5 }}>
                  Type a description above and click Generate to let AI build a circuit.
                </p>
                <div style={{ margin: "16px auto", width: 40, height: 1, backgroundColor: "#1a2744" }} />
                <p style={{ color: "#6b7280", fontSize: 12, fontFamily: "monospace", lineHeight: 1.5 }}>
                  Or <span style={{ color: "#9ca3af" }}>drag and drop</span> components from the Component Library panel on the right.
                </p>
              </div>
            </div>
          )}

          {/* Loading overlay */}
          {isGenerating && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 10,
                backgroundColor: "rgba(6,8,15,0.85)",
                backdropFilter: "blur(6px)",
                gap: 14,
              }}
            >
              <Loader2 size={38} style={{ color: "#3b82f6" }} className="animate-spin" />
              <p style={{ color: "#60a5fa", fontSize: 13, fontFamily: "monospace" }}>
                Generating circuit diagram…
              </p>
            </div>
          )}

          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeDragStop={onNodeDragStop}
            onConnect={handleConnect}
            onEdgeClick={handleEdgeClick}
            isValidConnection={(connection) => {
              if (!connection.source || !connection.sourceHandle || !connection.target || !connection.targetHandle) return false;
              return isValidConnection(connection.source, connection.sourceHandle, connection.target, connection.targetHandle).valid;
            }}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            fitViewOptions={{ padding: 0.25, maxZoom: 0.85 }}
            minZoom={0.05}
            maxZoom={3}
            connectionLineType={ConnectionLineType.SmoothStep}
            edgesFocusable={false}
            defaultEdgeOptions={{
              type: "circuitWire",
              style: { stroke: WIRE_COLORS.signal, strokeWidth: 1.5 },
            }}
            style={{ backgroundColor: "#06080f" }}
            proOptions={{ hideAttribution: true }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1.2}
              color="#1a2744"
            />
            <Controls
              style={{
                backgroundColor: "#0d1528",
                border: "1px solid #1a2744",
                borderRadius: 8,
              }}
            />
            <MiniMap
              style={{
                backgroundColor: "#080d1a",
                border: "1px solid #1a2744",
                borderRadius: 8,
              }}
              nodeColor="#1a3a5a"
              maskColor="rgba(6,8,15,0.7)"
            />
          </ReactFlow>
        </div>

        {/* Collapsible right sidebar */}
        <ConnectionSidebar />
      </div>
    </div>
  );
}

// ─── Public export (wrapped with provider) ────────────────────────────────────

export function ConnectionWorkspace({ currentQuery, designData }: { currentQuery?: string; designData?: any }) {
  return (
    <ReactFlowProvider>
      <FlowCanvas currentQuery={currentQuery} designData={designData} />
    </ReactFlowProvider>
  );
}
