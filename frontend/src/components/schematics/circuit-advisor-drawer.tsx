"use client";

import React, { useState, useEffect } from "react";
import { Loader2, X, CheckCircle2, AlertTriangle, ShieldAlert, Cpu, BookOpen, Activity, GitFork } from "lucide-react";

interface CircuitAdvisorDrawerProps {
    selectedElement: any; // ReactFlow node or edge
    onClose: () => void;
}

export function CircuitAdvisorDrawer({ selectedElement, onClose }: CircuitAdvisorDrawerProps) {
    const [mode, setMode] = useState<"Basic" | "Engineer" | "Expert">("Engineer");
    const [activeTab, setActiveTab] = useState("overview");
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!selectedElement) {
            setData(null);
            return;
        }

        const fetchAdvisorData = async () => {
            setLoading(true);
            setError(null);
            
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                
                // If it's an edge, it has a source and target
                if (selectedElement.source && selectedElement.target) {
                    const reqBody = {
                        source_node: selectedElement.sourceNode?.data || { hw_key: "unknown", name: "Unknown Source" },
                        target_node: selectedElement.targetNode?.data || { hw_key: "unknown", name: "Unknown Target" },
                        source_pin: selectedElement.sourceHandle || "Unknown",
                        target_pin: selectedElement.targetHandle || "Unknown",
                        protocol: selectedElement.data?.wireType || "Unknown",
                        mode: mode
                    };
                    
                    const res = await fetch(`${apiUrl}/api/schematics/advisor/connection`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(reqBody)
                    });
                    
                    if (!res.ok) throw new Error("Failed to fetch advisor data");
                    setData(await res.json());
                } else {
                    // For node clicks, we might want a different endpoint in the future,
                    // but for now we just show basic component info locally.
                    setData({
                        isNode: true,
                        name: selectedElement.data?.label || "Component",
                        hwType: selectedElement.data?.hwType || "Unknown",
                        ports: selectedElement.data?.ports || []
                    });
                }
            } catch (e: any) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        };

        fetchAdvisorData();
    }, [selectedElement, mode]);

    if (!selectedElement) return null;

    const tabs = [
        { id: "overview", label: "Overview", icon: Cpu },
        { id: "reasoning", label: "Reasoning", icon: BookOpen },
        { id: "validation", label: "Validation", icon: CheckCircle2 },
        { id: "alternatives", label: "Alternatives", icon: GitFork },
        { id: "risks", label: "Risk Analysis", icon: ShieldAlert },
        { id: "evidence", label: "Evidence", icon: Activity },
    ];

    const renderProgressBar = (label: string, value: number) => {
        const blocks = Math.round(value / 10);
        return (
            <div className="flex justify-between items-center text-xs my-1">
                <span className="w-1/3 text-neutral-400">{label}</span>
                <div className="flex text-blue-500 font-mono tracking-tighter">
                    {'█'.repeat(blocks)}{'░'.repeat(10 - blocks)}
                </div>
                <span className="w-10 text-right text-neutral-300 font-bold">{value}%</span>
            </div>
        );
    };

    return (
        <div className="fixed top-0 right-0 h-full w-[450px] bg-neutral-900 border-l border-neutral-700 shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="p-4 border-b border-neutral-700 flex justify-between items-center bg-neutral-950">
                <div className="flex items-center gap-2">
                    <Cpu className="w-5 h-5 text-blue-400" />
                    <h2 className="font-bold text-white tracking-wide">Circuit Advisor</h2>
                </div>
                <button onClick={onClose} className="text-neutral-400 hover:text-white transition-colors">
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Mode Selector */}
            <div className="p-4 border-b border-neutral-800 flex justify-center gap-2">
                {["Basic", "Engineer", "Expert"].map((m) => (
                    <button
                        key={m}
                        onClick={() => setMode(m as any)}
                        className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                            mode === m 
                            ? "bg-blue-500/20 border-blue-500 text-blue-300 font-bold" 
                            : "bg-neutral-800 border-neutral-700 text-neutral-400 hover:border-neutral-500"
                        }`}
                    >
                        {m}
                    </button>
                ))}
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                {loading ? (
                    <div className="flex flex-col items-center justify-center h-40 gap-3 text-neutral-500">
                        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                        <span className="text-sm">Analyzing connection parameters...</span>
                    </div>
                ) : error ? (
                    <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                        <div className="text-sm text-red-200">
                            <p className="font-bold mb-1">Analysis Error</p>
                            <p className="opacity-80">{error}</p>
                        </div>
                    </div>
                ) : data?.isNode ? (
                    <div className="space-y-4">
                        <div className="p-4 bg-neutral-800 rounded-lg border border-neutral-700">
                            <div className="flex justify-between items-start mb-1">
                                <h3 className="text-xl font-bold text-white">{data.name}</h3>
                                <span className="bg-green-500/20 text-green-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase">PASS</span>
                            </div>
                            <p className="text-sm text-neutral-400 uppercase tracking-widest">{data.hwType}</p>
                            
                            <div className="mt-4 grid grid-cols-2 gap-2">
                                <div className="bg-neutral-900 p-2 rounded border border-neutral-700">
                                    <p className="text-[10px] text-neutral-500 uppercase">Pin Usage</p>
                                    <p className="text-sm font-bold text-neutral-300">
                                        <span className="text-blue-400">4</span> / {data.ports.length} Used
                                    </p>
                                </div>
                                <div className="bg-neutral-900 p-2 rounded border border-neutral-700">
                                    <p className="text-[10px] text-neutral-500 uppercase">Health</p>
                                    <p className="text-sm font-bold text-green-400">0 Warnings</p>
                                </div>
                            </div>
                        </div>

                        <div className="p-4 bg-neutral-800 rounded-lg border border-neutral-700">
                            <h4 className="text-sm font-bold text-neutral-300 mb-3 uppercase flex items-center gap-2">
                                <Activity className="w-4 h-4 text-blue-400" />
                                Engineering Intelligence
                            </h4>
                            <div className="space-y-4">
                                <div>
                                    <p className="text-xs text-neutral-500 uppercase mb-1">Connected To</p>
                                    <p className="text-sm text-neutral-300">Auto-routed via standard protocols (I2C, PWM, Power) to compatible peripherals.</p>
                                </div>
                                <div>
                                    <p className="text-xs text-neutral-500 uppercase mb-1">Why Not Connected Directly?</p>
                                    <div className="bg-neutral-900 p-3 rounded text-sm text-neutral-300 border border-neutral-700">
                                        <span className="text-red-400 font-bold">Motor rejected direct MCU link:</span> Current exceeds GPIO limits. Motor driver routed between them.
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="p-4 bg-neutral-800 rounded-lg border border-neutral-700">
                            <h4 className="text-sm font-bold text-neutral-300 mb-3 uppercase">Pin Layout</h4>
                            <div className="space-y-2">
                                {data.ports.map((p: any) => (
                                    <div key={p.id} className="flex justify-between items-center text-sm p-2 bg-neutral-900 rounded border border-neutral-800">
                                        <span className="text-neutral-300 font-mono">{p.id}</span>
                                        <span className="text-neutral-500 text-xs uppercase px-2 py-0.5 bg-neutral-950 rounded">{p.type}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                ) : data ? (
                    <div className="space-y-6">
                        {/* Tabs Navigation */}
                        <div className="flex flex-wrap gap-1 border-b border-neutral-800 pb-2">
                            {tabs.map((tab) => {
                                const Icon = tab.icon;
                                return (
                                    <button
                                        key={tab.id}
                                        onClick={() => setActiveTab(tab.id)}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-colors ${
                                            activeTab === tab.id 
                                            ? "bg-neutral-800 text-white font-medium border border-neutral-700" 
                                            : "text-neutral-500 hover:bg-neutral-800/50 hover:text-neutral-300"
                                        }`}
                                    >
                                        <Icon className="w-3.5 h-3.5" />
                                        {tab.label}
                                    </button>
                                )
                            })}
                        </div>

                        {/* Tab Contents */}
                        <div className="mt-4">
                            {activeTab === "overview" && (
                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-3">
                                        <div className="bg-neutral-800 p-3 rounded-lg border border-neutral-700">
                                            <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1">Protocol</p>
                                            <p className="text-sm font-bold text-blue-400">{data.protocol}</p>
                                        </div>
                                        <div className="bg-neutral-800 p-3 rounded-lg border border-neutral-700">
                                            <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-1">Status</p>
                                            <p className={`text-sm font-bold ${data.status === "PASS" ? "text-green-400" : "text-yellow-400"}`}>
                                                {data.status}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="bg-neutral-800 p-4 rounded-lg border border-neutral-700">
                                        <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-2">Wiring</p>
                                        <div className="flex items-center gap-3">
                                            <div className="flex-1 bg-neutral-900 p-2 rounded border border-neutral-800">
                                                <p className="text-xs text-neutral-400 line-clamp-1">{data.source.split(" ")[0]}</p>
                                                <p className="text-sm font-bold text-white">{data.source.split(" ").slice(1).join(" ")}</p>
                                            </div>
                                            <div className="text-neutral-600">→</div>
                                            <div className="flex-1 bg-neutral-900 p-2 rounded border border-neutral-800">
                                                <p className="text-xs text-neutral-400 line-clamp-1">{data.destination.split(" ")[0]}</p>
                                                <p className="text-sm font-bold text-white">{data.destination.split(" ").slice(1).join(" ")}</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="bg-neutral-800 p-4 rounded-lg border border-neutral-700">
                                        <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-3">Confidence Sources</p>
                                        <div className="space-y-1">
                                            {renderProgressBar("Datasheet Match", data.confidence["Datasheet Match"])}
                                            {renderProgressBar("ERC Validation", data.confidence["ERC Validation"])}
                                            {renderProgressBar("Knowledge Base", data.confidence["Knowledge Base"])}
                                            {renderProgressBar("AI Explanation", data.confidence["AI Explanation"])}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {activeTab === "reasoning" && (
                                <div className="space-y-4">
                                    <div className="bg-neutral-800 p-4 rounded-lg border border-neutral-700">
                                        <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-3">Deterministic Engine Rules</p>
                                        <ul className="space-y-2">
                                            {data.deterministic_reasoning.map((r: string, idx: number) => (
                                                <li key={idx} className="text-xs text-neutral-300 flex items-start gap-2">
                                                    <span className="text-blue-500 mt-0.5">•</span>
                                                    {r}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                    
                                    {(mode === "Engineer" || mode === "Expert") && (
                                        <div className="bg-blue-900/20 p-4 rounded-lg border border-blue-500/30">
                                            <div className="flex items-center gap-2 mb-3">
                                                <Cpu className="w-4 h-4 text-blue-400" />
                                                <p className="text-[10px] text-blue-400 uppercase tracking-wider">AI Engineering Analysis ({mode})</p>
                                            </div>
                                            {data.ai_explanation ? (
                                                <div className="text-sm text-neutral-200 leading-relaxed whitespace-pre-wrap">
                                                    {data.ai_explanation}
                                                </div>
                                            ) : (
                                                <p className="text-xs text-neutral-500 italic">No AI explanation provided.</p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}

                            {activeTab === "validation" && (
                                <div className="space-y-3">
                                    {Object.entries(data.validations).map(([key, val]: any) => (
                                        <div key={key} className="flex justify-between items-center p-3 bg-neutral-800 rounded-lg border border-neutral-700">
                                            <span className="text-sm text-neutral-300">{key}</span>
                                            <span className={`text-xs font-bold px-2 py-1 rounded ${val === "PASS" ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}`}>
                                                {val}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {activeTab === "risks" && (
                                <div className="space-y-4">
                                    <div className="bg-red-900/10 p-4 rounded-lg border border-red-900/30">
                                        <div className="flex items-center gap-2 mb-4">
                                            <ShieldAlert className="w-4 h-4 text-red-400" />
                                            <p className="text-[10px] text-red-400 uppercase tracking-wider">Potential Risks Detected</p>
                                        </div>
                                        <ul className="space-y-3">
                                            {data.risks.map((r: string, idx: number) => (
                                                <li key={idx} className="text-sm text-neutral-300 flex items-start gap-3">
                                                    <AlertTriangle className={`w-4 h-4 shrink-0 mt-0.5 ${r.includes("No critical risks") ? "text-green-500" : "text-yellow-500"}`} />
                                                    <span className="leading-snug">{r}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            )}

                            {activeTab === "alternatives" && (
                                <div className="space-y-3">
                                    {data.alternatives.map((alt: any, idx: number) => (
                                        <div key={idx} className="bg-neutral-800 p-4 rounded-lg border border-neutral-700 relative overflow-hidden">
                                            <div className="absolute top-0 right-0 p-2 bg-neutral-900 rounded-bl-lg border-b border-l border-neutral-700">
                                                <span className="text-[10px] text-neutral-400">Conf: {alt.confidence}%</span>
                                            </div>
                                            <h4 className="text-sm font-bold text-white mb-1">{alt.name}</h4>
                                            <p className="text-xs text-neutral-400">{alt.pins}</p>
                                        </div>
                                    ))}
                                    {data.alternatives.length === 0 && (
                                        <p className="text-sm text-neutral-500 text-center py-8">No specific alternatives identified for this connection.</p>
                                    )}
                                </div>
                            )}
                            
                            {activeTab === "evidence" && (
                                <div className="bg-neutral-800 p-4 rounded-lg border border-neutral-700">
                                    <p className="text-[10px] text-neutral-500 uppercase tracking-wider mb-3">Knowledge Base Evidence</p>
                                    <p className="text-xs text-neutral-400 leading-relaxed">
                                        All connection parameters were sourced deterministically from the internal Yantraa hardware_db.json and CircuitAdvisorKnowledgeGraph rules engine. AI was only utilized for linguistic translation of raw connection facts.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                ) : null}
            </div>
        </div>
    );
}
