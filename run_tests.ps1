# Script para ejecutar tests con pytest en Windows
# Uso: .\run_tests.ps1 [filtro_opcional]
# Ej: .\run_tests.ps1 test_generation_service

param([string]$Filter = "")

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if ([string]::IsNullOrEmpty($Filter)) {
    Write-Host "Ejecutando todos los tests..." -ForegroundColor Green
    & python -m pytest src/tests -v --tb=short
} else {
    Write-Host "Ejecutando tests que coincidan con: $Filter" -ForegroundColor Green
    & python -m pytest src/tests -k $Filter -v --tb=short
}
