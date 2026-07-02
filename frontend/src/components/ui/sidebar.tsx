import { PlusIcon, Search, Folder, Compass, PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils";

export function Sidebar({ onOpen }: { onOpen?: () => void }) {
    return (
        <div className="w-[60px] h-screen bg-[#0A0A0A] border-r border-[#222222] flex flex-col items-center py-6 relative z-20">
            {/* Top Logo */}
            <div className="w-8 h-8 flex items-center justify-center mb-6">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 22L2 4H22L12 22Z" stroke="#F0F0F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M12 22V10" stroke="#F0F0F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
            </div>

            {onOpen && (
                <button onClick={onOpen} className="w-10 h-10 flex items-center justify-center text-[#888888] hover:text-[#F0F0F0] hover:bg-[#1A1A1A] rounded-md transition-colors mb-6" title="Expand Sidebar">
                    <PanelLeftOpen className="w-5 h-5 stroke-[1.5]" />
                </button>
            )}

            {/* Middle Icons */}
            <div className="flex-1 flex flex-col items-center gap-6 w-full">
                <button className="w-10 h-10 flex items-center justify-center text-[#888888] hover:text-[#F0F0F0] transition-colors">
                    <PlusIcon className="w-5 h-5 stroke-[1.5]" />
                </button>
                <button className="w-10 h-10 flex items-center justify-center text-[#888888] hover:text-[#F0F0F0] transition-colors">
                    <Search className="w-5 h-5 stroke-[1.5]" />
                </button>
                <button className="w-10 h-10 flex items-center justify-center text-[#888888] hover:text-[#F0F0F0] transition-colors">
                    <Folder className="w-5 h-5 stroke-[1.5]" />
                </button>
                <button className="w-10 h-10 flex items-center justify-center text-[#888888] hover:text-[#F0F0F0] transition-colors">
                    <Compass className="w-5 h-5 stroke-[1.5]" />
                </button>
            </div>

            {/* Bottom Profile */}
            <div className="mt-auto">
                <button className="w-8 h-8 flex items-center justify-center border border-[#333333] text-[#888888] hover:text-[#F0F0F0] hover:border-[#555555] transition-colors text-[10px] font-medium tracking-wider">
                    RM
                </button>
            </div>
        </div>
    );
}
