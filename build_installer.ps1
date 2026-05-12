# Build HamsterAI_Setup.exe using PyInstaller
# Run from the project root: .\build_installer.ps1

Set-Location $PSScriptRoot

Write-Host "`n=== Hamster AI — Installer Build ===" -ForegroundColor Yellow

# Check pyinstaller
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Cyan
    pip install pyinstaller --quiet
}

# Build
Write-Host "Building HamsterAI_Setup.exe..." -ForegroundColor Cyan
Set-Location installer
pyinstaller installer.spec --distpath ..\dist --workpath ..\build\installer_work --noconfirm
Set-Location ..

$output = "dist\HamsterAI_Setup.exe"
if (Test-Path $output) {
    $size = [math]::Round((Get-Item $output).Length / 1MB, 1)
    Write-Host "`n=== Build complete ===" -ForegroundColor Green
    Write-Host "Output : $((Resolve-Path $output).Path)" -ForegroundColor Green
    Write-Host "Size   : $size MB" -ForegroundColor Green
} else {
    Write-Host "`nBuild failed — $output not found." -ForegroundColor Red
    exit 1
}
