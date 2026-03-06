#Requires -Version 5.1
<#
.SYNOPSIS
    DocuMentor — One-Command Installer for Windows
.DESCRIPTION
    Installs OpenClaw (if needed) + custom workspace + Python deps
.EXAMPLE
    irm https://raw.githubusercontent.com/Asphyksia/DocuMentor/main/install.ps1 | iex
#>

$ErrorActionPreference = "Stop"

# ── Colors ──────────────────────────────────────────────
function Info($msg)    { Write-Host "  [i] $msg" -ForegroundColor Cyan }
function Success($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Warn($msg)    { Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Fail($msg)    { Write-Host "  [X] $msg" -ForegroundColor Red; exit 1 }
function Header($msg)  { Write-Host "`n  $msg`n" -ForegroundColor White -BackgroundColor DarkBlue }

$RepoUrl          = "https://github.com/Asphyksia/DocuMentor.git"
$InstallDir       = Join-Path $env:USERPROFILE "DocuMentor"
$OpenClawConfig   = Join-Path $env:USERPROFILE ".openclaw"
$OpenClawWorkspace= Join-Path $OpenClawConfig "workspace"
$ConfigFile       = Join-Path $OpenClawConfig "openclaw.json"

# ── Banner ──────────────────────────────────────────────
Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════════╗" -ForegroundColor White
Write-Host "  ║  DocuMentor — Instalador (Windows)         ║" -ForegroundColor White
Write-Host "  ║  Inteligencia documental con IA               ║" -ForegroundColor White
Write-Host "  ╚═══════════════════════════════════════════════╝" -ForegroundColor White
Write-Host ""

# ── Step 1: System dependencies ─────────────────────────
Header "1/6 · Verificando dependencias del sistema..."

# Check Node.js
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVer = node --version
    Success "Node.js: $nodeVer"
} else {
    Warn "Node.js no encontrado."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Info "Instalando Node.js via winget..."
        try {
            $wingetOut = winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements 2>&1
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
            # Check common Node paths
            $nodePaths = @("$env:ProgramFiles\nodejs", "${env:ProgramFiles(x86)}\nodejs")
            foreach ($np in $nodePaths) {
                if ((Test-Path "$np\node.exe") -and ($env:PATH -notlike "*$np*")) {
                    $env:PATH = "$np;$env:PATH"
                    break
                }
            }
            if (Get-Command node -ErrorAction SilentlyContinue) {
                Success "Node.js instalado"
            } else {
                Fail "Node.js no se encontró después de instalar. Cierra y abre PowerShell, luego ejecuta este script de nuevo."
            }
        } catch {
            Fail "Error instalando Node.js: $_`nInstálalo manualmente: https://nodejs.org"
        }
    } else {
        Fail "winget no disponible. Instala Node.js manualmente: https://nodejs.org"
    }
}

# Check Git
if (Get-Command git -ErrorAction SilentlyContinue) {
    Success "git disponible"
} else {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Info "Instalando git via winget..."
        try {
            $wingetOut = winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements 2>&1
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
            # Check common git paths
            $gitPaths = @("$env:ProgramFiles\Git\cmd", "${env:ProgramFiles(x86)}\Git\cmd")
            foreach ($gp in $gitPaths) {
                if ((Test-Path "$gp\git.exe") -and ($env:PATH -notlike "*$gp*")) {
                    $env:PATH = "$gp;$env:PATH"
                    break
                }
            }
            if (Get-Command git -ErrorAction SilentlyContinue) {
                Success "git instalado"
            } else {
                Fail "git no se encontró después de instalar. Cierra y abre PowerShell, luego ejecuta este script de nuevo."
            }
        } catch {
            Fail "Error instalando git: $_`nInstálalo manualmente: https://git-scm.com"
        }
    } else {
        Fail "git no encontrado y winget no disponible. Instálalo manualmente: https://git-scm.com"
    }
}

# Check Python (Windows has a fake "python" alias that redirects to MS Store — must handle carefully)
$pythonCmd = $null
try {
    $ErrorActionPreference_backup = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $pyVer = & python --version 2>&1
    $ErrorActionPreference = $ErrorActionPreference_backup
    if ($LASTEXITCODE -eq 0 -and "$pyVer" -match "Python 3") {
        $pythonCmd = "python"
        Success "Python: $pyVer"
    }
} catch {
    $ErrorActionPreference = "Stop"
}
if (-not $pythonCmd) {
    try {
        $ErrorActionPreference_backup = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $pyVer = & python3 --version 2>&1
        $ErrorActionPreference = $ErrorActionPreference_backup
        if ($LASTEXITCODE -eq 0 -and "$pyVer" -match "Python 3") {
            $pythonCmd = "python3"
            Success "Python: $pyVer"
        }
    } catch {
        $ErrorActionPreference = "Stop"
    }
}
if (-not $pythonCmd) {
    Warn "Python3 no encontrado."
    $pyInstalled = $false
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Info "Instalando Python via winget..."
        try {
            $wingetOut = winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements 2>&1
            # Refresh PATH after install
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
            # Also check common Python install locations
            $pyPaths = @(
                "$env:LOCALAPPDATA\Programs\Python\Python312",
                "$env:LOCALAPPDATA\Programs\Python\Python311",
                "$env:LOCALAPPDATA\Programs\Python\Python310",
                "$env:ProgramFiles\Python312",
                "$env:ProgramFiles\Python311"
            )
            foreach ($pp in $pyPaths) {
                if ((Test-Path "$pp\python.exe") -and ($env:PATH -notlike "*$pp*")) {
                    $env:PATH = "$pp;$pp\Scripts;$env:PATH"
                    break
                }
            }

            if (Get-Command python -ErrorAction SilentlyContinue) {
                $pythonCmd = "python"
                $pyInstalled = $true
                Success "Python instalado"
            }
        } catch {
            Warn "winget no pudo instalar Python: $_"
        }
    }
    if (-not $pyInstalled) {
        Warn "Python no está instalado. El dashboard y procesamiento de docs no funcionarán."
        Warn "Instálalo manualmente desde: https://www.python.org/downloads/"
        Warn "Marca 'Add Python to PATH' durante la instalación."
        Write-Host ""
        $cont = Read-Host "  ¿Continuar sin Python? [S/n]"
        if ($cont -in @("n", "no")) {
            Fail "Instalación cancelada. Instala Python y vuelve a ejecutar el script."
        }
    }
}

Success "Dependencias del sistema OK"

# ── Step 2: Check/Install OpenClaw ──────────────────────
Header "2/6 · Verificando OpenClaw..."

# Refresh PATH
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
$npmGlobal = Join-Path $env:APPDATA "npm"
if (Test-Path $npmGlobal) { $env:PATH = "$npmGlobal;$env:PATH" }

if (Get-Command openclaw -ErrorAction SilentlyContinue) {
    $clawVer = openclaw --version 2>&1
    Success "OpenClaw ya instalado ($clawVer)"
} else {
    Info "OpenClaw no encontrado. Instalando con el instalador oficial..."
    try {
        $ErrorActionPreference_backup = $ErrorActionPreference
        $ErrorActionPreference = "Continue"

        # Download and run the official OpenClaw Windows installer
        $clawInstaller = "$env:TEMP\openclaw-install.ps1"
        Invoke-WebRequest -Uri "https://openclaw.ai/install.ps1" -OutFile $clawInstaller -UseBasicParsing
        & $clawInstaller -NoOnboard

        $ErrorActionPreference = $ErrorActionPreference_backup

        # Refresh PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        if (Test-Path $npmGlobal) { $env:PATH = "$npmGlobal;$env:PATH" }
        # Check npm prefix
        try {
            $npmPrefix = (npm config get prefix 2>$null).Trim()
            if ($npmPrefix -and (Test-Path $npmPrefix) -and ($env:PATH -notlike "*$npmPrefix*")) {
                $env:PATH = "$npmPrefix;$env:PATH"
            }
        } catch {}

        if (Get-Command openclaw -ErrorAction SilentlyContinue) {
            Success "OpenClaw instalado"
        } else {
            # Fallback: try npm directly with env var to skip native builds
            Warn "Instalador oficial no encontró openclaw en PATH. Intentando npm directo..."
            $env:SHARP_IGNORE_GLOBAL_LIBVIPS = "1"
            $npmProc = Start-Process -FilePath "npm" -ArgumentList "install -g openclaw@latest" `
                -NoNewWindow -Wait -PassThru -RedirectStandardOutput "$env:TEMP\openclaw-npm-out.txt" `
                -RedirectStandardError "$env:TEMP\openclaw-npm-err.txt"

            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
            if (Test-Path $npmGlobal) { $env:PATH = "$npmGlobal;$env:PATH" }

            if (Get-Command openclaw -ErrorAction SilentlyContinue) {
                Success "OpenClaw instalado via npm"
            } else {
                Fail "OpenClaw no se pudo instalar. Prueba manualmente:`n  npm install -g openclaw@latest`nO considera usar WSL2: https://learn.microsoft.com/windows/wsl/install"
            }
        }
    } catch {
        Fail "Error instalando OpenClaw: $_`nConsidera usar WSL2: https://learn.microsoft.com/windows/wsl/install"
    }
}

# ── Step 3: Clone/Update repo ───────────────────────────
Header "3/6 · Descargando workspace..."

if (Test-Path (Join-Path $InstallDir ".git")) {
    Info "Directorio existente. Actualizando..."
    Push-Location $InstallDir
    git pull --ff-only 2>$null
    Pop-Location
} else {
    if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
    git clone $RepoUrl $InstallDir
}
Success "Workspace descargado: $InstallDir"

# ── Step 4: Copy workspace to OpenClaw ──────────────────
Header "4/6 · Instalando workspace personalizado..."

# Create dirs
foreach ($d in @("skills", "memory", "documents")) {
    $p = Join-Path $OpenClawWorkspace $d
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

# Core workspace files (always overwrite)
foreach ($f in @("SOUL.md", "AGENTS.md", "TOOLS.md", "HEARTBEAT.md")) {
    Copy-Item -Force (Join-Path $InstallDir "workspace\$f") (Join-Path $OpenClawWorkspace $f)
}

# USER.md: only copy if not exists
$userMd = Join-Path $OpenClawWorkspace "USER.md"
if (-not (Test-Path $userMd)) {
    Copy-Item (Join-Path $InstallDir "workspace\USER.md") $userMd
}

# MEMORY.md: never overwrite
$memMd = Join-Path $OpenClawWorkspace "MEMORY.md"
if (-not (Test-Path $memMd)) { "" | Out-File -Encoding utf8 $memMd }

# Copy skills
Copy-Item -Recurse -Force (Join-Path $InstallDir "workspace\skills\*") (Join-Path $OpenClawWorkspace "skills\")

# Clean residual onboard files
foreach ($r in @("BOOTSTRAP.md", "IDENTITY.md")) {
    $rp = Join-Path $OpenClawWorkspace $r
    if (Test-Path $rp) { Remove-Item -Force $rp }
}

Success "Workspace instalado en: $OpenClawWorkspace"

# ── Step 5: API Key + Channel ───────────────────────────
Header "5/6 · Configuración..."

$SkipConfig = $false
$ExistingToken = $null

# Check existing config
if (Test-Path $ConfigFile) {
    $configContent = Get-Content $ConfigFile -Raw -ErrorAction SilentlyContinue
    # Try to extract existing token
    if ($configContent -match '"token"\s*:\s*"([^"]+)"') {
        $ExistingToken = $Matches[1]
    }

    if ($configContent -match "relaygpu") {
        Info "Configuración de DocuMentor detectada."
        $reconfig = Read-Host "  ¿Reconfigurar? [s/N]"
        if ($reconfig -notin @("s", "si", "sí")) {
            Info "Manteniendo configuración actual."
            $SkipConfig = $true
        }
    } else {
        Info "Configuración de OpenClaw existente (sin DocuMentor)."
        $cont = Read-Host "  ¿Sobreescribir con config de DocuMentor? [S/n]"
        if ($cont -in @("n", "no")) {
            Info "Saltando configuración."
            $SkipConfig = $true
        }
    }
}

if (-not $SkipConfig) {
    # API Key
    Write-Host ""
    Write-Host "  Key de OpenGPU Relay"
    Write-Host "  Consigue una en: https://relaygpu.com"
    Write-Host ""
    do {
        $apiKey = Read-Host "  API Key"
        if (-not $apiKey) { Warn "La API key no puede estar vacia" }
    } while (-not $apiKey)

    # Channel
    Write-Host ""
    Write-Host "  Canal de comunicacion"
    Write-Host "  1 - Telegram -- recomendado"
    Write-Host "  2 - WhatsApp"
    Write-Host "  3 - Discord"
    Write-Host "  4 - Omitir por ahora"
    Write-Host ""

    $channelName = ""
    $channelToken = ""

    do {
        $chChoice = Read-Host "  Opcion [1]"
        if (-not $chChoice) { $chChoice = "1" }
        switch ($chChoice) {
            "1" {
                $channelName = "telegram"
                Write-Host ""
                Write-Host "  Crea un bot con @BotFather en Telegram y pega el token:"
                $channelToken = Read-Host "  Bot Token"
                break
            }
            "2" {
                $channelName = "whatsapp"
                Info "WhatsApp mostrara un QR despues del setup"
                break
            }
            "3" {
                $channelName = "discord"
                Write-Host ""
                Write-Host "  Crea un bot en https://discord.com/developers/applications"
                $channelToken = Read-Host "  Bot Token"
                break
            }
            "4" { break }
            default { Warn "Elige 1-4" }
        }
    } while ($chChoice -notin @("1","2","3","4"))

    # Gateway token
    if ($ExistingToken) {
        $gwToken = $ExistingToken
        Info "Reutilizando token del gateway existente"
    } else {
        $gwToken = -join ((1..32) | ForEach-Object { "{0:x2}" -f (Get-Random -Max 256) })
    }

    # Build config as a PowerShell object, then convert to JSON (avoids here-string parsing issues)
    $wsPath = $OpenClawWorkspace -replace '\\', '/'

    $config = @{
        models = @{
            providers = @{
                "relaygpu-anthropic" = @{
                    baseUrl = "https://relay.opengpu.network/v2/anthropic/v1/"
                    apiKey = $apiKey
                    api = "anthropic-messages"
                    models = @(
                        @{
                            id = "anthropic/claude-sonnet-4-6"
                            name = "Claude Sonnet 4-6 (OpenGPU)"
                            api = "anthropic-messages"
                            reasoning = $true
                            input = @("text")
                            cost = @{ input = 0; output = 0; cacheRead = 0; cacheWrite = 0 }
                            contextWindow = 200000
                            maxTokens = 64000
                        }
                    )
                }
                "relaygpu-openai" = @{
                    baseUrl = "https://relay.opengpu.network/v2/openai/v1/"
                    apiKey = $apiKey
                    api = "openai-completions"
                    models = @(
                        @{
                            id = "moonshotai/kimi-k2.5"
                            name = "Kimi K2.5 (OpenGPU)"
                            api = "openai-completions"
                            reasoning = $true
                            input = @("text")
                            cost = @{ input = 0; output = 0; cacheRead = 0; cacheWrite = 0 }
                            contextWindow = 128000
                            maxTokens = 65536
                        },
                        @{
                            id = "deepseek-ai/DeepSeek-V3.1"
                            name = "DeepSeek V3.1 (OpenGPU)"
                            api = "openai-completions"
                            reasoning = $true
                            input = @("text")
                            cost = @{ input = 0; output = 0; cacheRead = 0; cacheWrite = 0 }
                            contextWindow = 128000
                            maxTokens = 65536
                        }
                    )
                }
            }
        }
        agents = @{
            defaults = @{
                model = @{ primary = "relaygpu-openai/moonshotai/kimi-k2.5" }
                workspace = $wsPath
            }
        }
        gateway = @{
            mode = "local"
            auth = @{ token = $gwToken }
        }
    }

    # Add channel config if selected
    switch ($channelName) {
        "telegram" {
            $config.channels = @{
                telegram = @{
                    enabled = $true
                    botToken = $channelToken
                    dmPolicy = "allowlist"
                    allowFrom = @()
                    groupPolicy = "allowlist"
                    streaming = "partial"
                }
            }
        }
        "discord" {
            $config.channels = @{
                discord = @{
                    enabled = $true
                    botToken = $channelToken
                    dmPolicy = "allowlist"
                    allowFrom = @()
                    groupPolicy = "allowlist"
                }
            }
        }
        "whatsapp" {
            $config.channels = @{
                whatsapp = @{
                    enabled = $true
                    dmPolicy = "allowlist"
                    allowFrom = @()
                }
            }
        }
    }

    # Ensure config dir exists
    if (-not (Test-Path $OpenClawConfig)) {
        New-Item -ItemType Directory -Path $OpenClawConfig -Force | Out-Null
    }

    # Convert to JSON and write
    $configJson = $config | ConvertTo-Json -Depth 10
    $configJson | Out-File -Encoding utf8 $ConfigFile
    Success "Configuracion guardada: $ConfigFile"
}

# ── Step 6: Install Python deps + Start ─────────────────
Header "6/6 · Instalando dependencias y arrancando..."

$pythonDeps = "chromadb pdfplumber openpyxl python-docx matplotlib streamlit pandas prompt-guard"
$pipInstalled = $false

if ($pythonCmd) {
    Info "Instalando dependencias Python..."
    try {
        & $pythonCmd -m pip install -q $pythonDeps.Split(" ") 2>$null
        $pipInstalled = $true
    } catch {}

    if (-not $pipInstalled) {
        try {
            & $pythonCmd -m pip install --user -q $pythonDeps.Split(" ") 2>$null
            $pipInstalled = $true
        } catch {}
    }

    if ($pipInstalled) {
        Success "Dependencias Python instaladas"
    } else {
        Warn "No se pudieron instalar algunas dependencias."
        Warn "Prueba manualmente: $pythonCmd -m pip install $pythonDeps"
    }
} else {
    Warn "Python no disponible. Instala las dependencias manualmente."
}

# Start gateway
Info "Iniciando OpenClaw Gateway..."
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
Write-Host "  ══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ¡DocuMentor instalado correctamente!" -ForegroundColor Green
Write-Host "  ══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Workspace:  $OpenClawWorkspace"
Write-Host "  Config:     $ConfigFile"
Write-Host ""

if ($channelName) {
    Write-Host "  Canal: $channelName"
    Write-Host ""
    Write-Host "  IMPORTANTE: Añade tu ID de usuario a 'allowFrom' en:"
    Write-Host "     $ConfigFile"
    Write-Host ""
    Write-Host "     Cómo encontrar tu ID:"
    Write-Host "     1. Manda un mensaje al bot"
    Write-Host "     2. Mira los logs: openclaw gateway logs | Select -Last 20"
    Write-Host "     3. Busca tu ID numérico"
    Write-Host "     4. Añádelo a allowFrom: [`"TU_ID`"]"
    Write-Host "     5. Reinicia: openclaw gateway restart"
    Write-Host ""
}

if ($channelName -eq "whatsapp") {
    Write-Host "  Para vincular WhatsApp: openclaw channels login"
    Write-Host ""
}

if ($gwToken) {
    Write-Host "  Token del dashboard: $gwToken"
    Write-Host "     (guárdalo para acceder al dashboard web de OpenClaw)"
    Write-Host ""
}

Write-Host "  Iniciar dashboard visual:"
Write-Host "     cd $InstallDir; streamlit run dashboard\app.py"
Write-Host ""
Write-Host "  DocuMentor está listo. ¡Manda un mensaje al bot para empezar!"
Write-Host ""
Write-Host "  ─────────────────────────────────────────────"
Write-Host "  Comandos útiles:"
Write-Host "     openclaw gateway status     # Ver estado"
Write-Host "     openclaw gateway restart    # Reiniciar"
Write-Host "     openclaw gateway logs       # Ver logs"
Write-Host "     openclaw update             # Actualizar OpenClaw"
Write-Host ""
Write-Host "  Docs:     https://docs.openclaw.ai"
Write-Host "  Soporte:  https://discord.gg/clawd"
Write-Host ""
