import { PlusIcon, Search, Folder, Compass, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";

export function ProjectSidebar({ onClose }: { onClose?: () => void }) {
    return (
        <div className="w-[396px] h-screen shrink-0 relative overflow-hidden bg-[#0A0A0A] flex flex-col z-20">
            {/* SVG Background Layer */}
            <div className="absolute inset-0 pointer-events-none z-0">
                <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 396 1032" fill="none" preserveAspectRatio="none">
                    <path d="M0 608.5V835.5L29.4377 878.18V984L55.5 1032H396V516V0H55.5L29.4377 42.5V558.979L0 608.5Z" fill="#121212"/>
                </svg>
            </div>

            {/* Content Layer */}
            <div className="relative z-10 flex flex-col h-full w-full pt-6 pb-6 px-10">
                {/* Logo Area */}
                <div className="flex items-center justify-between mb-10 -ml-2">
                    <div className="w-8 h-8 flex items-center justify-center">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 22L2 4H22L12 22Z" stroke="#F0F0F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                            <path d="M12 22V10" stroke="#F0F0F0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                    </div>
                    {onClose && (
                        <button onClick={onClose} className="p-2 hover:bg-[#1A1A1A] rounded text-[#888888] hover:text-[#F0F0F0] transition-colors">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><path d="M9 3v18"/></svg>
                        </button>
                    )}
                </div>

                {/* Workspace Section */}
                <div className="mb-10">
                    <h3 className="text-[#555555] text-[11px] uppercase tracking-wider font-semibold mb-4 ml-1">Workspace</h3>
                    <div className="flex flex-col gap-1">
                        <button className="flex items-center gap-3 w-full px-2 py-2 text-[#E0E0E0] hover:bg-[#1A1A1A] rounded-md transition-colors text-sm font-medium">
                            <PlusIcon className="w-[18px] h-[18px] text-[#F0F0F0]" />
                            New Project
                        </button>
                        <button className="flex items-center gap-3 w-full px-2 py-2 text-[#888888] hover:text-[#E0E0E0] hover:bg-[#1A1A1A] rounded-md transition-colors text-sm font-medium">
                            <Search className="w-[18px] h-[18px]" />
                            Search Project
                        </button>
                    </div>
                </div>

                {/* Library Section */}
                <div className="mb-10">
                    <h3 className="text-[#555555] text-[11px] uppercase tracking-wider font-semibold mb-4 ml-1">Library</h3>
                    <div className="flex flex-col gap-1">
                        <button className="flex items-center gap-3 w-full px-2 py-2 text-[#888888] hover:text-[#E0E0E0] hover:bg-[#1A1A1A] rounded-md transition-colors text-sm font-medium">
                            <Folder className="w-[18px] h-[18px]" />
                            Projects
                        </button>
                        <button className="flex items-center gap-3 w-full px-2 py-2 text-[#888888] hover:text-[#E0E0E0] hover:bg-[#1A1A1A] rounded-md transition-colors text-sm font-medium">
                            <Compass className="w-[18px] h-[18px]" />
                            CAD Files
                        </button>
                    </div>
                </div>

                {/* Recent Projects Section */}
                <div className="flex-1">
                    <h3 className="text-[#555555] text-[11px] uppercase tracking-wider font-semibold mb-4 ml-1">Recent Projects</h3>
                    <div className="px-3 text-[#555555] text-sm">
                        No projects yet
                    </div>
                </div>

                {/* Upgrade & Profile Section */}
                <div className="mt-auto">
                    {/* Upgrade Prompt */}
                    <div className="mb-6 px-1">
                        <h4 className="text-[#E0E0E0] text-[13px] font-medium mb-1">Upgrade to Premium!</h4>
                        <p className="text-[#666666] text-[10px] leading-relaxed mb-4 max-w-[180px]">
                            Get unlimited access to generate CAD and Component mapping files
                        </p>
                        <button className="w-[200px] bg-[#F0F0F0] text-black py-2.5 text-xs font-semibold hover:bg-white transition-colors text-center">
                            Upgrade Now
                        </button>
                    </div>

                    {/* Profile Button */}
                    <button className="flex items-center gap-3 w-[200px] p-2 hover:bg-[#1A1A1A] rounded-lg transition-colors text-left border border-transparent hover:border-[#222222]">
                        <div className="w-8 h-8 rounded border border-[#333333] flex items-center justify-center text-[#888888] text-[10px] font-bold bg-[#161616]">
                            RM
                        </div>
                        <div className="flex-1">
                            <div className="text-[#E0E0E0] text-xs font-semibold">Rahul Mehta</div>
                            <div className="text-[#666666] text-[10px]">Free plan</div>
                        </div>
                        <ChevronsUpDown className="w-3.5 h-3.5 text-[#555555]" />
                    </button>
                </div>
            </div>
        </div>
    );
}
