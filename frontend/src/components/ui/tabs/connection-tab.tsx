import { ConnectionWorkspace } from "@/components/connection/connection-workspace";

export function ConnectionTab({ currentQuery, designData }: { currentQuery?: string; designData?: any }) {
    if (designData?.status === 'failed') {
        return (
            <div className="w-full h-full flex flex-col items-center justify-center bg-neutral-900 text-white p-8 rounded-xl border border-red-900">
                <h2 className="text-2xl font-bold text-red-500 mb-4">Graph generation failed at Connection Extraction</h2>
                <p className="text-neutral-400 text-center max-w-lg mb-6">{designData.error}</p>
                <div className="bg-black p-4 rounded-lg border border-neutral-800 w-full max-w-lg">
                    <p className="text-sm font-mono text-neutral-500">Status: {designData.status}</p>
                    <p className="text-sm font-mono text-neutral-500">Health: {designData.graph_health_score}/100</p>
                </div>
            </div>
        );
    }

    if (designData && (!designData.subsystems?.length && !designData.connections?.length)) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-neutral-900 text-white rounded-xl">
                <p className="text-neutral-500">No graph data returned.</p>
            </div>
        );
    }

    return (
        <div className="w-full h-full">
            <ConnectionWorkspace currentQuery={currentQuery} designData={designData} />
        </div>
    );
}
