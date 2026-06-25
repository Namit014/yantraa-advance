"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import {
    ReactFlow,
    Background,
    Controls,
    Node,
    Edge,
    useNodesState,
    useEdgesState,
    Handle,
    Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Loader2, Download, ChevronDown } from "lucide-react";
import dagre from "dagre";
import { toPng, toSvg } from 'html-to-image';
import jsPDF from 'jspdf';

// --- Custom Schematic Node ---
const SchematicNode = ({ data }: { data: any }) => {
    const { label, ports, hwType } = data;
    
    return (
        <div className="bg-neutral-900 border-2 border-neutral-700 rounded-lg min-w-[200px] shadow-xl overflow-hidden font-mono">
            <div className="bg-neutral-800 px-3 py-2 text-center border-b border-neutral-700">
                <span className="font-bold text-white text-sm block truncate px-2">{label}</span>
                <span className="block text-xs text-neutral-400 mt-1 uppercase">{hwType}</span>
            </div>
            
            <div className="flex flex-col gap-1 p-2">
                {ports && ports.map((port: any, idx: number) => {
                    const isLeft = port.type.includes("in") || port.type === "ground";
                    const isRight = port.type.includes("out") || port.type === "motor_phase";
                    // Fallback distribution
                    const isInputSide = isLeft || (!isRight && idx % 2 === 0);
                    
                    let color = "bg-neutral-400";
                    if (port.type === "power_out" || port.type === "power_in") color = "bg-red-500";
                    else if (port.type === "ground") color = "bg-neutral-300 border border-neutral-500";
                    else if (port.type.includes("pwm") || port.type.includes("i2c")) color = "bg-blue-400";
                    else if (port.type.includes("digital")) color = "bg-green-400";
                    else if (port.type.includes("analog")) color = "bg-orange-400";
                    else if (port.type === "motor_phase") color = "bg-purple-500";
                    else if (port.type.includes("mechanical")) color = "bg-neutral-100 border-2 border-dashed border-neutral-500";

                    return (
                        <div key={port.id} className={`flex relative items-center justify-between text-xs py-1 ${isInputSide ? 'flex-row' : 'flex-row-reverse'}`}>
                            {isInputSide && (
                                <>
                                <Handle
                                    type="target"
                                    position={Position.Left}
                                    id={port.id}
                                    className={`w-3 h-3 ${color} -left-[14px] !border-2 !border-neutral-900`}
                                />
                                <Handle
                                    type="source"
                                    position={Position.Left}
                                    id={port.id}
                                    className={`w-3 h-3 opacity-0`} // Invisible source handle to fix bi-directional Edge routing errors
                                />
                                </>
                            )}
                            <span className="text-neutral-300 px-2">{port.label || port.id}</span>
                            {!isInputSide && (
                                <>
                                <Handle
                                    type="source"
                                    position={Position.Right}
                                    id={port.id}
                                    className={`w-3 h-3 ${color} -right-[14px] !border-2 !border-neutral-900`}
                                />
                                <Handle
                                    type="target"
                                    position={Position.Right}
                                    id={port.id}
                                    className={`w-3 h-3 opacity-0`} // Invisible target handle
                                />
                                </>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

const nodeTypes = {
    schematicNode: SchematicNode,
};

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: any[], edges: any[], direction = 'LR') => {
    const isHorizontal = direction === 'LR';
    dagreGraph.setGraph({ rankdir: direction, ranksep: 350, nodesep: 150 });

    nodes.forEach((node) => {
        // Approximate width and height based on ports length
        const height = Math.max(100, (node.data?.ports?.length || 1) * 30 + 50);
        dagreGraph.setNode(node.id, { width: 220, height });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const layoutedNodes = nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        const height = Math.max(100, (node.data?.ports?.length || 1) * 30 + 50);
        
        return {
            ...node,
            targetPosition: isHorizontal ? 'left' : 'top',
            sourcePosition: isHorizontal ? 'right' : 'bottom',
            // Shift coordinates because dagre anchors on center-center, but ReactFlow anchors on top-left
            position: {
                x: nodeWithPosition.x - 110,
                y: nodeWithPosition.y - height / 2,
            },
        };
    });

    return { nodes: layoutedNodes, edges };
};

export function SchematicsWorkspace({ designData }: { designData?: any }) {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [exportOpen, setExportOpen] = useState(false);

    const handleExport = async (format: "png" | "svg" | "pdf") => {
        setExportOpen(false);
        const viewportNode = document.querySelector('.react-flow__viewport') as HTMLElement;
        if (!viewportNode) return;

        try {
            // Give a little time for dropdown to close visually
            await new Promise((r) => setTimeout(r, 100));

            // Compute exact bounding box of all nodes
            let minX = Infinity;
            let minY = Infinity;
            let maxX = -Infinity;
            let maxY = -Infinity;
            
            nodes.forEach((n: any) => {
                if (n.position.x < minX) minX = n.position.x;
                if (n.position.y < minY) minY = n.position.y;
                // Node width is ~220, height is variable but max ~400
                if (n.position.x + 350 > maxX) maxX = n.position.x + 350;
                if (n.position.y + 450 > maxY) maxY = n.position.y + 450;
            });
            
            if (minX === Infinity) return; // No nodes
            
            // Add padding
            minX -= 100;
            minY -= 100;
            maxX += 100;
            maxY += 100;
            
            const graphWidth = maxX - minX;
            const graphHeight = maxY - minY;
            
            // Adjust these parameters for high quality
            const options = {
                backgroundColor: '#171717',
                width: graphWidth,
                height: graphHeight,
                style: {
                    width: graphWidth.toString() + 'px',
                    height: graphHeight.toString() + 'px',
                    transform: `translate(${-minX}px, ${-minY}px) scale(1)`
                }
            };

            if (format === "png") {
                const dataUrl = await toPng(viewportNode, { ...options, pixelRatio: 2 });
                const link = document.createElement('a');
                link.download = 'robot_schematic.png';
                link.href = dataUrl;
                link.click();
            } else if (format === "svg") {
                const dataUrl = await toSvg(viewportNode, options);
                const link = document.createElement('a');
                link.download = 'robot_schematic.svg';
                link.href = dataUrl;
                link.click();
            } else if (format === "pdf") {
                const dataUrl = await toPng(viewportNode, { ...options, pixelRatio: 2 });
                const pdf = new jsPDF({
                    orientation: graphWidth > graphHeight ? 'landscape' : 'portrait',
                    unit: 'px',
                    format: [graphWidth, graphHeight]
                });
                pdf.addImage(dataUrl, 'PNG', 0, 0, graphWidth, graphHeight);
                pdf.save('robot_schematic.pdf');
            }
        } catch (error) {
            console.error("Failed to export diagram:", error);
        }
    };

    const generateSchematics = useCallback(async () => {
        if (!designData || !designData.subsystems) return;
        
        setIsLoading(true);
        setError(null);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/schematics/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ designData })
            });

            if (!response.ok) {
                throw new Error("Failed to generate deterministic schematics");
            }

            const data = await response.json();
            
            // Color edges
            const coloredEdges = data.edges.map((e: any) => {
                let stroke = "#9ca3af";
                let strokeDasharray = "0";
                if (e.data?.wireType === "power") stroke = "#ef4444"; // red
                else if (e.data?.wireType === "ground") stroke = "#e5e7eb"; // brighter gray
                else if (e.data?.wireType?.includes("pwm") || e.data?.wireType?.includes("i2c")) stroke = "#3b82f6"; // bright blue
                else if (e.data?.wireType?.includes("digital")) stroke = "#22c55e"; // bright green
                else if (e.data?.wireType?.includes("analog")) stroke = "#f97316"; // bright orange
                else if (e.data?.wireType === "motor_phase") stroke = "#a855f7"; // bright purple
                else if (e.data?.wireType === "mechanical") {
                    stroke = "#ffffff";
                    strokeDasharray = "8 8"; // dashed line
                }
                
                return {
                    ...e,
                    style: { stroke, strokeWidth: 4, strokeDasharray },
                };
            });

            // Perform Dagre Layout
            const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
                data.nodes || [],
                coloredEdges || [],
                'LR' // Left-to-Right layout
            );

            setNodes(layoutedNodes);
            setEdges(layoutedEdges);
        } catch (err: any) {
            console.error("Schematics generation error:", err);
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [designData, setNodes, setEdges]);

    useEffect(() => {
        if (designData) {
            generateSchematics();
        }
    }, [designData, generateSchematics]);

    if (!designData) {
        return (
            <div className="w-full h-full flex flex-col items-center justify-center bg-neutral-950 text-neutral-400">
                <p>Generate a design first to see the schematics.</p>
            </div>
        );
    }

    return (
        <div className="w-full h-full relative bg-neutral-950 rounded-xl overflow-hidden border border-neutral-800">
            {isLoading && (
                <div className="absolute inset-0 z-10 bg-neutral-950/80 flex flex-col items-center justify-center text-blue-500">
                    <Loader2 className="w-8 h-8 animate-spin mb-4" />
                    <p className="font-medium text-sm">Generating deterministic schematics...</p>
                </div>
            )}
            
            {error && (
                <div className="absolute inset-0 z-10 bg-neutral-950/90 flex flex-col items-center justify-center text-red-500 p-6">
                    <p className="font-bold mb-2">Schematics Generation Failed</p>
                    <p className="text-sm text-red-400 text-center">{error}</p>
                    <button 
                        onClick={generateSchematics}
                        className="mt-4 px-4 py-2 bg-red-900/50 hover:bg-red-900/80 rounded-lg text-white transition-colors"
                    >
                        Retry
                    </button>
                </div>
            )}
            
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                className="bg-neutral-900"
            >
                <Background color="#333" gap={16} />
                <Controls className="bg-neutral-800 border-neutral-700 fill-white" />
            </ReactFlow>

            {/* Export Menu Overlay */}
            <div className="absolute top-4 right-4 z-50">
                <div className="relative">
                    <button 
                        onClick={() => setExportOpen(!exportOpen)}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-black/50 border border-blue-500"
                    >
                        <Download className="w-4 h-4" />
                        Export
                        <ChevronDown className={`w-4 h-4 transition-transform ${exportOpen ? 'rotate-180' : ''}`} />
                    </button>
                    
                    {exportOpen && (
                        <div className="absolute top-full right-0 mt-2 w-48 bg-neutral-800 border border-neutral-700 rounded-lg shadow-xl overflow-hidden py-1">
                            <button 
                                onClick={() => handleExport("svg")}
                                className="w-full text-left px-4 py-2 text-sm text-neutral-200 hover:bg-neutral-700 hover:text-white transition-colors"
                            >
                                Export as SVG
                            </button>
                            <button 
                                onClick={() => handleExport("png")}
                                className="w-full text-left px-4 py-2 text-sm text-neutral-200 hover:bg-neutral-700 hover:text-white transition-colors"
                            >
                                Export as PNG
                            </button>
                            <button 
                                onClick={() => handleExport("pdf")}
                                className="w-full text-left px-4 py-2 text-sm text-neutral-200 hover:bg-neutral-700 hover:text-white transition-colors"
                            >
                                Export as PDF
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
