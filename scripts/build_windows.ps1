$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectDir

python -m pip install -e ".[build]"
python scripts/build_icons.py
python -m PyInstaller --noconfirm --clean DropMD.spec

$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) {
    throw "Inno Setup 6 is required: https://jrsoftware.org/isdl.php"
}
& $Iscc packaging/windows/installer.iss
Write-Host "Created release/DropMD-Windows-Setup.exe"
