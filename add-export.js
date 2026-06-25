const fs = require('fs');
const p = 'd:/FINAL YANTRA/yantraa-advance/frontend/src/components/ui/tabs/mapping-tab.tsx';
let code = fs.readFileSync(p, 'utf8');

if (!code.includes("import { toPng } from 'html-to-image'")) {
    code = code.replace('import dagre from "dagre";', 'import dagre from "dagre";\nimport { toPng } from \'html-to-image\';\nimport { jsPDF } from \'jspdf\';');
}

code = code.replace('Network, PanelLeft, PanelRight', 'Network, PanelLeft, PanelRight, Download, FileImage, FileText');

const handlers = 
    const handleExportPNG = useCallback(() => {
        const flowEl = document.querySelector('.react-flow') as HTMLElement;
        if (!flowEl) return;
        toPng(flowEl, { pixelRatio: 3, backgroundColor: '#0B0E14' })
            .then((dataUrl) => {
                const a = document.createElement('a');
                a.setAttribute('download', 'yantraa-mapping.png');
                a.setAttribute('href', dataUrl);
                a.click();
            })
            .catch((err) => console.error('Failed to export PNG', err));
    }, []);

    const handleExportPDF = useCallback(() => {
        const flowEl = document.querySelector('.react-flow') as HTMLElement;
        if (!flowEl) return;
        toPng(flowEl, { pixelRatio: 3, backgroundColor: '#0B0E14' })
            .then((dataUrl) => {
                const pdf = new jsPDF({
                    orientation: 'landscape',
                    unit: 'px',
                    format: [flowEl.clientWidth, flowEl.clientHeight]
                });
                pdf.addImage(dataUrl, 'PNG', 0, 0, flowEl.clientWidth, flowEl.clientHeight);
                pdf.save('yantraa-mapping.pdf');
            })
            .catch((err) => console.error('Failed to export PDF', err));
    }, []);
;

code = code.replace(/(setConnections\\(prev => \\[\.\.\.prev, newConn\\]\\);\\s+\\}, \\[\\]\\);)/, $1\n);

const panel = 
                                    <Panel position="top-right" className="flex gap-2 mr-10 mt-2">
                                        <button onClick={handleExportPNG} className="flex items-center gap-2 px-3 py-1.5 bg-[#131823] border border-neutral-800 text-neutral-400 hover:text-white hover:border-neutral-700 rounded text-xs transition-colors shadow-lg" title="Export as High-Res PNG">
                                            <FileImage size={14} /> PNG
                                        </button>
                                        <button onClick={handleExportPDF} className="flex items-center gap-2 px-3 py-1.5 bg-[#131823] border border-neutral-800 text-neutral-400 hover:text-white hover:border-neutral-700 rounded text-xs transition-colors shadow-lg" title="Export as High-Res PDF">
                                            <FileText size={14} /> PDF
                                        </button>
                                    </Panel>;

code = code.replace(/(<Background color="#222" gap=\\{16\\} \\/>)/, $1\n);

fs.writeFileSync(p, code, 'utf8');
console.log('Done mapping export replacement');
