"use client";

import { useState, useMemo } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { COMPONENT_CATEGORIES } from "./component-data";
import { cn } from "@/lib/utils";

interface ComponentSidebarProps {
  onAddComponent: (componentId: string, componentName: string) => void;
}

export function ComponentSidebar({ onAddComponent }: ComponentSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredCategories = useMemo(() => {
    if (!searchQuery.trim()) return COMPONENT_CATEGORIES;
    const q = searchQuery.toLowerCase();
    return COMPONENT_CATEGORIES.map((cat) => ({
      ...cat,
      items: cat.items.filter((item) => item.name.toLowerCase().includes(q)),
    })).filter((cat) => cat.items.length > 0);
  }, [searchQuery]);

  return (
    <div className="w-[280px] bg-[#0c1220] border-l border-[#1a2744] flex flex-col shrink-0 h-full">
      {/* Header */}
      <div className="px-4 pt-5 pb-3">
        <h2 className="text-sm font-bold text-white tracking-wider uppercase mb-3">
          Components
        </h2>
        <div className="relative flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-500" />
            <input
              type="text"
              placeholder="Search components..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0a0f1a] border border-[#1a2744] rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder:text-neutral-600 focus:outline-none focus:border-blue-600/50 transition-colors"
            />
          </div>
          <button className="p-2 bg-[#0a0f1a] border border-[#1a2744] rounded-lg text-neutral-500 hover:text-white hover:border-blue-600/50 transition-colors">
            <SlidersHorizontal className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Component List */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-4 scrollbar-thin">
        {filteredCategories.map((category) => (
          <div key={category.name}>
            {/* Category Header */}
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-bold text-neutral-400 tracking-wider uppercase">
                {category.name}
              </span>
              <span className="text-[11px] text-neutral-600 font-medium">
                {category.count}
              </span>
            </div>

            {/* Component Grid */}
            <div className="grid grid-cols-4 gap-1.5">
              {category.items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => onAddComponent(item.id, item.name)}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData("component-id", item.id);
                    e.dataTransfer.setData("component-name", item.name);
                    e.dataTransfer.setData("component-icon", item.icon);
                  }}
                  className={cn(
                    "flex flex-col items-center justify-center gap-1 p-2 rounded-lg",
                    "bg-[#111a2e] border border-[#1a2744]",
                    "hover:border-blue-600/40 hover:bg-[#131f38]",
                    "transition-all duration-150 cursor-grab active:cursor-grabbing",
                    "group"
                  )}
                >
                  <span className="text-xl group-hover:scale-110 transition-transform duration-150">
                    {item.icon}
                  </span>
                  <span className="text-[9px] text-neutral-400 text-center leading-tight group-hover:text-neutral-200 transition-colors line-clamp-2">
                    {item.name}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
