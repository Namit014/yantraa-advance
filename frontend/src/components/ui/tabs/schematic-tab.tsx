"use client";

import {
    MousePointer2,
    Hand,
    Type,
    PenLine,
    Square,
    Circle,
    AlignCenter,
    Undo2,
    Redo2,
    Minus,
    Plus,
} from "lucide-react";

export default function SchematicTab() {
    return (
        <div className="h-full w-full bg-white flex flex-col overflow-hidden">
            {/* Toolbar */}
            <div className="h-14 border-b bg-white flex items-center px-4 gap-3 shrink-0">
                <ToolButton active>
                    <MousePointer2 className="h-4 w-4" />
                </ToolButton>

                <ToolButton>
                    <Hand className="h-4 w-4" />
                </ToolButton>

                <ToolButton>
                    <Type className="h-4 w-4" />
                </ToolButton>

                <ToolButton>
                    <PenLine className="h-4 w-4" />
                </ToolButton>

                <ToolButton>
                    <Square className="h-4 w-4" />
                </ToolButton>

                <ToolButton>
                    <Circle className="h-4 w-4" />
                </ToolButton>

                <ToolButton>
                    <AlignCenter className="h-4 w-4" />
                </ToolButton>

                <div className="w-px h-6 bg-border mx-1" />

                <ToolButton>
                    <Undo2 className="h-4 w-4" />
                </ToolButton>

                <ToolButton>
                    <Redo2 className="h-4 w-4" />
                </ToolButton>

                <div className="flex-1" />

                {/* Zoom */}
                <div className="flex items-center border rounded-lg overflow-hidden">
                    <button className="px-3 py-2 hover:bg-muted">
                        <Minus className="h-4 w-4" />
                    </button>

                    <div className="px-4 text-sm font-medium">100%</div>

                    <button className="px-3 py-2 hover:bg-muted">
                        <Plus className="h-4 w-4" />
                    </button>
                </div>
            </div>

            {/* Workspace */}
            <div className="relative flex-1 overflow-hidden bg-[#fafafa]">
                {/* Dot Grid */}
                <div
                    className="absolute inset-0"
                    style={{
                        backgroundImage:
                            "radial-gradient(circle, rgba(0,0,0,0.15) 1px, transparent 1px)",
                        backgroundSize: "20px 20px",
                    }}
                />

                {/* Future schematic elements will go here */}
                <div className="absolute inset-0 z-10" />
            </div>
        </div>
    );
}

function ToolButton({
    children,
    active = false,
}: {
    children: React.ReactNode;
    active?: boolean;
}) {
    return (
        <button
            className={`
        h-9 w-9 rounded-md flex items-center justify-center transition-colors
        ${active
                    ? "bg-muted border"
                    : "hover:bg-muted/70"
                }
      `}
        >
            {children}
        </button>
    );
}