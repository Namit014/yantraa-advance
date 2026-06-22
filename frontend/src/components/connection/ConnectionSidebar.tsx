"use client";

import { useState, useEffect } from "react";
import { X, Trash2, Save, Plus, ChevronRight, AlertCircle } from "lucide-react";
import {
  useConnectionStore,
  WIRE_COLORS,
  type WireType,
  type CircuitNode,
  type CircuitEdge,
  type Port,
} from "./useConnectionStore";

// ─── Wire type selector ────────────────────────────────────────────────────────

const WIRE_TYPES: { value: WireType; label: string }[] = [
  { value: "power", label: "Power" },
  { value: "ground", label: "Ground" },
  { value: "signal", label: "Signal" },
  { value: "data", label: "Data (I²C/SPI/UART)" },
  { value: "pwm", label: "PWM" },
  { value: "can", label: "CAN Bus" },
];

// ─── Port select ───────────────────────────────────────────────────────────────

function PortSelect({
  nodes,
  selectedNodeId,
  selectedPortId,
  onNodeChange,
  onPortChange,
  label,
}: {
  nodes: CircuitNode[];
  selectedNodeId: string;
  selectedPortId: string;
  onNodeChange: (nodeId: string) => void;
  onPortChange: (portId: string) => void;
  label: string;
}) {
  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const ports: Port[] = (selectedNode?.data?.ports as Port[]) ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label
        style={{
          fontSize: 10,
          color: "#9ca3af",
          fontFamily: "monospace",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {label}
      </label>
      {/* Component dropdown */}
      <select
        value={selectedNodeId}
        onChange={(e) => onNodeChange(e.target.value)}
        style={{
          backgroundColor: "#111827",
          border: "1px solid #1f2937",
          borderRadius: 6,
          color: "white",
          padding: "6px 8px",
          fontSize: 12,
          fontFamily: "monospace",
          outline: "none",
          cursor: "pointer",
          width: "100%",
        }}
      >
        {nodes.map((n) => (
          <option key={n.id} value={n.id} style={{ backgroundColor: "#111827" }}>
            {n.data.label as string}
          </option>
        ))}
      </select>
      {/* Port dropdown */}
      <select
        value={selectedPortId}
        onChange={(e) => onPortChange(e.target.value)}
        style={{
          backgroundColor: "#111827",
          border: "1px solid #1f2937",
          borderRadius: 6,
          color: "white",
          padding: "6px 8px",
          fontSize: 12,
          fontFamily: "monospace",
          outline: "none",
          cursor: "pointer",
          width: "100%",
        }}
      >
        {ports.length === 0 && (
          <option value="" style={{ backgroundColor: "#111827" }}>
            — no ports —
          </option>
        )}
        {ports.map((p) => (
          <option key={p.id} value={p.id} style={{ backgroundColor: "#111827" }}>
            {p.label} ({p.side})
          </option>
        ))}
      </select>
    </div>
  );
}

// ─── Main sidebar ──────────────────────────────────────────────────────────────

export function ConnectionSidebar() {
  const { nodes, edges, selectedEdgeId, sidebarOpen, setSidebarOpen, updateEdge, deleteEdge, addEdge, setSelectedEdge } =
    useConnectionStore();

  const selectedEdge: CircuitEdge | undefined = edges.find(
    (e) => e.id === selectedEdgeId
  );

  // Local edit state for selected wire
  const [fromNodeId, setFromNodeId] = useState("");
  const [fromPortId, setFromPortId] = useState("");
  const [toNodeId, setToNodeId] = useState("");
  const [toPortId, setToPortId] = useState("");
  const [wireType, setWireType] = useState<WireType>("signal");
  const [wireLabel, setWireLabel] = useState("");

  // Add connection local state
  const [addFromNodeId, setAddFromNodeId] = useState("");
  const [addFromPortId, setAddFromPortId] = useState("");
  const [addToNodeId, setAddToNodeId] = useState("");
  const [addToPortId, setAddToPortId] = useState("");
  const [addWireType, setAddWireType] = useState<WireType>("signal");

  // Sync local state when selected edge changes
  useEffect(() => {
    if (!selectedEdge?.data) return;
    const d = selectedEdge.data;
    setFromNodeId(d.from.nodeId ?? "");
    setFromPortId(d.from.portId ?? "");
    setToNodeId(d.to.nodeId ?? "");
    setToPortId(d.to.portId ?? "");
    setWireType(d.wireType ?? "signal");
    setWireLabel(d.label ?? "");
  }, [selectedEdge]);

  // Initialize add form defaults
  useEffect(() => {
    if (nodes.length > 0) {
      setAddFromNodeId(nodes[0].id);
      setAddToNodeId(nodes.length > 1 ? nodes[1].id : nodes[0].id);
    }
  }, [nodes]);

  const handleSave = () => {
    if (!selectedEdgeId) return;
    updateEdge(selectedEdgeId, {
      from: { nodeId: fromNodeId, portId: fromPortId },
      to: { nodeId: toNodeId, portId: toPortId },
      wireType,
      label: wireLabel,
    });
  };

  const handleDelete = () => {
    if (!selectedEdgeId) return;
    deleteEdge(selectedEdgeId);
  };

  const handleAddConnection = () => {
    const id = `wire-user-${Date.now()}`;
    const fromNode = nodes.find((n) => n.id === addFromNodeId);
    const toNode = nodes.find((n) => n.id === addToNodeId);
    if (!fromNode || !toNode) return;

    const newEdge: CircuitEdge = {
      id,
      source: addFromNodeId,
      target: addToNodeId,
      sourceHandle: addFromPortId || undefined,
      targetHandle: addToPortId || undefined,
      type: "circuitWire",
      label: addWireType,
      data: {
        from: { nodeId: addFromNodeId, portId: addFromPortId },
        to: { nodeId: addToNodeId, portId: addToPortId },
        color: WIRE_COLORS[addWireType],
        label: addWireType,
        wireType: addWireType,
      },
      style: { stroke: WIRE_COLORS[addWireType], strokeWidth: 2 },
    };
    addEdge(newEdge);
    setSelectedEdge(id);
  };

  const containerStyle: React.CSSProperties = {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    width: sidebarOpen ? 300 : 0,
    overflow: "hidden",
    transition: "width 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
    zIndex: 20,
    backgroundColor: "#0a0f1a",
    borderLeft: sidebarOpen ? "1px solid #1a2744" : "none",
    display: "flex",
    flexDirection: "column",
  };

  const innerStyle: React.CSSProperties = {
    width: 300,
    height: "100%",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  };

  return (
    <div style={containerStyle}>
      <div style={innerStyle}>
        {/* Header */}
        <div
          style={{
            padding: "16px",
            borderBottom: "1px solid #1a2744",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexShrink: 0,
          }}
        >
          <span
            style={{
              color: "white",
              fontSize: 13,
              fontWeight: 700,
              fontFamily: "monospace",
              letterSpacing: "0.05em",
            }}
          >
            {selectedEdge ? "Edit Wire" : "Connections"}
          </span>
          <button
            onClick={() => setSidebarOpen(false)}
            style={{
              background: "none",
              border: "none",
              color: "#6b7280",
              cursor: "pointer",
              padding: 4,
              borderRadius: 4,
              display: "flex",
              alignItems: "center",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.color = "white")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.color = "#6b7280")
            }
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Scroll area */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: 20,
          }}
        >
          {/* ── Wire Edit Section ── */}
          {selectedEdge ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 10px",
                  backgroundColor: `${WIRE_COLORS[selectedEdge.data?.wireType ?? "signal"]}22`,
                  border: `1px solid ${WIRE_COLORS[selectedEdge.data?.wireType ?? "signal"]}44`,
                  borderRadius: 6,
                }}
              >
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    backgroundColor:
                      WIRE_COLORS[selectedEdge.data?.wireType ?? "signal"],
                  }}
                />
                <span
                  style={{
                    color: WIRE_COLORS[selectedEdge.data?.wireType ?? "signal"],
                    fontSize: 11,
                    fontFamily: "monospace",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  {selectedEdge.data?.wireType ?? "signal"} wire
                </span>
              </div>

              {/* From */}
              <PortSelect
                nodes={nodes}
                selectedNodeId={fromNodeId}
                selectedPortId={fromPortId}
                onNodeChange={setFromNodeId}
                onPortChange={setFromPortId}
                label="From"
              />

              {/* To */}
              <PortSelect
                nodes={nodes}
                selectedNodeId={toNodeId}
                selectedPortId={toPortId}
                onNodeChange={setToNodeId}
                onPortChange={setToPortId}
                label="To"
              />

              {/* Wire type */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label
                  style={{
                    fontSize: 10,
                    color: "#9ca3af",
                    fontFamily: "monospace",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Wire Type
                </label>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {WIRE_TYPES.map((wt) => (
                    <button
                      key={wt.value}
                      onClick={() => setWireType(wt.value)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 10px",
                        backgroundColor:
                          wireType === wt.value
                            ? `${WIRE_COLORS[wt.value]}22`
                            : "transparent",
                        border:
                          wireType === wt.value
                            ? `1px solid ${WIRE_COLORS[wt.value]}66`
                            : "1px solid #1f2937",
                        borderRadius: 6,
                        cursor: "pointer",
                        textAlign: "left",
                        width: "100%",
                        transition: "all 0.15s",
                      }}
                    >
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          backgroundColor: WIRE_COLORS[wt.value],
                          flexShrink: 0,
                        }}
                      />
                      <span
                        style={{
                          color:
                            wireType === wt.value
                              ? WIRE_COLORS[wt.value]
                              : "#9ca3af",
                          fontSize: 11,
                          fontFamily: "monospace",
                        }}
                      >
                        {wt.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Label */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label
                  style={{
                    fontSize: 10,
                    color: "#9ca3af",
                    fontFamily: "monospace",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Label
                </label>
                <input
                  type="text"
                  value={wireLabel}
                  onChange={(e) => setWireLabel(e.target.value)}
                  placeholder="e.g. I2C SDA, PWM1..."
                  style={{
                    backgroundColor: "#111827",
                    border: "1px solid #1f2937",
                    borderRadius: 6,
                    color: "white",
                    padding: "6px 10px",
                    fontSize: 12,
                    fontFamily: "monospace",
                    outline: "none",
                    width: "100%",
                  }}
                  onFocus={(e) =>
                    (e.currentTarget.style.borderColor = "#3b82f6")
                  }
                  onBlur={(e) =>
                    (e.currentTarget.style.borderColor = "#1f2937")
                  }
                />
              </div>

              {/* Action buttons */}
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  onClick={handleSave}
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 6,
                    padding: "8px",
                    backgroundColor: "#1e3a5f",
                    border: "1px solid #3b82f6",
                    borderRadius: 6,
                    color: "#60a5fa",
                    fontSize: 12,
                    fontFamily: "monospace",
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "#2563eb";
                    e.currentTarget.style.color = "white";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "#1e3a5f";
                    e.currentTarget.style.color = "#60a5fa";
                  }}
                >
                  <Save size={13} />
                  Save
                </button>
                <button
                  onClick={handleDelete}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 6,
                    padding: "8px 14px",
                    backgroundColor: "#2d1010",
                    border: "1px solid #7f1d1d",
                    borderRadius: 6,
                    color: "#ef4444",
                    fontSize: 12,
                    fontFamily: "monospace",
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "#7f1d1d";
                    e.currentTarget.style.color = "white";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "#2d1010";
                    e.currentTarget.style.color = "#ef4444";
                  }}
                >
                  <Trash2 size={13} />
                  Delete
                </button>
              </div>

              {/* Divider */}
              <div
                style={{
                  borderTop: "1px solid #1a2744",
                  margin: "4px 0",
                }}
              />
            </div>
          ) : (
            <div
              style={{
                color: "#6b7280",
                fontSize: 12,
                fontFamily: "monospace",
                textAlign: "center",
                padding: "12px 0",
              }}
            >
              Click a wire to edit it
            </div>
          )}

          {/* ── Add Connection Section ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                color: "#9ca3af",
                fontSize: 11,
                fontFamily: "monospace",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              <Plus size={11} />
              Add Connection
            </div>

            <PortSelect
              nodes={nodes}
              selectedNodeId={addFromNodeId}
              selectedPortId={addFromPortId}
              onNodeChange={setAddFromNodeId}
              onPortChange={setAddFromPortId}
              label="From"
            />

            <PortSelect
              nodes={nodes}
              selectedNodeId={addToNodeId}
              selectedPortId={addToPortId}
              onNodeChange={setAddToNodeId}
              onPortChange={setAddToPortId}
              label="To"
            />

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label
                style={{
                  fontSize: 10,
                  color: "#9ca3af",
                  fontFamily: "monospace",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Type
              </label>
              <select
                value={addWireType}
                onChange={(e) => setAddWireType(e.target.value as WireType)}
                style={{
                  backgroundColor: "#111827",
                  border: "1px solid #1f2937",
                  borderRadius: 6,
                  color: "white",
                  padding: "6px 8px",
                  fontSize: 12,
                  fontFamily: "monospace",
                  outline: "none",
                  cursor: "pointer",
                  width: "100%",
                }}
              >
                {WIRE_TYPES.map((wt) => (
                  <option key={wt.value} value={wt.value} style={{ backgroundColor: "#111827" }}>
                    {wt.label}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleAddConnection}
              disabled={nodes.length < 2}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                padding: "8px",
                backgroundColor: nodes.length < 2 ? "#0f1520" : "#0f2a1a",
                border: `1px solid ${nodes.length < 2 ? "#1a2744" : "#166534"}`,
                borderRadius: 6,
                color: nodes.length < 2 ? "#374151" : "#4ade80",
                fontSize: 12,
                fontFamily: "monospace",
                cursor: nodes.length < 2 ? "not-allowed" : "pointer",
                transition: "all 0.15s",
                width: "100%",
              }}
              onMouseEnter={(e) => {
                if (nodes.length >= 2) {
                  e.currentTarget.style.backgroundColor = "#166534";
                  e.currentTarget.style.color = "white";
                }
              }}
              onMouseLeave={(e) => {
                if (nodes.length >= 2) {
                  e.currentTarget.style.backgroundColor = "#0f2a1a";
                  e.currentTarget.style.color = "#4ade80";
                }
              }}
            >
              <Plus size={13} />
              Add Wire
            </button>
          </div>

          {/* ── Diagnostics & Repair Section ── */}
          {nodes.some((n) => n.data.isOrphaned) && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 16 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  color: "#ef4444",
                  fontSize: 11,
                  fontFamily: "monospace",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                <AlertCircle size={11} />
                Diagnostics (Orphans Detected)
              </div>
              
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {nodes
                  .filter((n) => n.data.isOrphaned)
                  .map((n) => (
                    <div
                      key={n.id}
                      style={{
                        padding: "8px 12px",
                        backgroundColor: "#2d1010",
                        border: "1px solid #7f1d1d",
                        borderRadius: 6,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <span style={{ color: "#fca5a5", fontSize: 11, fontFamily: "monospace", maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {n.data.label as string}
                      </span>
                      <button
                        onClick={() => {
                          // Quick repair heuristic: connect to first available node's ground or first port
                          const targetNode = nodes.find(other => other.id !== n.id);
                          if (targetNode) {
                            const newEdge: CircuitEdge = {
                              id: `wire-repair-${Date.now()}`,
                              source: n.id,
                              target: targetNode.id,
                              sourceHandle: n.data.ports && n.data.ports.length > 0 ? (n.data.ports[0] as any).id : undefined,
                              targetHandle: targetNode.data.ports && targetNode.data.ports.length > 0 ? (targetNode.data.ports[0] as any).id : undefined,
                              type: "circuitWire",
                              label: "repair",
                              data: {
                                from: { nodeId: n.id, portId: n.data.ports && n.data.ports.length > 0 ? (n.data.ports[0] as any).id : "" },
                                to: { nodeId: targetNode.id, portId: targetNode.data.ports && targetNode.data.ports.length > 0 ? (targetNode.data.ports[0] as any).id : "" },
                                color: WIRE_COLORS.signal,
                                label: "repaired",
                                wireType: "signal",
                              },
                              style: { stroke: WIRE_COLORS.signal, strokeWidth: 2, strokeDasharray: "4 4" },
                            };
                            addEdge(newEdge);
                            
                            // Remove orphaned flag
                            const useConnectionStoreLocal = require("./useConnectionStore").useConnectionStore;
                            useConnectionStoreLocal.getState().setNodes((prev: any) => 
                              prev.map((node: any) => node.id === n.id ? { ...node, data: { ...node.data, isOrphaned: false } } : node)
                            );
                          }
                        }}
                        style={{
                          backgroundColor: "#7f1d1d",
                          color: "white",
                          border: "none",
                          borderRadius: 4,
                          padding: "4px 8px",
                          fontSize: 10,
                          cursor: "pointer",
                          fontFamily: "monospace",
                        }}
                      >
                        Repair
                      </button>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
