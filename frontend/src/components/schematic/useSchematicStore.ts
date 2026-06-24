import { create } from "zustand";

export interface Point {
    x: number;
    y: number;
}

export interface SchematicElement {
    id: string;
    type: "line" | "rect" | "circle" | "text" | "wire" | "component" | "ic_block";
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
    
    // For AI generated canonical elements
    partId?: string;
    componentId?: string;
    designator?: string;
    netId?: string;
    pinStubs?: any[];
    highlightErc?: boolean;
}

export interface ERCIssue {
    severity: "info" | "warning" | "error";
    message: string;
    component_id?: string;
    net_name?: string;
}

export interface PowerBudget {
    total_mA: number;
    margin_pct: number;
    runtime_hrs: number;
    warnings: string[];
}

export interface Confidence {
    subsystems: Record<string, number>;
    overall: number;
}

interface SchematicStore {
    // Canonical data
    netlist: any | null;
    
    // View data
    elements: SchematicElement[];
    history: SchematicElement[][];
    historyIdx: number;
    
    // Meta state
    isGenerating: boolean;
    generatingStep: string;
    generationHash: string;
    fallbackUsed: boolean;
    
    // Validation state
    ercIssues: ERCIssue[];
    preErcIssues: ERCIssue[];
    powerBudget: PowerBudget | null;
    confidence: Confidence | null;
    assumptions: string[];
    error: string | null;
    
    partsDb: any[] | null;
    
    // Actions
    setElements: (els: SchematicElement[]) => void;
    pushHistory: (els: SchematicElement[]) => void;
    undo: () => void;
    redo: () => void;
    fetchPartsDb: () => Promise<void>;
    generate: (designData: any, query: string) => Promise<void>;
    regenerate: (designData: any, query: string, confirmed: boolean) => Promise<void>;
}

export const useSchematicStore = create<SchematicStore>((set, get) => ({
    netlist: null,
    elements: [],
    history: [[]],
    historyIdx: 0,
    isGenerating: false,
    generatingStep: "",
    generationHash: "",
    fallbackUsed: false,
    ercIssues: [],
    preErcIssues: [],
    powerBudget: null,
    confidence: null,
    assumptions: [],
    error: null,
    partsDb: null,
    
    setElements: (els) => set({ elements: els }),
    
    pushHistory: (els) => {
        const { history, historyIdx } = get();
        const newHistory = history.slice(0, historyIdx + 1);
        newHistory.push(els);
        // keep last 50
        if (newHistory.length > 50) newHistory.shift();
        set({ 
            elements: els, 
            history: newHistory, 
            historyIdx: newHistory.length - 1 
        });
    },
    
    undo: () => {
        const { history, historyIdx } = get();
        if (historyIdx > 0) {
            set({
                historyIdx: historyIdx - 1,
                elements: history[historyIdx - 1]
            });
        }
    },
    
    redo: () => {
        const { history, historyIdx } = get();
        if (historyIdx < history.length - 1) {
            set({
                historyIdx: historyIdx + 1,
                elements: history[historyIdx + 1]
            });
        }
    },
    
    fetchPartsDb: async () => {
        if (get().partsDb) return;
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const res = await fetch(`${API_URL}/api/parts-db`);
            if (res.ok) {
                const data = await res.json();
                set({ partsDb: data });
            }
        } catch (e) {
            console.error("Failed to fetch parts DB", e);
        }
    },
    
    generate: async (designData, query) => {
        await get().fetchPartsDb();
        const state = get();
        
        // Simple hash check to avoid redundant generation
        const hashInput = JSON.stringify(designData || {}) + query + (state.partsDb?.length || 0);
        
        if (state.generationHash === hashInput && state.elements.length > 0) {
            return; // Cache hit
        }
        
        set({ isGenerating: true, error: null, generatingStep: "Extracting specification..." });
        
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const res = await fetch(`${API_URL}/api/schematic/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query, designData })
            });
            
            if (!res.ok) throw new Error("API error during generation");
            
            const data = await res.json();
            
            // Atomic history push for the whole generation
            get().pushHistory(data.elements);
            
            set({
                netlist: data.netlist,
                ercIssues: data.erc_issues,
                preErcIssues: data.pre_erc_issues,
                powerBudget: data.power_budget,
                confidence: data.confidence,
                assumptions: data.assumptions,
                generationHash: hashInput,
                fallbackUsed: data.fallback_used,
                isGenerating: false
            });
            
        } catch (e: any) {
            set({ error: e.message || "Failed to generate schematic", isGenerating: false });
        }
    },
    
    regenerate: async (designData, query, confirmed) => {
        if (!confirmed && get().elements.length > 0) {
            // Caller should handle confirmation dialog
            return;
        }
        // Force hash clear to regenerate
        set({ generationHash: "" });
        await get().generate(designData, query);
    }
}));
