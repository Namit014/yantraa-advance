$cadDir = "d:\yantraa-advance\knowledgebase\Autonomous_Mobile_Robot\Vigibot\CAD"
$tmpDir = "d:\yantraa-advance\scratch\vigibot-tmp"

Write-Host "Creating CAD directory..."
New-Item -ItemType Directory -Force -Path $cadDir

if (Test-Path $tmpDir) { 
    Write-Host "Cleaning up old temp directory..."
    Remove-Item -Recurse -Force $tmpDir 
}

Write-Host "Cloning VigiCAD repository..."
# Attempting to clone the Vigibot CAD repository
git clone --depth 1 https://github.com/vigibot/vigicad.git $tmpDir

if (Test-Path $tmpDir) {
    Write-Host "Copying CAD files (.STEP, .STP)..."
    Get-ChildItem -Path $tmpDir -Recurse -Include *.STEP,*.STP | ForEach-Object {
        $dest = Join-Path -Path $cadDir -ChildPath $_.Name
        Copy-Item -Path $_.FullName -Destination $dest -Force
        Write-Host "Copied: $($_.Name)"
    }
    
    Write-Host "Cleaning up repository..."
    Remove-Item -Recurse -Force $tmpDir
    Write-Host "Done!"
} else {
    Write-Host "Failed to clone repository. URL might be different."
}
