import { SchematicsWorkspace } from "../../schematics/schematics-workspace";

interface SchematicsTabProps {
    currentQuery?: string;
    designData?: any;
}

export function SchematicsTab({ currentQuery, designData }: SchematicsTabProps) {
    return (
        <div className="w-full h-full relative">
            <SchematicsWorkspace currentQuery={currentQuery} designData={designData} />
        </div>
    );
}
