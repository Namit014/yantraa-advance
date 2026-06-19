"use client";

import { useEffect, useRef, useCallback } from "react";
import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
    ArrowUpIcon,
    Paperclip,
    PlusIcon,
} from "lucide-react";
import { MappingTab } from "./tabs/mapping-tab";
import { ConnectionTab } from "./tabs/connection-tab";
import { CADTab } from "./tabs/cad-tab";

interface UseAutoResizeTextareaProps {
    minHeight: number;
    maxHeight?: number;
}

function useAutoResizeTextarea({
    minHeight,
    maxHeight,
}: UseAutoResizeTextareaProps) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const adjustHeight = useCallback(
        (reset?: boolean) => {
            const textarea = textareaRef.current;
            if (!textarea) return;

            if (reset) {
                textarea.style.height = `${minHeight}px`;
                return;
            }

            // Temporarily shrink to get the right scrollHeight
            textarea.style.height = `${minHeight}px`;

            // Calculate new height
            const newHeight = Math.max(
                minHeight,
                Math.min(
                    textarea.scrollHeight,
                    maxHeight ?? Number.POSITIVE_INFINITY
                )
            );

            textarea.style.height = `${newHeight}px`;
        },
        [minHeight, maxHeight]
    );

    useEffect(() => {
        // Set initial height
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = `${minHeight}px`;
        }
    }, [minHeight]);

    // Adjust height on window resize
    useEffect(() => {
        const handleResize = () => adjustHeight();
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, [adjustHeight]);

    return { textareaRef, adjustHeight };
}

const formatAssistantResponse = (data: any) => {
    let text = `### 🤖 Yantraa Robot Design\n\n`;
    
    if (data.subsystems && data.subsystems.length > 0) {
        text += `#### Subsystems & Components\n`;
        data.subsystems.forEach((sub: any) => {
            text += `**${sub.name}**\n`;
            sub.components.forEach((comp: any) => {
                const rolePart = comp.role ? ` (${comp.role})` : "";
                const voltPart = comp.voltage ? `Voltage: ${comp.voltage}` : "";
                const interfacePart = comp.interface ? `Interface: ${comp.interface}` : "";
                
                let specs = "";
                if (voltPart && interfacePart) specs = ` — *${voltPart}, ${interfacePart}*`;
                else if (voltPart) specs = ` — *${voltPart}*`;
                else if (interfacePart) specs = ` — *${interfacePart}*`;
                
                text += `- **${comp.name}**${rolePart}${specs}\n`;
            });
            text += `\n`;
        });
    }
    
    if (data.bom && data.bom.length > 0) {
        text += `#### Bill of Materials (BOM)\n`;
        data.bom.forEach((item: any) => {
            text += `- ${item.name} (Qty: ${item.qty})\n`;
        });
        text += `\n`;
    }
    
    if (data.missing && data.missing.length > 0) {
        text += `⚠️ **Missing Components (Not in local knowledgebase):**\n`;
        data.missing.forEach((item: any) => {
            text += `- **${item.name}**: ${item.reason}\n`;
        });
        text += `\n`;
    }
    
    if (data.validation && data.validation.length > 0) {
        text += `🔍 **Validation Checks:**\n`;
        data.validation.forEach((val: any) => {
            const emoji = val.type === 'error' ? '❌' : '⚠️';
            text += `${emoji} *${val.type.toUpperCase()}:* ${val.message}\n`;
        });
        text += `\n`;
    }
    
    return text;
};

export function VercelV0Chat() {
    const [value, setValue] = useState("");
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant', content: string }[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<'mapping' | 'connection' | 'cad'>('mapping');
    const [cadPrompt, setCadPrompt] = useState<{ available: boolean, urls: string[] }>({ available: false, urls: [] });
    const [acceptedCadUrls, setAcceptedCadUrls] = useState<string[]>([]);
    const [robotDesign, setRobotDesign] = useState<any | null>(null);

    // Derive latest AI response and last user query to feed into MappingTab
    const latestAIResponse = [...messages].reverse().find(m => m.role === 'assistant')?.content ?? "";
    const latestUserQuery = [...messages].reverse().find(m => m.role === 'user')?.content ?? "";

    const { textareaRef, adjustHeight } = useAutoResizeTextarea({
        minHeight: 60,
        maxHeight: 200,
    });

    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading]);

    const handleSubmit = async () => {
        if (!value.trim() || isLoading) return;

        const userMessage = value.trim();
        setValue("");
        adjustHeight(true);
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL;
            const response = await fetch(`${apiUrl}/api/design`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "ngrok-skip-browser-warning": "true"
                },
                body: JSON.stringify({ query: userMessage })
            });

            if (!response.ok) {
                throw new Error("Failed to fetch response");
            }

            const data = await response.json();
            
            setRobotDesign(data);
            
            if (data.chat_reply) {
                setMessages(prev => [...prev, { role: 'assistant', content: data.chat_reply }]);
            } else {
                const formattedContent = formatAssistantResponse(data);
                setMessages(prev => [...prev, { role: 'assistant', content: formattedContent }]);
            }
            
            if (data.cad_available && data.cad_urls && data.cad_urls.length > 0) {
                setCadPrompt({ available: true, urls: data.cad_urls });
            } else if (data.cad_available && data.cad_url) {
                setCadPrompt({ available: true, urls: [data.cad_url] });
            } else {
                setCadPrompt({ available: false, urls: [] });
            }

        } catch (error) {
            console.log("Error asking question:", error instanceof Error ? error.message : String(error));
            setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error while processing your request." }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className={cn("flex w-full h-screen bg-black overflow-hidden transition-all duration-500", messages.length === 0 ? "justify-center" : "justify-start")}>
            {/* Main Chat Container */}
            <div className={cn("flex flex-col relative transition-all duration-500",
                messages.length === 0 ? "w-full max-w-4xl p-4 items-center" : "w-[400px] border-r border-neutral-800 bg-neutral-950 shrink-0"
            )}>
                {messages.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center space-y-8 w-full mt-20">
                        <h1 className="text-4xl font-bold text-white text-center">
                            Yantra AI
                        </h1>
                    </div>
                ) : (
                    <div className="flex-1 w-full overflow-y-auto space-y-6 pb-48 pt-8 px-4 flex flex-col">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={cn("flex w-full", msg.role === 'user' ? "justify-end" : "justify-start")}>
                                <div className={cn(
                                    "max-w-[80%] rounded-2xl px-5 py-4",
                                    msg.role === 'user'
                                        ? "bg-neutral-800 text-white"
                                        : "bg-transparent text-neutral-200"
                                )}>
                                    {msg.role === 'assistant' && (
                                        <div className="flex items-center gap-2 mb-2">
                                            <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold">
                                                Y
                                            </div>
                                            <span className="font-semibold text-sm text-neutral-400">Yantra AI</span>
                                        </div>
                                    )}
                                    <div className="whitespace-pre-wrap leading-relaxed text-[15px]">
                                        {msg.content}
                                    </div>
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div className="flex w-full justify-start">
                                <div className="bg-transparent text-neutral-200 rounded-2xl px-5 py-4 flex items-center gap-3">
                                    <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold animate-pulse">
                                        Y
                                    </div>
                                    <div className="flex gap-1 items-center">
                                        <div className="w-2 h-2 bg-neutral-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                        <div className="w-2 h-2 bg-neutral-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                        <div className="w-2 h-2 bg-neutral-500 rounded-full animate-bounce"></div>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                )}

                {/* Input Area */}
                <div className={cn("w-full transition-all duration-300",
                    messages.length === 0
                        ? "max-w-3xl pb-10"
                        : "absolute bottom-0 left-0 w-full p-4 bg-neutral-950/80 backdrop-blur-md border-t border-neutral-800 z-10"
                )}>
                    {cadPrompt.available && (
                        <div className="mb-4 bg-blue-900/40 border border-blue-500/50 rounded-xl p-4 flex flex-col gap-3 shadow-xl animate-in slide-in-from-bottom-2">
                            <p className="text-blue-100 text-sm font-medium">
                                {cadPrompt.urls.length > 1 
                                    ? `A highly detailed 3D CAD assembly with ${cadPrompt.urls.length} parts is available in our knowledge base. Do you want to view it?` 
                                    : "A highly detailed 3D CAD model for this robot is available in our knowledge base. Do you want to view it?"}
                            </p>
                            <div className="flex gap-2">
                                <button 
                                    onClick={() => {
                                        setAcceptedCadUrls(cadPrompt.urls);
                                        setActiveTab('cad');
                                        setCadPrompt({ available: false, urls: [] });
                                    }}
                                    className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded-lg text-sm transition-colors font-medium">
                                    Yes, View CAD
                                </button>
                                <button 
                                    onClick={() => setCadPrompt({ available: false, urls: [] })}
                                    className="bg-neutral-800 hover:bg-neutral-700 text-white px-4 py-1.5 rounded-lg text-sm transition-colors font-medium">
                                    No
                                </button>
                            </div>
                        </div>
                    )}
                    <div className="relative bg-neutral-900 rounded-xl border border-neutral-800 shadow-2xl">
                        <div className="overflow-y-auto">
                            <Textarea
                                ref={textareaRef}
                                value={value}
                                onChange={(e) => {
                                    setValue(e.target.value);
                                    adjustHeight();
                                }}
                                onKeyDown={handleKeyDown}
                                placeholder="Ask me anything..."
                                className={cn(
                                    "w-full px-4 py-4",
                                    "resize-none",
                                    "bg-transparent",
                                    "border-none",
                                    "text-white text-lg",
                                    "focus:outline-none",
                                    "focus-visible:ring-0 focus-visible:ring-offset-0",
                                    "placeholder:text-neutral-500 placeholder:text-lg",
                                    "min-h-[60px]"
                                )}
                                style={{ overflow: "hidden" }}
                                disabled={isLoading}
                            />
                        </div>

                        <div className="flex items-center justify-between p-3">
                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    className="group p-2 hover:bg-neutral-800 rounded-lg transition-colors flex items-center gap-1"
                                >
                                    <Paperclip className="w-4 h-4 text-white" />
                                    <span className="text-xs text-zinc-400 hidden group-hover:inline transition-opacity">
                                        Attach
                                    </span>
                                </button>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    className="px-2 py-1.5 rounded-lg text-sm text-zinc-400 transition-colors border border-dashed border-zinc-700 hover:border-zinc-600 hover:bg-zinc-800 flex items-center justify-between gap-1"
                                >
                                    <PlusIcon className="w-4 h-4" />
                                    Project
                                </button>
                                <button
                                    type="button"
                                    onClick={handleSubmit}
                                    disabled={isLoading || !value.trim()}
                                    className={cn(
                                        "px-1.5 py-1.5 rounded-lg text-sm transition-colors border flex items-center justify-between gap-1",
                                        value.trim() && !isLoading
                                            ? "bg-white text-black border-white hover:bg-neutral-200"
                                            : "text-zinc-500 border-zinc-800 bg-zinc-900"
                                    )}
                                >
                                    <ArrowUpIcon className="w-5 h-5" />
                                    <span className="sr-only">Send</span>
                                </button>
                            </div>
                        </div>
                    </div>
                    <div className="text-center mt-2 text-xs text-neutral-500">
                        Agentic AI can make mistakes. Consider verifying important information.
                    </div>
                </div>
            </div>

            {/* Right Side Content (Only visible when messages > 0) */}
            {messages.length > 0 && (
                <div className="flex-1 relative bg-[#0a0a0a] animate-in fade-in duration-500">
                    {/* Top Nav */}
<<<<<<< HEAD
                    <div className="absolute top-6 left-1/2 -translate-x-1/2 z-10 flex flex-col items-center gap-2">
                        <div className="flex items-center gap-6 px-6 py-3 bg-neutral-900/80 backdrop-blur-md border border-neutral-800 rounded-full shadow-2xl">
                            <div className="flex items-center gap-6 text-sm font-medium text-neutral-300">
                                <button onClick={() => setActiveTab('mapping')} className={cn("transition-colors", activeTab === 'mapping' ? "text-white" : "hover:text-white")}>Mapping</button>
                                <button onClick={() => setActiveTab('connection')} className={cn("transition-colors", activeTab === 'connection' ? "text-white" : "hover:text-white")}>Connection</button>
                                <button onClick={() => setActiveTab('cad')} className={cn("transition-colors", activeTab === 'cad' ? "text-white" : "hover:text-white")}>CAD</button>
                            </div>
=======
                    <div className="absolute top-6 left-1/2 -translate-x-1/2 z-10 flex items-center gap-6 px-6 py-3 bg-neutral-900/80 backdrop-blur-md border border-neutral-800 rounded-full shadow-2xl">
                        <div className="flex items-center gap-6 text-sm font-medium text-neutral-300">
                            <button onClick={() => setActiveTab('mapping')} className={cn("transition-colors", activeTab === 'mapping' ? "text-white" : "hover:text-white")}>Mapping</button>
                            <button onClick={() => setActiveTab('connection')} className={cn("transition-colors", activeTab === 'connection' ? "text-white" : "hover:text-white")}>Connection</button>
                            <button onClick={() => {
                                if (cadPrompt.available) {
                                    setAcceptedCadUrls(cadPrompt.urls);
                                    setCadPrompt({ available: false, urls: [] });
                                }
                                setActiveTab('cad');
                            }} className={cn("transition-colors", activeTab === 'cad' ? "text-white" : "hover:text-white")}>CAD</button>
>>>>>>> 073b64c08c1e57d69a1527fd490dd6a00da15243
                        </div>
                        {activeTab === 'connection' && (
                            <div className="text-[10px] text-blue-400 font-mono bg-blue-950/40 border border-blue-900/50 px-3 py-1 rounded-full animate-in fade-in slide-in-from-top-2">
                                Wiring components placed from the Mapping view
                            </div>
                        )}
                        {activeTab === 'cad' && (
                            <div className="text-[10px] text-purple-400 font-mono bg-purple-950/40 border border-purple-900/50 px-3 py-1 rounded-full animate-in fade-in slide-in-from-top-2">
                                3D Assembly generated from Mapping components
                            </div>
                        )}
                    </div>

                    {/* Tab Content */}
                    <div className="w-full h-full pt-20 pb-4 px-4 relative">
                        {activeTab === 'mapping' && <MappingTab aiResponse={latestAIResponse} currentQuery={latestUserQuery} designData={robotDesign} />}
                        {activeTab === 'connection' && <ConnectionTab currentQuery={latestUserQuery} designData={robotDesign} />}
                        {activeTab === 'cad' && (
                            <CADTab 
                                currentQuery={latestUserQuery} 
                                cadUrls={acceptedCadUrls.length > 0 ? acceptedCadUrls : (robotDesign?.cad_urls || (robotDesign?.cad_url ? [robotDesign.cad_url] : []))} 
                                designData={robotDesign} 
                                onGeneratedCad={(newUrl) => {
                                    setAcceptedCadUrls(prev => [...prev, newUrl]);
                                    if (robotDesign) {
                                        setRobotDesign((prev: any) => ({
                                            ...prev,
                                            cad_urls: [...(prev.cad_urls || []), newUrl],
                                            missing: prev.missing ? prev.missing.filter((m: any) => !newUrl.toLowerCase().includes(m.name.toLowerCase())) : []
                                        }));
                                    }
                                }}
                            />
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
