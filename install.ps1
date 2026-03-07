#Requires -Version 5.1
<#
.SYNOPSIS
    DocuMentor - Installer for Windows
.DESCRIPTION
    Step 1: Install OpenClaw (official installer)
    Step 2: Copy DocuMentor workspace + skills
    Python deps are installed by the bot on first conversation.
.EXAMPLE
    irm https://raw.githubusercontent.com/Asphyksia/DocuMentor/main/install.ps1 -OutFile $env:TEMP\dm-install.ps1; & $env:TEMP\dm-install.ps1
#>

$ErrorActionPreference = "Stop"

function Info($msg)    { Write-Host "  [i] $msg" -ForegroundColor Cyan }
function Success($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Warn($msg)    { Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Fail($msg)    { Write-Host "  [X] $msg" -ForegroundColor Red; exit 1 }
function Header($msg)  { Write-Host "`n  $msg`n" -ForegroundColor White -BackgroundColor DarkBlue }

$RepoUrl           = "https://github.com/Asphyksia/DocuMentor.git"
$InstallDir        = Join-Path $env:USERPROFILE "DocuMentor"
$OpenClawConfig    = Join-Path $env:USERPROFILE ".openclaw"
$OpenClawWorkspace = Join-Path $OpenClawConfig "workspace"

Write-Host ""
Write-Host "  ======================================================" -ForegroundColor White
Write-Host "  DocuMentor - Instalador (Windows)" -ForegroundColor White
Write-Host "  Inteligencia documental con IA" -ForegroundColor White
Write-Host "  ======================================================" -ForegroundColor White
Write-Host ""

# ── Step 1: Install OpenClaw ────────────────────────────
Header "1/2 - OpenClaw..."

# Refresh PATH
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
$npmGlobal = Join-Path $env:APPDATA "npm"
if (Test-Path $npmGlobal) { $env:PATH = "$npmGlobal;$env:PATH" }

$openclawFound = $false
try {
    $ErrorActionPreference = "Continue"
    $ver = openclaw --version 2>&1
    $ErrorActionPreference = "Stop"
    if ($LASTEXITCODE -eq 0) { $openclawFound = $true }
} catch { $ErrorActionPreference = "Stop" }

if ($openclawFound) {
    Success "OpenClaw ya instalado ($ver)"
} else {
    Info "Instalando OpenClaw con el instalador oficial..."
    try {
        $ErrorActionPreference = "Continue"
        $clawScript = "$env:TEMP\openclaw-official.ps1"
        Invoke-WebRequest -Uri "https://openclaw.ai/install.ps1" -OutFile $clawScript -UseBasicParsing
        & $clawScript -NoOnboard
        $ErrorActionPreference = "Stop"
    } catch {
        $ErrorActionPreference = "Stop"
        Fail "Error instalando OpenClaw: $_`nInstala manualmente: https://docs.openclaw.ai/start/getting-started"
    }

    # Refresh PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    if (Test-Path $npmGlobal) { $env:PATH = "$npmGlobal;$env:PATH" }
    try {
        $npmPrefix = (npm config get prefix 2>$null).Trim()
        if ($npmPrefix -and (Test-Path $npmPrefix)) { $env:PATH = "$npmPrefix;$env:PATH" }
    } catch {}

    $openclawFound = $false
    try {
        $ErrorActionPreference = "Continue"
        $ver = openclaw --version 2>&1
        $ErrorActionPreference = "Stop"
        if ($LASTEXITCODE -eq 0) { $openclawFound = $true }
    } catch { $ErrorActionPreference = "Stop" }

    if ($openclawFound) {
        Success "OpenClaw instalado"
    } else {
        Fail "OpenClaw no encontrado tras instalar. Abre PowerShell nuevo y ejecuta el instalador de nuevo."
    }
}

# ── Step 2: Clone repo + copy workspace ─────────────────
Header "2/2 - Instalando workspace DocuMentor..."

# Need git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Info "Instalando git via winget..."
    try {
        winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements 2>$null
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
        $gitPaths = @("$env:ProgramFiles\Git\cmd", "${env:ProgramFiles(x86)}\Git\cmd")
        foreach ($gp in $gitPaths) {
            if (Test-Path "$gp\git.exe") { $env:PATH = "$gp;$env:PATH"; break }
        }
    } catch {}
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Fail "git no disponible. Instala desde https://git-scm.com y vuelve a ejecutar."
    }
}

if (Test-Path (Join-Path $InstallDir ".git")) {
    Info "Actualizando repo existente..."
    Push-Location $InstallDir
    git pull --ff-only 2>$null
    Pop-Location
} else {
    if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
    git clone $RepoUrl $InstallDir
}
Success "Repo: $InstallDir"

foreach ($d in @("skills","memory","documents")) {
    $p = Join-Path $OpenClawWorkspace $d
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

foreach ($f in @("SOUL.md","AGENTS.md","TOOLS.md","HEARTBEAT.md")) {
    Copy-Item -Force (Join-Path $InstallDir "workspace\$f") (Join-Path $OpenClawWorkspace $f)
}
$userMd = Join-Path $OpenClawWorkspace "USER.md"
if (-not (Test-Path $userMd)) { Copy-Item (Join-Path $InstallDir "workspace\USER.md") $userMd }
$memMd = Join-Path $OpenClawWorkspace "MEMORY.md"
if (-not (Test-Path $memMd)) { "" | Out-File -Encoding utf8 $memMd }
Copy-Item -Recurse -Force (Join-Path $InstallDir "workspace\skills\*") (Join-Path $OpenClawWorkspace "skills\")

foreach ($r in @("BOOTSTRAP.md","IDENTITY.md")) {
    $rp = Join-Path $OpenClawWorkspace $r
    if (Test-Path $rp) { Remove-Item -Force $rp }
}
Success "Workspace instalado en: $OpenClawWorkspace"

# Start gateway
try {
    openclaw doctor --repair 2>$null
    openclaw gateway install --force 2>$null
    openclaw gateway restart 2>$null
    Success "Gateway iniciado"
} catch {
    Warn "No se pudo iniciar el gateway. Ejecuta: openclaw gateway start"
}

# ── Done ────────────────────────────────────────────────
Write-Host ""
Write-Host "  ======================================================" -ForegroundColor Green
Write-Host "  DocuMentor instalado!" -ForegroundColor Green
Write-Host "  ======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Abre OpenClaw y habla con el bot." -ForegroundColor White
Write-Host "  El asistente se configurara y preparara todo en la primera conversacion." -ForegroundColor White
Write-Host ""
Write-Host "  openclaw dashboard    <- abre el panel de control" -ForegroundColor Cyan
Write-Host "  openclaw gateway logs <- ver logs" -ForegroundColor Gray
Write-Host ""
