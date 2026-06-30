import { Handle, Position } from "@xyflow/react";
import type { SchematicNodeData } from "./useSchematicsStore";

export function SchematicNodeComponent({ data }: { data: SchematicNodeData }) {
    const pins = data.pins || [];

    const posMap: Record<string, Position> = {
        top: Position.Top,
        bottom: Position.Bottom,
        left: Position.Left,
        right: Position.Right,
    };

    return (
        <div style={{
            background: "#000000",
            border: "2px solid #FFFFFF",
            borderRadius: "4px",
            minWidth: "140px",
            minHeight: "120px",
            color: "#FFFFFF",
            fontFamily: "monospace",
            display: "flex",
            flexDirection: "column",
            position: "relative"
        }}>
            <div style={{
                background: "#111111",
                padding: "6px 8px",
                borderBottom: "2px solid #FFFFFF",
                fontSize: "12px",
                fontWeight: "bold",
                textAlign: "center"
            }}>
                {data.label}
            </div>
            
            <div style={{ padding: "8px", fontSize: "10px", flex: 1, position: "relative" }}>
                {pins.map((pin) => {
                    // Distribute pins evenly
                    const sidePins = pins.filter(p => p.side === pin.side);
                    const sideIndex = sidePins.findIndex(p => p.id === pin.id);
                    const offsetPercent = (100 / (sidePins.length + 1)) * (sideIndex + 1);
                    
                    const isHorizontal = pin.side === "top" || pin.side === "bottom";
                    
                    // Pin label position
                    const labelStyle: React.CSSProperties = {
                        position: "absolute",
                    };
                    
                    if (pin.side === "left") {
                        labelStyle.left = "4px";
                        labelStyle.top = `${offsetPercent}%`;
                        labelStyle.transform = "translateY(-50%)";
                    } else if (pin.side === "right") {
                        labelStyle.right = "4px";
                        labelStyle.top = `${offsetPercent}%`;
                        labelStyle.transform = "translateY(-50%)";
                        labelStyle.textAlign = "right";
                    } else if (pin.side === "top") {
                        labelStyle.top = "4px";
                        labelStyle.left = `${offsetPercent}%`;
                        labelStyle.transform = "translateX(-50%)";
                    } else if (pin.side === "bottom") {
                        labelStyle.bottom = "4px";
                        labelStyle.left = `${offsetPercent}%`;
                        labelStyle.transform = "translateX(-50%)";
                    }
                    
                    return (
                        <div key={pin.id}>
                            <div style={labelStyle}>{pin.label}</div>
                            {/* We output both source and target handles for every pin so edges can connect either way */}
                            <Handle
                                type="source"
                                position={posMap[pin.side] || Position.Right}
                                id={pin.id}
                                style={{
                                    background: "#FFFFFF",
                                    width: "6px",
                                    height: "6px",
                                    borderRadius: "0", // Square pins for classic look
                                    border: "1px solid #000000",
                                    ...(isHorizontal ? { left: `${offsetPercent}%` } : { top: `${offsetPercent}%` })
                                }}
                            />
                            <Handle
                                type="target"
                                position={posMap[pin.side] || Position.Right}
                                id={pin.id}
                                style={{
                                    background: "#FFFFFF",
                                    width: "6px",
                                    height: "6px",
                                    borderRadius: "0",
                                    border: "1px solid #000000",
                                    ...(isHorizontal ? { left: `${offsetPercent}%` } : { top: `${offsetPercent}%` })
                                }}
                            />
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
