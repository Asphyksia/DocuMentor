#Requires -Version 5.1
<#
.SYNOPSIS
    DocuMentor - One-Command Installer for Windows (via WSL2)
.DESCRIPTION
    Sets up WSL2 with Ubuntu if needed, then runs the Linux installer inside WSL.
    OpenClaw requires WSL2 on Windows.
.EXAMPLE
    irm https://raw.githubusercontent.com/Asphyksia/DocuMentor/main/install.ps1 -OutFile $env:TEMP\dm-install.ps1; & $env:TEMP\dm-install.ps1
#>

$ErrorActionPreference = "Stop"

function Info($msg)    { Write-Host "  [i] $msg" -ForegroundColor Cyan }
function Success($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Warn($msg)    { Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Fail($msg)    { Write-Host "  [X] $msg" -ForegroundColor Red; exit 1 }
function Header($msg)  { Write-Host "`n  $msg`n" -ForegroundColor White -BackgroundColor DarkBlue }

Write-Host ""
Write-Host "  ======================================================" -ForegroundColor White
Write-Host "  DocuMentor - Instalador (Windows)" -ForegroundColor White
Write-Host "  Inteligencia documental con IA" -ForegroundColor White
Write-Host "  ======================================================" -ForegroundColor White
Write-Host ""
Write-Host "  OpenClaw requiere WSL2 en Windows." -ForegroundColor Yellow
Write-Host "  Este instalador configura WSL2 y ejecuta el setup de Linux." -ForegroundColor Yellow
Write-Host ""

# ── Step 1: Check/Install WSL2 ─────────────────────────
Header "1/3 - Verificando WSL2..."

$wslAvailable = $false
try {
    $ErrorActionPreference_bak = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $wslCheck = wsl --status 2>&1
    $ErrorActionPreference = $ErrorActionPreference_bak
    if ($LASTEXITCODE -eq 0) {
        $wslAvailable = $true
    }
} catch {
    $ErrorActionPreference = "Stop"
}

# Also check if any distro is installed
$wslDistro = $null
if ($wslAvailable) {
    try {
        $ErrorActionPreference_bak = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $distroList = wsl -l -q 2>&1 | Where-Object { $_ -match '\S' } | ForEach-Object { $_.Trim() -replace '\x00','' }
        $ErrorActionPreference = $ErrorActionPreference_bak
        if ($distroList) {
            # Pick Ubuntu if available, otherwise first distro
            foreach ($d in $distroList) {
                if ($d -match "Ubuntu") {
                    $wslDistro = $d
                    break
                }
            }
            if (-not $wslDistro) {
                $wslDistro = $distroList[0]
            }
        }
    } catch {
        $ErrorActionPreference = "Stop"
    }
}

if ($wslAvailable -and $wslDistro) {
    Success "WSL2 disponible con distro: $wslDistro"
} elseif ($wslAvailable -and -not $wslDistro) {
    Info "WSL2 disponible pero sin distro instalada. Instalando Ubuntu..."
    try {
        wsl --install -d Ubuntu --no-launch
        $wslDistro = "Ubuntu"
        Write-Host ""
        Warn "Ubuntu instalado en WSL2."
        Warn "Puede que necesites REINICIAR el PC para completar la instalacion."
        Write-Host ""
        $restart = Read-Host "  Si ya has reiniciado o quieres continuar, pulsa Enter. Si no, escribe 'salir'"
        if ($restart -eq "salir") {
            Info "Reinicia el PC y vuelve a ejecutar este instalador."
            exit 0
        }
    } catch {
        Fail "No se pudo instalar Ubuntu en WSL2: $_`nEjecuta manualmente: wsl --install -d Ubuntu"
    }
} else {
    Info "WSL2 no detectado. Instalando..."
    try {
        Write-Host ""
        Info "Esto puede tardar unos minutos y requerir reinicio del PC."
        Write-Host ""
        wsl --install -d Ubuntu --no-launch
        Write-Host ""
        Warn "================================================================"
        Warn "WSL2 + Ubuntu instalados."
        Warn "REINICIA EL PC y vuelve a ejecutar este instalador."
        Warn "================================================================"
        Write-Host ""
        Read-Host "  Pulsa Enter para salir"
        exit 0
    } catch {
        Fail "No se pudo instalar WSL2: $_`nActiva WSL2 manualmente: https://learn.microsoft.com/windows/wsl/install"
    }
}

# ── Step 2: Run Linux installer inside WSL ──────────────
Header "2/3 - Ejecutando instalador de DocuMentor en WSL..."

Info "Lanzando install.sh dentro de WSL ($wslDistro)..."
Write-Host ""

try {
    # Write a launcher script that WSL will execute interactively
    # Using wsl with -e bash and a script file preserves stdin for interactive prompts
    $wslScript = "/tmp/dm-install.sh"

    # Download the installer inside WSL first
    Info "Descargando instalador..."
    wsl -d $wslDistro -- bash -c "curl -fsSL https://raw.githubusercontent.com/Asphyksia/DocuMentor/main/install.sh -o $wslScript && chmod +x $wslScript"
    if ($LASTEXITCODE -ne 0) {
        Fail "No se pudo descargar el instalador"
    }

    # Run interactively — wsl without --, bash with -i keeps stdin open
    Info "Ejecutando instalador interactivo (puedes escribir normalmente)..."
    Write-Host ""
    wsl -d $wslDistro -e bash -li $wslScript
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Fail "El instalador de Linux fallo con codigo $exitCode"
    }
} catch {
    Fail "Error ejecutando el instalador en WSL: $_"
}

# ── Step 3: Done ────────────────────────────────────────
Header "3/3 - Completado"

Write-Host ""
Write-Host "  ======================================================" -ForegroundColor Green
Write-Host "  DocuMentor instalado correctamente en WSL2!" -ForegroundColor Green
Write-Host "  ======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Para usar DocuMentor, abre WSL:" -ForegroundColor White
Write-Host "     wsl" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Comandos utiles (dentro de WSL):" -ForegroundColor White
Write-Host "     openclaw gateway status     # Ver estado" -ForegroundColor Gray
Write-Host "     openclaw gateway restart    # Reiniciar" -ForegroundColor Gray
Write-Host "     openclaw gateway logs       # Ver logs" -ForegroundColor Gray
Write-Host ""
Write-Host "  Dashboard (dentro de WSL):" -ForegroundColor White
Write-Host "     cd ~/DocuMentor && streamlit run dashboard/app.py" -ForegroundColor Cyan
Write-Host "     Accede en: http://localhost:8501" -ForegroundColor Gray
Write-Host ""
Write-Host "  Docs:     https://docs.openclaw.ai" -ForegroundColor Gray
Write-Host "  Soporte:  https://discord.gg/clawd" -ForegroundColor Gray
Write-Host ""
