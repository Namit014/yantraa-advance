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
import { Sidebar } from "./sidebar";
import { ProjectSidebar } from "./project-sidebar";

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

    const [isChatOpen, setIsChatOpen] = useState(true);

    const [isProjectSidebarOpen, setIsProjectSidebarOpen] = useState(false);

    // Auto-open project sidebar on first message
    useEffect(() => {
        if (messages.length === 1 && !robotDesign) {
            setIsProjectSidebarOpen(true);
        }
    }, [messages.length, robotDesign]);

    if (!robotDesign) {
        // Shared input box rendering for both states of Phase 1
        const renderInputBox = () => (
            <div className="w-full max-w-3xl px-6">
                <div className="relative flex flex-col bg-[#111111] border border-[#222222]">
                    {/* Corner Crosshairs */}
                    <div className="absolute -top-1 -left-1 w-2 h-2 pointer-events-none flex items-center justify-center">
                        <div className="absolute w-full h-[1px] bg-[#555555]" />
                        <div className="absolute h-full w-[1px] bg-[#555555]" />
                    </div>
                    <div className="absolute -top-1 -right-1 w-2 h-2 pointer-events-none flex items-center justify-center">
                        <div className="absolute w-full h-[1px] bg-[#555555]" />
                        <div className="absolute h-full w-[1px] bg-[#555555]" />
                    </div>
                    <div className="absolute -bottom-1 -left-1 w-2 h-2 pointer-events-none flex items-center justify-center">
                        <div className="absolute w-full h-[1px] bg-[#555555]" />
                        <div className="absolute h-full w-[1px] bg-[#555555]" />
                    </div>
                    <div className="absolute -bottom-1 -right-1 w-2 h-2 pointer-events-none flex items-center justify-center">
                        <div className="absolute w-full h-[1px] bg-[#555555]" />
                        <div className="absolute h-full w-[1px] bg-[#555555]" />
                    </div>

                    <div className="overflow-y-auto max-h-[140px] min-h-[60px] flex items-center">
                        <Textarea
                            ref={textareaRef}
                            value={value}
                            onChange={(e) => {
                                setValue(e.target.value);
                                adjustHeight();
                            }}
                            onKeyDown={handleKeyDown}
                            placeholder="Make a pick and place robot |"
                            className={cn(
                                "w-full px-5 py-5",
                                "resize-none bg-transparent border-none",
                                "text-[#F0F0F0] text-[14px] leading-relaxed",
                                "focus:outline-none focus-visible:ring-0 focus-visible:ring-offset-0",
                                "placeholder:text-[#555555]"
                            )}
                            style={{ overflow: "hidden" }}
                            disabled={isLoading}
                        />
                    </div>

                    <div className="flex items-center justify-between px-3 pb-3 pt-2">
                        <div className="flex items-center gap-1.5">
                            <button type="button" className="p-1.5 hover:bg-[#252525] rounded transition-colors text-[#888888] hover:text-[#F0F0F0]">
                                <Paperclip className="w-[16px] h-[16px]" />
                            </button>
                            <button type="button" className="p-1.5 hover:bg-[#252525] rounded transition-colors text-[#888888] hover:text-[#F0F0F0]">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" x2="12" y1="19" y2="22"></line></svg>
                            </button>
                            <button type="button" className="px-3 py-1 ml-2 rounded text-[11px] text-[#E0E0E0] font-medium transition-colors border border-[#333333] hover:border-[#555555] hover:bg-[#252525] flex items-center gap-2">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"></path></svg>
                                Prompt Library
                            </button>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-1.5 text-[#888888] text-xs font-medium cursor-pointer hover:text-[#F0F0F0] transition-colors">
                                <div className="w-1.5 h-1.5 rounded-full bg-[#888888]" />
                                Yantraa 1.0
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="ml-0.5"><polyline points="6 9 12 15 18 9"></polyline></svg>
                            </div>
                            <button
                                type="button"
                                onClick={handleSubmit}
                                disabled={isLoading || !value.trim()}
                                className={cn(
                                    "w-8 h-8 flex items-center justify-center transition-colors rounded-sm",
                                    value.trim() && !isLoading
                                        ? "bg-[#F0F0F0] text-black hover:bg-white"
                                        : "bg-[#F0F0F0] text-black opacity-90"
                                )}
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                                <span className="sr-only">Send</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );

        return (
            <div className="flex w-full h-screen bg-[#0A0A0A] overflow-hidden relative">
                {/* Viewport Crosshairs/Grid Lines */}
                <div className={cn("absolute top-0 bottom-0 w-px bg-[#222222] pointer-events-none z-10 transition-all duration-300", isProjectSidebarOpen ? "left-[396px]" : "left-[59px]")} />
                <div className="absolute top-[59px] left-0 right-0 h-px bg-[#222222] pointer-events-none z-10" />
                <div className="absolute bottom-[59px] left-0 right-0 h-px bg-[#222222] pointer-events-none z-10" />

                {/* Sidebar toggle */}
                <div className={cn("shrink-0 transition-all duration-300 h-full", isProjectSidebarOpen ? "w-[396px]" : "w-[60px]")}>
                    {isProjectSidebarOpen ? (
                        <ProjectSidebar onClose={() => setIsProjectSidebarOpen(false)} />
                    ) : (
                        <Sidebar onOpen={() => setIsProjectSidebarOpen(true)} />
                    )}
                </div>

                <div className="flex flex-1 flex-col relative z-20 items-center justify-center">
                    {/* Upgrade button top right */}
                    <button className="absolute top-6 right-6 px-4 py-2 border border-[#333333] hover:border-[#555555] bg-transparent text-[#F0F0F0] text-xs font-medium flex items-center gap-2 transition-colors z-50 rounded-sm">
                        <img src="/yantraa-logo.png" alt="Yantraa" className="w-3.5 h-3.5 object-contain" />
                        Upgrade
                    </button>

                    {messages.length === 0 ? (
                        // Phase 1A: Landing Page
                        <div className="w-full h-full flex flex-col items-center justify-center relative -mt-10">
                            <h1 className="text-[28px] font-medium text-[#F0F0F0] text-center mb-8 tracking-tight">
                                What would you like to build today?
                            </h1>
                            
                            {renderInputBox()}

                            {/* Suggestion Cards */}
                            <div className="grid grid-cols-3 gap-4 mt-4 w-full max-w-3xl px-6">
                                <div onClick={() => setValue("Design a Pick & Place Robot")} className="bg-[#111111] border border-transparent hover:border-[#222222] p-5 cursor-pointer transition-colors group">
                                    <div className="flex items-center gap-2 mb-3 text-[#E0E0E0] text-xs font-medium group-hover:text-white transition-colors">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.29 7 12 12 20.71 7"></polyline><line x1="12" y1="22" x2="12" y2="12"></line></svg>
                                        Design a Pick & Place Robot
                                    </div>
                                    <p className="text-[10px] text-[#777777] leading-relaxed">
                                        Generate CAD, component mapping, and connections for a pick-and-place robotic system.
                                    </p>
                                </div>
                                <div onClick={() => setValue("Design a Delta Robot")} className="bg-[#111111] border border-transparent hover:border-[#222222] p-5 cursor-pointer transition-colors group">
                                    <div className="flex items-center gap-2 mb-3 text-[#E0E0E0] text-xs font-medium group-hover:text-white transition-colors">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>
                                        Design a Delta Robot
                                    </div>
                                    <p className="text-[10px] text-[#777777] leading-relaxed">
                                        Validate requirements, assess technical viability, and refine your robot before generating designs.
                                    </p>
                                </div>
                                <div onClick={() => setValue("Check Feasibility")} className="bg-[#111111] border border-transparent hover:border-[#222222] p-5 cursor-pointer transition-colors group">
                                    <div className="flex items-center gap-2 mb-3 text-[#E0E0E0] text-xs font-medium group-hover:text-white transition-colors">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
                                        Check Feasibility
                                    </div>
                                    <p className="text-[10px] text-[#777777] leading-relaxed">
                                        Evaluate cost, complexity, technical viability and understand the process before building your robot.
                                    </p>
                                </div>
                            </div>
                        </div>
                    ) : (
                        // Phase 1B: Chatting
                        <div className="w-full max-w-4xl h-full flex flex-col relative pb-32">
                            {/* Messages */}
                            <div className="flex-1 w-full overflow-y-auto space-y-8 pt-24 px-6 flex flex-col custom-scrollbar">
                                {messages.map((msg, idx) => {
                                    if (msg.role === 'assistant' && !msg.content) return null;
                                    return (
                                        <div key={idx} className={cn("flex w-full", msg.role === 'user' ? "justify-end" : "justify-start")}>
                                            <div className={cn(
                                                "max-w-[85%] px-5 py-4",
                                                msg.role === 'user'
                                                    ? "bg-[#1A1A1A] text-[#F0F0F0] border-t border-r border-[#2A2A2A]"
                                                    : "bg-transparent text-[#F0F0F0]"
                                            )}
                                            style={msg.role === 'user' ? { clipPath: "polygon(0 0, 100% 0, 100% 100%, 16px 100%, 0 calc(100% - 16px))" } : {}}
                                            >
                                                <div className="whitespace-pre-wrap leading-relaxed text-[14px] text-[#E0E0E0]">
                                                    {msg.content}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                                {isLoading && (!messages.length || messages[messages.length - 1].role !== 'assistant' || isThinking || !messages[messages.length - 1].content) && (
                                    <div className="flex w-full justify-start">
                                        <div className="bg-transparent text-[#F0F0F0] px-4 py-3 flex flex-col gap-2">
                                            <div className="flex items-center gap-3">
                                                <div className="flex gap-1 items-center">
                                                    <div className="w-1.5 h-1.5 bg-[#555555] rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                                    <div className="w-1.5 h-1.5 bg-[#555555] rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                                    <div className="w-1.5 h-1.5 bg-[#555555] rounded-full animate-bounce"></div>
                                                </div>
                                            </div>
                                            {isThinking && (
                                                <div className="text-[12px] text-[#888888] font-mono animate-pulse">
                                                    {statusMessage}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* Input Area anchored at bottom */}
                            <div className="absolute bottom-10 left-1/2 -translate-x-1/2 w-full flex flex-col items-center">
                                {renderInputBox()}
                                <p className="text-[#444444] text-[10px] text-center mt-4 tracking-wide">
                                    Yantraa can make mistakes. Consider verifying important information.
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Result Phase (robotDesign != null)
    return (
        <div className="flex w-full h-screen bg-[#0A0A0A] overflow-hidden relative">
            {/* Viewport Crosshairs/Grid Lines */}
            <div className="absolute left-[59px] top-0 bottom-0 w-px bg-[#222222] pointer-events-none z-10" />
            <div className="absolute top-[59px] left-0 right-0 h-px bg-[#222222] pointer-events-none z-10" />
            <div className="absolute bottom-[59px] left-0 right-0 h-px bg-[#222222] pointer-events-none z-10" />
            
            <Sidebar />

            <div className="flex flex-1 relative z-20">
                {/* Chat Sidebar Panel */}
                <div className={cn(
                    "flex flex-col relative transition-all duration-300 ease-in-out shrink-0 h-full",
                    isChatOpen ? "w-[396px]" : "w-0"
                )}>
                    {/* SVG Background */}
                    <div className="absolute inset-0 pointer-events-none z-0 w-[396px] overflow-hidden">
                        <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 396 1032" fill="none" preserveAspectRatio="none">
                            <path d="M0 608.5V835.5L29.4377 878.18V984L55.5 1032H396V516V0H55.5L29.4377 42.5V558.979L0 608.5Z" fill="#121212"/>
                        </svg>
                    </div>

                    {/* Chat Content wrapper - hide when closed to prevent text bleeding */}
                    <div className={cn(
                        "relative z-10 flex flex-col h-full w-[396px] transition-opacity duration-300",
                        isChatOpen ? "opacity-100" : "opacity-0 pointer-events-none"
                    )}>
                        {/* Messages Area */}
                        <div className="flex-1 w-full overflow-y-auto space-y-6 pb-32 pt-8 px-6 flex flex-col custom-scrollbar">
                            {messages.length === 0 ? (
                                <div className="flex flex-col items-center justify-center w-full h-full opacity-50">
                                    <h2 className="text-xl font-medium text-[#F0F0F0] text-center">
                                        Ask Yantraa
                                    </h2>
                                    <p className="text-xs text-[#888888] text-center mt-2">
                                        Design your next robotic system.
                                    </p>
                                </div>
                            ) : (
                                <>
                                    {messages.map((msg, idx) => {
                                        if (msg.role === 'assistant' && !msg.content) return null;
                                        return (
                                            <div key={idx} className={cn("flex w-full", msg.role === 'user' ? "justify-end" : "justify-start")}>
                                                <div className={cn(
                                                    "max-w-[85%] rounded-2xl px-4 py-3",
                                                    msg.role === 'user'
                                                        ? "bg-[#252525] border border-[#333333] text-[#F0F0F0]"
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
                                                    <div className="whitespace-pre-wrap leading-relaxed text-[13px] text-[#E0E0E0]">
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
                                                    <div className="text-[11px] text-[#888888] font-mono pl-8 animate-pulse">
                                                        {statusMessage}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                    <div ref={messagesEndRef} />
                                </>
                            )}
                        </div>

                        {/* Input Area inside the sidebar */}
                        <div className="w-full p-4 absolute bottom-0 left-0 bg-gradient-to-t from-[#121212] via-[#121212] to-transparent pt-10 z-10">
                            {cadPrompt.available && (
                                <div className="mb-3 bg-[#1A1A1A] border border-[#2A2A2A] p-4 flex flex-col gap-3 animate-in slide-in-from-bottom-2">
                                    <p className="text-[#F0F0F0] text-xs font-medium">
                                        {cadPrompt.urls.length > 1 
                                            ? `A 3D CAD assembly with ${cadPrompt.urls.length} parts is available. View it?` 
                                            : "A highly detailed 3D CAD model is available. View it?"}
                                    </p>
                                    <div className="flex gap-2">
                                        <button 
                                            onClick={() => {
                                                setAcceptedCadUrls(cadPrompt.urls);
                                                setActiveTab('cad');
                                                setCadPrompt({ available: false, urls: [] });
                                            }}
                                            className="bg-[#F0F0F0] hover:bg-white text-black px-3 py-1.5 text-[11px] transition-colors font-semibold">
                                            Yes, View
                                        </button>
                                        <button 
                                            onClick={() => setCadPrompt({ available: false, urls: [] })}
                                            className="bg-[#252525] hover:bg-[#333333] text-[#F0F0F0] px-3 py-1.5 text-[11px] transition-colors font-medium border border-[#2A2A2A]">
                                            No
                                        </button>
                                    </div>
                                </div>
                            )}

                            <div className="relative flex flex-col bg-[#1A1A1A] border border-[#2A2A2A] rounded-[24px] shadow-2xl overflow-hidden">
                                <div className="overflow-y-auto max-h-[140px] min-h-[50px] flex items-center">
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
                                            "w-full px-5 py-3.5",
                                            "resize-none bg-transparent border-none",
                                            "text-[#F0F0F0] text-[13px] leading-relaxed",
                                            "focus:outline-none focus-visible:ring-0 focus-visible:ring-offset-0",
                                            "placeholder:text-[#555555]"
                                        )}
                                        style={{ overflow: "hidden" }}
                                        disabled={isLoading}
                                    />
                                </div>

                                <div className="flex items-center justify-between px-3 pb-2">
                                    <div className="flex items-center gap-1">
                                        <button type="button" className="p-1.5 hover:bg-[#252525] rounded-full transition-colors text-[#888888] hover:text-[#F0F0F0]">
                                            <Paperclip className="w-[14px] h-[14px]" />
                                        </button>
                                        <button type="button" className="p-1.5 hover:bg-[#252525] rounded-full transition-colors text-[#888888] hover:text-[#F0F0F0]">
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" x2="12" y1="19" y2="22"></line></svg>
                                        </button>
                                        <button type="button" className="px-2 py-1 ml-1 rounded text-[10px] text-[#E0E0E0] font-medium transition-colors border border-[#333333] hover:border-[#555555] hover:bg-[#252525] flex items-center gap-1.5">
                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"></path></svg>
                                            Prompt Library
                                        </button>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={handleSubmit}
                                        disabled={isLoading || !value.trim()}
                                        className={cn(
                                            "p-1.5 rounded-full transition-colors flex items-center justify-center",
                                            value.trim() && !isLoading
                                                ? "bg-[#F0F0F0] text-black hover:bg-white"
                                                : "text-[#555555] bg-[#222222]"
                                        )}
                                    >
                                        <ArrowUpIcon className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Toggle Button for the Sidebar */}
                    <button 
                        onClick={() => setIsChatOpen(!isChatOpen)}
                        className={cn(
                            "absolute bottom-8 -right-4 w-8 h-8 bg-[#1A1A1A] border border-[#333333] hover:border-[#555555] hover:bg-[#222222] flex items-center justify-center text-[#F0F0F0] font-bold text-[10px] z-50 transition-transform duration-300 shadow-xl",
                            !isChatOpen && "-translate-x-4 translate-y-0"
                        )}
                        style={{ clipPath: "polygon(4px 0, calc(100% - 4px) 0, 100% 4px, 100% calc(100% - 4px), calc(100% - 4px) 100%, 4px 100%, 0 calc(100% - 4px), 0 4px)" }}
                    >
                        N
                    </button>
                </div>

                {/* Right Side Content (Main Tabs) */}
                <div className="flex-1 relative bg-[#0A0A0A] border-l border-[#222222]">
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
            </div>
        </div>
    );
}
