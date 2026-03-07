#Requires -Version 5.1
<#
.SYNOPSIS
    DocuMentor - Uninstaller for Windows
#>

$ErrorActionPreference = "Continue"

function Info($msg)    { Write-Host "  [i] $msg" -ForegroundColor Cyan }
function Success($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Warn($msg)    { Write-Host "  [!] $msg" -ForegroundColor Yellow }

$InstallDir        = Join-Path $env:USERPROFILE "DocuMentor"
$OpenClawConfig    = Join-Path $env:USERPROFILE ".openclaw"
$OpenClawWorkspace = Join-Path $OpenClawConfig "workspace"

Write-Host ""
Write-Host "  ======================================================" -ForegroundColor White
Write-Host "  DocuMentor - Desinstalador (Windows)" -ForegroundColor White
Write-Host "  ======================================================" -ForegroundColor White
Write-Host ""
Write-Host "  Esto eliminara:" -ForegroundColor Yellow
Write-Host "    Repo local:  $InstallDir" -ForegroundColor Yellow
Write-Host "    Workspace:   $OpenClawWorkspace" -ForegroundColor Yellow
Write-Host "    Documentos y datos indexados" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "  Continuar? [s/N]"
if ($confirm -notin @("s","si")) {
    Write-Host "  Cancelado."
    exit 0
}

Write-Host ""

# Stop gateway
try {
    openclaw gateway stop 2>$null
    Success "Gateway detenido"
} catch {}

# Remove repo
if (Test-Path $InstallDir) {
    Info "Eliminando repo: $InstallDir"
    Remove-Item -Recurse -Force $InstallDir
    Success "Repo eliminado"
}

# Remove workspace
if (Test-Path $OpenClawWorkspace) {
    Info "Eliminando workspace: $OpenClawWorkspace"
    Remove-Item -Recurse -Force $OpenClawWorkspace
    Success "Workspace eliminado"
}

# Remove OpenClaw config
Write-Host ""
$confirmConfig = Read-Host "  Eliminar tambien la configuracion de OpenClaw (~\.openclaw)? [s/N]"
if ($confirmConfig -in @("s","si")) {
    if (Test-Path $OpenClawConfig) {
        Remove-Item -Recurse -Force $OpenClawConfig
        Success "Configuracion de OpenClaw eliminada"
    }
}

# Uninstall OpenClaw
Write-Host ""
$confirmClaw = Read-Host "  Desinstalar tambien OpenClaw? [s/N]"
if ($confirmClaw -in @("s","si")) {
    try {
        openclaw uninstall 2>$null
        Success "OpenClaw desinstalado"
    } catch {
        try {
            npm uninstall -g openclaw 2>$null
            Success "OpenClaw desinstalado via npm"
        } catch {
            Warn "No se pudo desinstalar OpenClaw automaticamente. Ejecuta: npm uninstall -g openclaw"
        }
    }
}

Write-Host ""
Write-Host "  Desinstalacion completada." -ForegroundColor Green
Write-Host ""
