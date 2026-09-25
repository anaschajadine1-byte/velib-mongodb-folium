$ErrorActionPreference = "Stop"

Write-Host "[1/3] Création de l'environnement virtuel..."
python -m venv .venv

Write-Host "[2/3] Mise à jour de pip..."
.\.venv\Scripts\python.exe -m pip install --upgrade pip

Write-Host "[3/3] Installation des dépendances..."
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host ""
Write-Host "Installation terminée."
Write-Host "Lance ensuite : .\run.ps1"
