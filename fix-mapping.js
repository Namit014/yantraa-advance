const fs = require('fs');
const p = 'd:/FINAL YANTRA/yantraa-advance/frontend/src/components/ui/tabs/mapping-tab.tsx';
let code = fs.readFileSync(p, 'utf8');

// 1. Remove bomItems hook
const bomItemsPattern = /const bomItems = useMemo\(\(\) => \{[\s\S]*?\}, \[designData\]\);/;
code = code.replace(bomItemsPattern, '');

// 2. Remove handleExportBOM hook
const handleExportBOMPattern = /const handleExportBOM = useCallback\(\(\) => \{[\s\S]*?\}, \[nodes, connections, groupedNodes\]\);/;
code = code.replace(handleExportBOMPattern, '');

// 3. Fix activeView type declaration
code = code.replace(/useState<"canvas" \| "bom">/, 'useState<"canvas">');

// 4. Remove JSX condition block
const jsxPattern = /\{activeView === "bom" \? \([\s\S]*?\) : activeView === "matrix" \? \([\s\S]*?\) : \(/;
code = code.replace(jsxPattern, '');

// 5. Remove matching close brace )\}
const closePattern = /<\/div>\s*<\/div>\s*\)\}\s*<\/div>\s*\{\/\* FLOATING RIGHT TOGGLE BUTTON \*\/\}/;
code = code.replace(closePattern, '</div>\n                        </div>\n                </div>\n\n                {/* FLOATING RIGHT TOGGLE BUTTON */}');

// 6. Fix "Assembly Matrix" to "Canvas"
code = code.replace(/Select a component from the Assembly Matrix to view its details/g, 'Select a component from the Canvas to view its details');

// 7. Fix infinite fetch loop
const fetchLoopPattern = /if \(designData \|\| !currentQuery\) return;[\r\n\s]*doFetch\(currentQuery\);/;
const fetchLoopReplacement = `if (designData || !currentQuery) return;\n        if (lastQueryRef.current === currentQuery) return;\n        lastQueryRef.current = currentQuery;\n        doFetch(currentQuery);`;
code = code.replace(fetchLoopPattern, fetchLoopReplacement);

fs.writeFileSync(p, code, 'utf8');
console.log('Replacements complete');
