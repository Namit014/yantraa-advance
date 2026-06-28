import sys
import re

def resolve_v0_ai_chat():
    f = "frontend/src/components/ui/v0-ai-chat.tsx"
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    pattern = r'<<<<<<< HEAD\n\s*<div className="w-full h-full pt-20 pb-4 px-4 relative">\n\s*\{activeTab === \'mapping\' && <MappingTab aiResponse=\{latestAIResponse\} currentQuery=\{latestUserQuery\} designData=\{robotDesign\} isChatLoading=\{isLoading\} />\}\n=======\n\s*<div className="w-full h-full pt-\[60px\] pb-4 px-4 relative">\n\s*\{activeTab === \'mapping\' && <MappingTab aiResponse=\{latestAIResponse\} currentQuery=\{latestUserQuery\} designData=\{robotDesign\} />\}\n>>>>>>> [a-f0-9]+'
    
    replacement = """                    <div className="w-full h-full pt-[60px] pb-4 px-4 relative">
                        {activeTab === 'mapping' && <MappingTab aiResponse={latestAIResponse} currentQuery={latestUserQuery} designData={robotDesign} isChatLoading={isLoading} />}"""
    
    new_content = re.sub(pattern, replacement, content)
    with open(f, 'w', encoding='utf-8') as file:
        file.write(new_content)

def resolve_mapping_tab():
    f = "frontend/src/components/ui/tabs/mapping-tab.tsx"
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    pattern = r'<<<<<<< HEAD\n\s*<div className="flex-1 h-full bg-\[#050505\] relative border-r border-neutral-800/50 flex flex-col">\n\s*\{isLoading \? \(\n\s*<div className="flex-1 flex flex-col items-center justify-center p-6 text-center">\n\s*<div className="w-16 h-16 border-4 border-sky-500/20 border-t-sky-500 rounded-full animate-spin mb-6"></div>\n\s*<h2 className="text-xl font-bold text-white tracking-widest uppercase mb-2">Generating Component Mapping</h2>\n\s*<p className="text-neutral-500 text-sm max-w-md">Our AI is analyzing your prompt to generate the optimal mechanical and electronic components, and routing the wiring connections. Please wait...</p>\n\s*</div>\n\s*\) : activeView === "bom" \? \(\n\s*<div className="flex-1 overflow-y-auto p-8 bg-\[#050505\]">\n=======\n\s*<div className="flex-1 h-full bg-\[#0A0A0A\] relative border-r border-\[#2A2A2A\] flex flex-col">\n\s*\{activeView === "bom" \? \(\n\s*<div className="flex-1 overflow-y-auto p-8 bg-\[#0A0A0A\]">\n>>>>>>> [a-f0-9]+'

    replacement = """                <div className="flex-1 h-full bg-[#0A0A0A] relative border-r border-[#2A2A2A] flex flex-col">
                    {isLoading ? (
                        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                            <div className="w-16 h-16 border-4 border-sky-500/20 border-t-sky-500 rounded-full animate-spin mb-6"></div>
                            <h2 className="text-xl font-bold text-white tracking-widest uppercase mb-2">Generating Component Mapping</h2>
                            <p className="text-neutral-500 text-sm max-w-md">Our AI is analyzing your prompt to generate the optimal mechanical and electronic components, and routing the wiring connections. Please wait...</p>
                        </div>
                    ) : activeView === "bom" ? (
                        <div className="flex-1 overflow-y-auto p-8 bg-[#0A0A0A]">"""
    
    new_content = re.sub(pattern, replacement, content)
    with open(f, 'w', encoding='utf-8') as file:
        file.write(new_content)

def resolve_api_design():
    f = "src/api/design.py"
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    p1 = r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> [a-f0-9]+'
    
    def repl(m):
        head = m.group(1)
        inc = m.group(2)
        if "def _safe_llm_call" in head:
            return inc
        elif "import traceback" in head:
            return head
        elif "history_str = \"\"" in inc:
            return inc
        return m.group(0)
    
    new_content = re.sub(p1, repl, content, flags=re.DOTALL)
    with open(f, 'w', encoding='utf-8') as file:
        file.write(new_content)

def resolve_llm():
    f = "src/llm.py"
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    p1 = r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> [a-f0-9]+'
    
    def repl(m):
        head = m.group(1)
        inc = m.group(2)
        if "\"maxOutputTokens\": 8192" in head:
            return head
        elif "elif not GEMINI_API_KEY" in head:
            return head
        elif "\"max_tokens\": 1500" in head:
            return head
        elif "if model is None:" in head and "openrouter/free" in head:
            return "" # remove it because it's duplicated below docstring in incoming
        elif "call_llm_stream" in inc:
            return inc
        return head
        
    new_content = re.sub(p1, repl, content, flags=re.DOTALL)
    with open(f, 'w', encoding='utf-8') as file:
        file.write(new_content)

resolve_v0_ai_chat()
resolve_mapping_tab()
resolve_api_design()
resolve_llm()
print("Done")
