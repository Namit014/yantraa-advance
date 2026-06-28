import { ConnectionWorkspace } from "@/components/connection/connection-workspace";

export function ConnectionTab({ currentQuery, designData }: { currentQuery?: string; designData?: any }) {
    return (
        <div className="w-full h-full">
            <ConnectionWorkspace currentQuery={currentQuery} designData={designData} />
        </div>
    );
}
