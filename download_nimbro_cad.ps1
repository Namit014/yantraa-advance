$op2CadDir = "d:\yantraa-advance\knowledgebase\Humanoid_Robot\NimbRo_OP2\CAD"
$op2xCadDir = "d:\yantraa-advance\knowledgebase\Humanoid_Robot\NimbRo_OP2X\CAD"
$tmpDir = "d:\yantraa-advance\scratch\nimbro-tmp"

Write-Host "Cleaning up old temp directory..."
if (Test-Path $tmpDir) { Remove-Item -Recurse -Force $tmpDir }

Write-Host "Cloning NimbRo repository..."
git clone --depth 1 https://github.com/NimbRo/nimbro-op2.git $tmpDir

if (Test-Path $tmpDir) {
    Write-Host "Copying CAD files (.STEP, .STP)..."
    Get-ChildItem -Path $tmpDir -Recurse -Include *.STEP,*.STP | ForEach-Object {
        # Check if the path contains 'op2x' to put it in OP2X, otherwise OP2
        if ($_.FullName -match 'op2x' -or $_.FullName -match 'OP2X') {
            $dest = Join-Path -Path $op2xCadDir -ChildPath $_.Name
            Copy-Item -Path $_.FullName -Destination $dest -Force
            Write-Host "Copied to OP2X: $($_.Name)"
        } else {
            $dest = Join-Path -Path $op2CadDir -ChildPath $_.Name
            Copy-Item -Path $_.FullName -Destination $dest -Force
            Write-Host "Copied to OP2: $($_.Name)"
        }
    }
    
    Write-Host "Cleaning up repository..."
    Remove-Item -Recurse -Force $tmpDir
    Write-Host "Done!"
} else {
    Write-Host "Failed to clone repository."
}
