import React from 'react';
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, EdgeProps } from '@xyflow/react';

export default function AdvisorEdge({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    style = {},
    markerEnd,
    data,
}: EdgeProps) {
    const [edgePath, labelX, labelY] = getSmoothStepPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
    });

    const isPower = data?.wireType === "power" || data?.wireType === "ground";
    
    return (
        <>
            {/* The invisible thicker edge for easier clicking and hovering */}
            <path
                id={id + "_interaction"}
                className="react-flow__edge-interaction peer"
                d={edgePath}
                fill="none"
                strokeOpacity={0}
                strokeWidth={25}
            />
            {/* The visible edge */}
            <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
            
            {/* The Edge Label / Tooltip overlay */}
            <EdgeLabelRenderer>
                <div
                    style={{
                        position: 'absolute',
                        transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
                        pointerEvents: 'none',
                        zIndex: 10,
                    }}
                    className="nodrag nopan opacity-0 peer-hover:opacity-100 transition-opacity duration-200"
                >
                    <div className="bg-neutral-900 border border-neutral-700 text-white p-2 rounded shadow-xl text-xs flex flex-col gap-1 min-w-[150px]">
                        <div className="flex justify-between items-center border-b border-neutral-700 pb-1 mb-1">
                            <span className="font-bold text-blue-400 uppercase tracking-wider">{data?.wireType || "Connection"}</span>
                        </div>
                        <div className="flex items-center gap-1 text-neutral-300">
                            <span className="text-neutral-500 italic">Click for Engineering Analysis</span>
                        </div>
                    </div>
                </div>
            </EdgeLabelRenderer>
        </>
    );
}
