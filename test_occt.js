const fs = require('fs');
const occtimportjs = require('occt-import-js')();

occtimportjs.then((occt) => {
    const fileBuffer = fs.readFileSync('c:\\Users\\User\\Desktop\\Advance_yantraa\\yantraa-advance\\knowledgebase\\CAD_Models\\Robots\\Articulated_robot_cad.STEP');
    const result = occt.ReadStepFile(fileBuffer, null);
    
    console.log(`Parsed ${result?.meshes?.length} meshes`);
    if (result && result.meshes) {
        let emptyMeshes = 0;
        let validMeshes = 0;
        for (let m of result.meshes) {
            if (!m.attributes || !m.attributes.position || !m.attributes.position.array) {
                emptyMeshes++;
            } else {
                validMeshes++;
            }
        }
        console.log(`Empty: ${emptyMeshes}, Valid: ${validMeshes}`);
    }
});
