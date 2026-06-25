"use client";

import { SchematicsWorkspace } from "@/components/schematics/schematics-workspace";

export function SchematicsTab({ designData, currentQuery }: { designData?: any, currentQuery?: string }) {
    return (
        <div className="w-full h-full">
            <SchematicsWorkspace designData={designData} currentQuery={currentQuery} />
        </div>
    );
}
