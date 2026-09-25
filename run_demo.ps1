$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Environnement virtuel absent. Lance d'abord .\setup.ps1"
    exit 1
}

& .\.venv\Scripts\python.exe app.py --demo @args
