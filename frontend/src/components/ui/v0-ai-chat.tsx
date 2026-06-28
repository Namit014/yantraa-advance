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
    const [isThinking, setIsThinking] = useState(false);
    const [statusMessage, setStatusMessage] = useState("");
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
        setIsThinking(true);
        setStatusMessage("Reading your prompt...");

        const statusStages = [
            "Reading your prompt...",
            "Mapping subsystems...",
            "Selecting components...",
            "Building your BOM..."
        ];
        let statusIndex = 0;
        const intervalId = setInterval(() => {
            statusIndex = (statusIndex + 1) % statusStages.length;
            setStatusMessage(statusStages[statusIndex]);
        }, 1800);

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://api.yantraa.tech";
            // We need to keep track of the complete message history to send to the backend
            const completeMessages = [...messages, { role: 'user' as const, content: userMessage }];
            
            const response = await fetch(`${apiUrl}/api/design/stream`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "ngrok-skip-browser-warning": "true"
                },
                body: JSON.stringify({
                    query: userMessage,
                    messages: completeMessages
                })
            });

            if (!response.ok) {
                throw new Error("Failed to start stream");
            }

            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let botMessage = "";
            let isFirstToken = true;

            // Append empty message bubble for the assistant's stream response
            setMessages(prev => [...prev, { role: 'assistant', content: "" }]);

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (!line.trim()) continue;
                    const cleanLine = line.replace(/^data:\s*/, "").trim();
                    if (!cleanLine) continue;

                    try {
                        const eventData = JSON.parse(cleanLine);
                        if (eventData.type === "token") {
                            if (isFirstToken) {
                                isFirstToken = false;
                                setIsThinking(false);
                                clearInterval(intervalId);
                            }
                            botMessage += eventData.content;
                            setMessages(prev => {
                                const updated = [...prev];
                                updated[updated.length - 1] = { role: 'assistant', content: botMessage };
                                return updated;
                            });
                        } else if (eventData.type === "status") {
                            setStatusMessage(eventData.content);
                        } else if (eventData.type === "final_design") {
                            const design = eventData.design;
                            setRobotDesign(design);

                            if (design.chat_reply) {
                                botMessage = design.chat_reply;
                            } else {
                                botMessage = formatAssistantResponse(design);
                            }

                            setMessages(prev => {
                                const updated = [...prev];
                                updated[updated.length - 1] = { role: 'assistant', content: botMessage };
                                return updated;
                            });

                            if (design.cad_available && design.cad_urls && design.cad_urls.length > 0) {
                                setCadPrompt({ available: true, urls: design.cad_urls });
                                setAcceptedCadUrls(design.cad_urls);
                                setActiveTab("cad");
                            } else if (design.cad_available && design.cad_url) {
                                setCadPrompt({ available: true, urls: [design.cad_url] });
                                setAcceptedCadUrls([design.cad_url]);
                                setActiveTab("cad");
                            } else {
                                setCadPrompt({ available: false, urls: [] });
                                setActiveTab("connection");
                            }

                            setIsThinking(false);
                            clearInterval(intervalId);
                        }
                    } catch (err) {
                        console.log("Error parsing chunk:", err);
                    }
                }
            }

        } catch (error) {
            console.log("Error asking question:", error instanceof Error ? error.message : String(error));
            clearInterval(intervalId);
            setMessages(prev => {
                const updated = [...prev];
                // Replace the last assistant message (which might be empty) with error text
                if (updated.length > 0 && updated[updated.length - 1].role === 'assistant') {
                    updated[updated.length - 1] = { role: 'assistant', content: "Sorry, I encountered an error while processing your request." };
                } else {
                    updated.push({ role: 'assistant', content: "Sorry, I encountered an error while processing your request." });
                }
                return updated;
            });
        } finally {
            setIsLoading(false);
            setIsThinking(false);
            clearInterval(intervalId);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className={cn("flex w-full h-screen bg-[#0A0A0A] overflow-hidden transition-all duration-500", messages.length === 0 ? "justify-center" : "justify-start")}>
            {/* Main Chat Container */}
            <div className={cn("flex flex-col relative transition-all duration-500",
                messages.length === 0 ? "w-full max-w-4xl p-4 items-center" : "w-[400px] border-r border-[#2A2A2A] bg-[#0A0A0A] shrink-0"
            )}>
                {messages.length === 0 ? (
                    <div className="flex-1 flex flex-col items-center justify-center space-y-4 w-full mt-20">
                        {/* pulsing bot avatar brand icon */}
                        <div className="mb-2 flex flex-col items-center gap-3">
                            <div className="w-16 h-16 rounded-2xl bg-[#1E1E1E] border border-[#2A2A2A] flex items-center justify-center text-xl font-bold text-[#F0F0F0] animate-pulse shadow-2xl">
                                Y
                            </div>
                            <span className="text-xs font-semibold tracking-widest text-[#555555] uppercase">Yantraa co-pilot</span>
                        </div>
                        <h1 className="text-3xl font-medium text-[#F0F0F0] text-center leading-tight">
                            Hey, I'm Yantraa 👋
                        </h1>
                        <p className="text-sm text-[#888888] text-center max-w-md">
                            Tell me what you're building and I'll generate your BOM, wiring diagram, and more.
                        </p>
                        
                        <div className="flex flex-wrap gap-2 justify-center mt-6 max-w-lg">
                            {[
                                "Design a warehouse AGV",
                                "Build a line-following robot",
                                "Inspection drone for pipelines",
                                "Autonomous delivery robot for campus"
                            ].map(chip => (
                                <button
                                    key={chip}
                                    onClick={() => {
                                        setValue(chip);
                                        setTimeout(() => {
                                            if (textareaRef.current) {
                                                textareaRef.current.style.height = 'auto';
                                                textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
                                            }
                                        }, 50);
                                    }}
                                    className="px-3 py-2 bg-[#1E1E1E] hover:bg-[#252525] border border-[#2A2A2A] rounded-xl text-xs text-[#888888] hover:text-[#F0F0F0] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-md"
                                >
                                    {chip}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="flex-1 w-full overflow-y-auto space-y-6 pb-48 pt-8 px-4 flex flex-col">
                        {messages.map((msg, idx) => {
                            if (msg.role === 'assistant' && !msg.content) return null;
                            return (
                                <div key={idx} className={cn("flex w-full", msg.role === 'user' ? "justify-end" : "justify-start")}>
                                    <div className={cn(
                                        "max-w-[82%] rounded-2xl px-4 py-3",
                                        msg.role === 'user'
                                            ? "bg-[#1E1E1E] border border-[#2A2A2A] text-[#F0F0F0]"
                                            : "bg-transparent text-[#F0F0F0]"
                                    )}>
                                        {msg.role === 'assistant' && (
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="w-5 h-5 rounded-md bg-[#1E1E1E] border border-[#2A2A2A] flex items-center justify-center text-[10px] font-bold text-[#F0F0F0]">
                                                    Y
                                                </div>
                                                <span className="font-medium text-xs text-[#888888]">Yantraa AI</span>
                                            </div>
                                        )}
                                        <div className="whitespace-pre-wrap leading-relaxed text-[14px] text-[#F0F0F0]">
                                            {msg.content}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                        {isLoading && (!messages.length || messages[messages.length - 1].role !== 'assistant' || isThinking || !messages[messages.length - 1].content) && (
                            <div className="flex w-full justify-start">
                                <div className="bg-transparent text-[#F0F0F0] rounded-2xl px-4 py-3 flex flex-col gap-2">
                                    <div className="flex items-center gap-3">
                                        <div className="w-5 h-5 rounded-md bg-[#1E1E1E] border border-[#2A2A2A] flex items-center justify-center text-[10px] font-bold text-[#F0F0F0] animate-pulse">
                                            Y
                                        </div>
                                        <div className="flex gap-1 items-center">
                                            <div className="w-1.5 h-1.5 bg-[#555555] rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                            <div className="w-1.5 h-1.5 bg-[#555555] rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                            <div className="w-1.5 h-1.5 bg-[#555555] rounded-full animate-bounce"></div>
                                        </div>
                                    </div>
                                    {isThinking && (
                                        <div className="text-xs text-[#888888] font-mono pl-8 animate-pulse">
                                            {statusMessage}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                )}

                {/* Input Area */}
                <div className={cn("w-full transition-all duration-300",
                    messages.length === 0
                        ? "max-w-[580px] pb-10"
                        : "absolute bottom-0 left-0 w-full p-4 bg-[#0A0A0A]/90 backdrop-blur-md border-t border-[#2A2A2A] z-10"
                )}>
                    {cadPrompt.available && (
                        <div className="mb-3 bg-[#1E1E1E] border border-[#2A2A2A] rounded-xl p-4 flex flex-col gap-3 animate-in slide-in-from-bottom-2">
                            <p className="text-[#F0F0F0] text-sm font-medium">
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
                                    className="bg-[#F0F0F0] hover:bg-white text-black px-4 py-1.5 rounded-lg text-xs transition-colors font-semibold">
                                    Yes, View CAD
                                </button>
                                <button 
                                    onClick={() => setCadPrompt({ available: false, urls: [] })}
                                    className="bg-[#252525] hover:bg-[#333333] text-[#F0F0F0] px-4 py-1.5 rounded-lg text-xs transition-colors font-medium border border-[#2A2A2A]">
                                    No
                                </button>
                            </div>
                        </div>
                    )}
                    <div className="relative bg-[#1E1E1E] rounded-2xl border border-[#2A2A2A] shadow-2xl">
                        <div className="overflow-y-auto">
                            <Textarea
                                ref={textareaRef}
                                value={value}
                                onChange={(e) => {
                                    setValue(e.target.value);
                                    adjustHeight();
                                }}
                                onKeyDown={handleKeyDown}
                                placeholder={messages.length === 0 ? "Try: Make a pick and place robot..." : "Ask me anything..."}
                                className={cn(
                                    "w-full px-4 py-4",
                                    "resize-none",
                                    "bg-transparent",
                                    "border-none",
                                    "text-[#F0F0F0] text-[15px]",
                                    "focus:outline-none",
                                    "focus-visible:ring-0 focus-visible:ring-offset-0",
                                    "placeholder:text-[#555555] placeholder:text-[15px]",
                                    "min-h-[60px]"
                                )}
                                style={{ overflow: "hidden" }}
                                disabled={isLoading}
                            />
                        </div>

                        <div className="flex items-center justify-between px-3 pb-3 pt-1">
                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    className="group p-2 hover:bg-[#252525] rounded-lg transition-colors flex items-center gap-1"
                                >
                                    <Paperclip className="w-4 h-4 text-[#888888]" />
                                    <span className="text-xs text-[#555555] hidden group-hover:inline transition-opacity">
                                        Attach
                                    </span>
                                </button>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    className="px-2 py-1.5 rounded-lg text-xs text-[#888888] transition-colors border border-[#2A2A2A] hover:border-[#444444] hover:bg-[#252525] flex items-center justify-between gap-1"
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
                                            ? "bg-[#F0F0F0] text-black border-[#F0F0F0] hover:bg-white"
                                            : "text-[#555555] border-[#2A2A2A] bg-[#1E1E1E]"
                                    )}
                                >
                                    <ArrowUpIcon className="w-5 h-5" />
                                    <span className="sr-only">Send</span>
                                </button>
                            </div>
                        </div>
                    </div>
                    <div className="text-center mt-2 text-xs text-[#555555]">
                        Agentic AI can make mistakes. Consider verifying important information.
                    </div>
                </div>
            </div>

            {/* Right Side Content (Only visible when messages > 0) */}
            {messages.length > 0 && (
                <div className="flex-1 relative bg-[#0A0A0A] animate-in fade-in duration-500">
                    {/* Top Nav — pill tab bar */}
                    <div className="absolute top-5 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1 px-1.5 py-1.5 bg-[#161616] border border-[#2A2A2A] rounded-full shadow-2xl">
                        <button
                            onClick={() => setActiveTab('mapping')}
                            className={cn(
                                "px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-200",
                                activeTab === 'mapping'
                                    ? "bg-[#1E1E1E] text-[#F0F0F0] shadow-sm"
                                    : "text-[#888888] hover:text-[#F0F0F0]"
                            )}
                        >
                            Mapping
                        </button>
                        <button
                            onClick={() => setActiveTab('connection')}
                            className={cn(
                                "px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-200",
                                activeTab === 'connection'
                                    ? "bg-[#1E1E1E] text-[#F0F0F0] shadow-sm"
                                    : "text-[#888888] hover:text-[#F0F0F0]"
                            )}
                        >
                            Connection
                        </button>
                        <button
                            onClick={() => {
                                if (cadPrompt.available) {
                                    setAcceptedCadUrls(cadPrompt.urls);
                                    setCadPrompt({ available: false, urls: [] });
                                }
                                setActiveTab('cad');
                            }}
                            className={cn(
                                "px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-200",
                                activeTab === 'cad'
                                    ? "bg-[#1E1E1E] text-[#F0F0F0] shadow-sm"
                                    : "text-[#888888] hover:text-[#F0F0F0]"
                            )}
                        >
                            CAD
                        </button>
                    </div>

                    {/* Tab Content */}
                    <div className="w-full h-full pt-[60px] pb-4 px-4 relative">
                        {activeTab === 'mapping' && <MappingTab aiResponse={latestAIResponse} currentQuery={latestUserQuery} designData={robotDesign} isChatLoading={isLoading} />}
                        {activeTab === 'connection' && <ConnectionTab currentQuery={latestUserQuery} designData={robotDesign} />}
                        {activeTab === 'cad' && (() => {
                            const urls = acceptedCadUrls.length > 0 ? acceptedCadUrls : (robotDesign?.cad_urls || (robotDesign?.cad_url ? [robotDesign.cad_url] : []));
                            const cadUrl = urls[0] || 'default-cad';
                            return (
                                <CADTab 
                                    key={cadUrl}
                                    currentQuery={latestUserQuery} 
                                    cadUrls={urls} 
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
                            );
                        })()}
                    </div>
                </div>
            )}
        </div>
    );
}
