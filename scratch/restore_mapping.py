import re

with open('frontend/src/components/ui/tabs/mapping-tab.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the garbage characters
content = content.replace("ΓåÆ", "→")

# Make sure fuzzyMatch uses the user's preferred version from the prompt:
old_fuzzy = """    const wordsA = a.toLowerCase().split(/[\\s\\(\\)\\-\\_]+/).filter(w => w.length > 3);
    const wordsB = b.toLowerCase().split(/[\\s\\(\\)\\-\\_]+/).filter(w => w.length > 3);
    const intersection = wordsA.filter(w => wordsB.includes(w));
    
    if (wordsA.length > 0 && intersection.length / wordsA.length > 0.6) return true;
    if (wordsB.length > 0 && intersection.length / wordsB.length > 0.6) return true;"""

new_fuzzy = """    // Split by non-alphanumeric, filter out purely empty strings
    const wordsA = a.toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 1);
    const wordsB = b.toLowerCase().split(/[^a-z0-9]+/).filter(w => w.length > 1);
    const intersection = wordsA.filter(w => wordsB.includes(w));
    
    // More robust keyword matching (handles IMU, DOF, etc.)
    if (wordsA.length > 0 && intersection.length / wordsA.length >= 0.6) return true;
    if (wordsB.length > 0 && intersection.length / wordsB.length >= 0.6) return true;"""

if old_fuzzy in content:
    content = content.replace(old_fuzzy, new_fuzzy)

# Make sure fetchComponentsFromRAG has existingNodes:
old_rag_start = """async function fetchComponentsFromRAG(
    topic: string,
    aiResponseFallback: string
): Promise<RawComponent[]> {"""

new_rag_start = """async function fetchComponentsFromRAG(
    topic: string,
    aiResponseFallback: string,
    existingNodes: ComponentNode[]
): Promise<RawComponent[]> {
    const existingStr = existingNodes.length > 0 
        ? existingNodes.map(n => `- ${n.label} (${n.category})`).join("\\n") 
        : "None";"""

if old_rag_start in content:
    content = content.replace(old_rag_start, new_rag_start)

# Update the prompt inside fetchComponentsFromRAG
old_prompt = """    const prompt1 =
        `Return ONLY a JSON array. No explanation, no markdown, no extra text. ` +
        `For the topic: '${topic}', list a comprehensive and highly detailed set of low-level hardware components needed to build this robot (e.g., specific microcontrollers, specific sensors, motor drivers, high-torque servos, lipo batteries, structural brackets, etc.). Provide at least 8 to 15 components if possible. Do NOT just say "arm" or "leg". ` +
        `Each item must have exactly these fields: ` +
        `{"name": string, "category": one of exactly: "actuator"|"sensor"|"controller"|"mechanical"|"power"|"electronic", ` +
        `"description": string, "connects_to": string[]}`;"""

new_prompt = """    const prompt1 =
        `Return ONLY a JSON array. No explanation, no markdown, no extra text. ` +
        `Here is the list of existing components already in the system:\\n${existingStr}\\n\\n` +
        `For the topic: '${topic}', list a comprehensive and highly detailed set of NEW low-level hardware components needed. ` +
        `DO NOT duplicate or re-describe ANY of the existing components listed above. If you need to refer to an existing component in 'connects_to', use its EXACT name. ` +
        `Each item must have exactly these fields: ` +
        `{"name": string, "category": one of exactly: "actuator"|"sensor"|"controller"|"mechanical"|"power"|"electronic", ` +
        `"description": string, "connects_to": string[]}`;"""

if old_prompt in content:
    content = content.replace(old_prompt, new_prompt)

# Update doFetch call
content = content.replace("const fetchedRaw = await fetchComponentsFromRAG(q, aiResponse);", "const fetchedRaw = await fetchComponentsFromRAG(q, aiResponse, nodes);")

with open('frontend/src/components/ui/tabs/mapping-tab.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done fixing mapping-tab.tsx")
