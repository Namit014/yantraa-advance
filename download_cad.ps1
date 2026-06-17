$cadDir = "d:\yantraa-advance\knowledgebase\Articulated_Robot\BCN3D_Moveo\CAD"
$tmpDir = "d:\yantraa-advance\scratch\bcn3d-tmp"

Write-Host "Creating CAD directory..."
New-Item -ItemType Directory -Force -Path $cadDir

if (Test-Path $tmpDir) { 
    Write-Host "Cleaning up old temp directory..."
    Remove-Item -Recurse -Force $tmpDir 
}

Write-Host "Cloning BCN3D-Moveo repository..."
git clone --depth 1 https://github.com/BCN3D/BCN3D-Moveo.git $tmpDir

Write-Host "Copying CAD files (.SLDPRT, .SLDASM, .STEP, .STP)..."
Get-ChildItem -Path $tmpDir -Recurse -Include *.SLDPRT,*.SLDASM,*.STEP,*.STP | ForEach-Object {
    $dest = Join-Path -Path $cadDir -ChildPath $_.Name
    # Check if a file with the same name already exists in the destination to avoid overwriting issues, 
    # though we are dumping everything flat into CAD/ so we just copy it.
    Copy-Item -Path $_.FullName -Destination $dest -Force
    Write-Host "Copied: $($_.Name)"
}

Write-Host "Cleaning up repository..."
Remove-Item -Recurse -Force $tmpDir

Write-Host "Done!"
