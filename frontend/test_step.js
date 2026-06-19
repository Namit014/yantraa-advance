const fs = require('fs');
const occtimportjs = require('occt-import-js')();

occtimportjs.then(occt => {
    const fileBuffer = fs.readFileSync('../knowledgebase/CAD_Models/Robots/Full_System_A-2403-02.step');
    const result = occt.ReadStepFile(new Uint8Array(fileBuffer), null);
    
    console.log("Total meshes:", result.meshes ? result.meshes.length : 0);
    
    if (result.meshes) {
        let validMeshes = 0;
        let emptyPosArrays = 0;
        let invalidCoords = 0;
        
        for (const m of result.meshes) {
            const posArray = m.attributes?.position?.array;
            if (!posArray || posArray.length === 0) {
                emptyPosArrays++;
                continue;
            }

            let isInvalid = false;
            for (let i = 0; i < posArray.length; i++) {
                if (!isFinite(posArray[i]) || Math.abs(posArray[i]) > 1e10) {
                    isInvalid = true;
                    break;
                }
            }
            
            if (isInvalid) {
                invalidCoords++;
            } else {
                validMeshes++;
            }
        }
        
        console.log("Empty posArrays:", emptyPosArrays);
        console.log("Invalid coordinates (>1e10 or NaN):", invalidCoords);
        console.log("Valid meshes:", validMeshes);
    }
});
