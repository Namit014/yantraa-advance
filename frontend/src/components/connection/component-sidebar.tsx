"use client";

import { useState, useMemo } from "react";
import { Search, SlidersHorizontal, X } from "lucide-react";
import { COMPONENT_CATEGORIES } from "./component-data";
import { cn } from "@/lib/utils";

interface ComponentSidebarProps {
  onAddComponent: (componentId: string, componentName: string) => void;
}

export function ComponentSidebar({ onAddComponent }: ComponentSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [sparkfunComponents, setSparkfunComponents] = useState<any[]>([]);

  useEffect(() => {
    // Fetch SparkFun components
    const q = searchQuery.trim();
    fetch(`/api/sparkfun/components${q ? `?q=${encodeURIComponent(q)}` : ""}`)
      .then(res => res.json())
      .then(data => setSparkfunComponents(data))
      .catch(err => console.error("Failed to fetch SparkFun components:", err));
  }, [searchQuery]);

  const filteredCategories = useMemo(() => {
    let baseCategories = COMPONENT_CATEGORIES;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      baseCategories = COMPONENT_CATEGORIES.map((cat) => ({
        ...cat,
        items: cat.items.filter((item) => item.name.toLowerCase().includes(q)),
      }));
    }
    
    // Add SparkFun category
    if (sparkfunComponents.length > 0) {
      baseCategories = [
        ...baseCategories,
        {
          name: "SparkFun Library",
          items: sparkfunComponents.map(c => ({
            id: `sparkfun-${c.name}`,
            name: c.name,
            icon: "⚙️",
            prodId: c.prod_id,
            modelUrl: c.model_path
          }))
        }
      ];
    }
    
    return baseCategories;
  }, [searchQuery, sparkfunComponents]);

  return (
    <div className="w-[280px] bg-[#0c1220] border-l border-[#1a2744] flex flex-col shrink-0 h-full">
      {/* Header */}
      <div className="px-4 pt-5 pb-3">
        <h2 className="text-sm font-bold text-white tracking-wider uppercase mb-3 flex justify-between items-center">
          <span>Components</span>
          {searchQuery && (
            <span className="text-[10px] bg-blue-900/50 text-blue-400 px-2 py-0.5 rounded-full border border-blue-800/50 flex items-center gap-1 font-mono">
              {filteredCategories.reduce((acc, cat) => acc + cat.items.length, 0)} results
              <button onClick={() => setSearchQuery("")} className="hover:text-white transition-colors ml-1">
                <X size={10} />
              </button>
            </span>
          )}
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
        {filteredCategories.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 space-y-4 mt-12">
            <div className="w-12 h-12 rounded-full bg-[#111a2e] border border-[#1a2744] flex items-center justify-center">
              <Search className="w-5 h-5 text-neutral-500" />
            </div>
            <div>
              <p className="text-sm text-neutral-300 font-medium mb-1">No components found</p>
              <p className="text-xs text-neutral-500">Try broadening your search or add a custom component.</p>
            </div>
            <button 
              className="mt-2 text-xs font-bold bg-[#1e3a5f] hover:bg-[#2563eb] text-blue-300 hover:text-white px-4 py-2 rounded-lg transition-colors border border-blue-800/50"
            >
              + Add Custom Component
            </button>
          </div>
        ) : (
          filteredCategories.map((category) => (
            <div key={category.name}>
              {/* Category Header */}
              <div className="flex items-center justify-between mb-2.5">
                <span className="text-[11px] font-bold text-neutral-400 tracking-wider uppercase">
                  {category.name}
                </span>
                <span className="text-[11px] text-neutral-600 font-medium">
                  {category.items.length}
                </span>
              </div>

              {/* Component Grid */}
              {category.items.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-4 bg-[#111a2e]/50 border border-dashed border-[#1a2744] rounded-lg text-center">
                  <span className="text-xs text-neutral-500 mb-2">No {category.name} components found</span>
                  <button className="text-[10px] font-bold bg-[#1e3a5f] hover:bg-[#2563eb] text-blue-300 hover:text-white px-3 py-1.5 rounded-lg transition-colors">
                    Add Custom Component
                  </button>
                </div>
              ) : (
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
                        if (item.prodId) e.dataTransfer.setData("component-prodid", item.prodId);
                        if (item.modelUrl) e.dataTransfer.setData("component-modelurl", item.modelUrl);
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
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
