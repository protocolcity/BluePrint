# BluePrint — Windows first install (nothing else required except Python)
#
# For someone with a blank PC:
#   1. Install Python 3.11+ from https://www.python.org/downloads/windows/
#      → tick "Add python.exe to PATH" → finish → close & reopen PowerShell
#   2. Paste this whole file into PowerShell, OR run:
#        powershell -ExecutionPolicy Bypass -File install_windows.ps1
#
# What this does:
#   • finds Python 3.11+
#   • pip installs BluePrint + WorkLane + WorkForce
#   • creates a workspace folder under your user profile
#   • starts the suite (keep this window open)
#   • open http://127.0.0.1:8801/ in your browser
#
# Optional flags:
#   -WorkspaceDir "D:\MyWork"   custom folder (default: %USERPROFILE%\ProtocolCity)
#   -SkipServe                  install + setup only (do not start the suite)
#   -SkipInstall                assume packages already installed

param(
    [string]$WorkspaceDir = "",
    [switch]$SkipServe,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$MinMajor = 3
$MinMinor = 11
$Url = "http://127.0.0.1:8801/"

function Write-Step([string]$msg) {
    Write-Host ""
    Write-Host "── $msg ──" -ForegroundColor Cyan
}

function Write-Fail([string]$msg) {
    Write-Host ""
    Write-Host "ERROR: $msg" -ForegroundColor Red
}

function Get-Python {
    # Prefer the Windows py launcher, then bare python. Always use -m so we
    # never depend on Scripts\ being on PATH.
    $candidates = @(
        @{ Cmd = "py"; Args = @("-3.12") },
        @{ Cmd = "py"; Args = @("-3.11") },
        @{ Cmd = "py"; Args = @("-3") },
        @{ Cmd = "python"; Args = @() },
        @{ Cmd = "python3"; Args = @() }
    )
    foreach ($c in $candidates) {
        try {
            $code = @'
import sys
v = sys.version_info
print(sys.executable)
print("%d.%d" % (v.major, v.minor))
sys.exit(0 if (v.major, v.minor) >= (3, 11) else 2)
'@
            $out = & $c.Cmd @($c.Args + @("-c", $code)) 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) {
                $lines = @($out | ForEach-Object { "$_".Trim() } | Where-Object { $_ })
                if ($lines.Count -ge 2) {
                    return @{
                        Exe     = $lines[0]
                        Version = $lines[1]
                        Launcher = $c.Cmd
                        Prefix  = $c.Args
                    }
                }
            }
        } catch {
            continue
        }
    }
    return $null
}

function Invoke-Py([string[]]$PyArgs) {
    & $script:Py.Exe @PyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed ($LASTEXITCODE): $($PyArgs -join ' ')"
    }
}

Write-Host ""
Write-Host "BluePrint — Windows install" -ForegroundColor Green
Write-Host "Installs the suite, creates a workspace, opens the map."
Write-Host ""

# ── 1. Python ──────────────────────────────────────────────────────────────
Write-Step "Looking for Python 3.11+"
$script:Py = Get-Python
if (-not $script:Py) {
    Write-Fail "Python 3.11 or newer was not found."
    Write-Host ""
    Write-Host "Do this once, then run this script again:" -ForegroundColor Yellow
    Write-Host "  1. Open: https://www.python.org/downloads/windows/"
    Write-Host "  2. Download Python 3.12 (or 3.11+)"
    Write-Host "  3. Run the installer"
    Write-Host "  4. CHECK the box:  Add python.exe to PATH"
    Write-Host "  5. Click Install Now"
    Write-Host "  6. Close this window, open a NEW PowerShell, run the script again"
    Write-Host ""
    Write-Host "Optional (Windows 11 with winget):"
    Write-Host "  winget install Python.Python.3.12 --accept-package-agreements"
    Write-Host "  (then close PowerShell and open a new one)"
    exit 1
}
Write-Host "Using Python $($script:Py.Version) at $($script:Py.Exe)"

if (-not $WorkspaceDir) {
    $WorkspaceDir = Join-Path $env:USERPROFILE "ProtocolCity"
}

# ── 2. Packages ────────────────────────────────────────────────────────────
if (-not $SkipInstall) {
    Write-Step "Installing BluePrint + engines (PyPI)"
    Invoke-Py @("-m", "pip", "install", "--upgrade", "pip")
    # Quote extras for PowerShell; engines pulls WorkLane + WorkForce.
    # Single-quoted so PowerShell does not treat [engines] as a wildcard.
    Invoke-Py @("-m", "pip", "install", "--upgrade", 'protocolcity[engines]')
    Write-Host "Packages installed."
} else {
    Write-Step "Skipping pip install (-SkipInstall)"
}

# ── 3. Workspace ───────────────────────────────────────────────────────────
Write-Step "Creating workspace at $WorkspaceDir"
Invoke-Py @(
    "-m", "protocolcity", "setup", $WorkspaceDir,
    "--create", "--yes"
)
Write-Host "Workspace ready."

# ── 4. Serve ───────────────────────────────────────────────────────────────
if ($SkipServe) {
    Write-Host ""
    Write-Host "Install done. Start the suite with:" -ForegroundColor Green
    Write-Host "  $($script:Py.Exe) -m protocolcity serve --root `"$WorkspaceDir`""
    Write-Host "Then open: $Url"
    exit 0
}

Write-Step "Starting the suite"
Write-Host "When you see the server running, open your browser:"
Write-Host "  $Url" -ForegroundColor Green
Write-Host ""
Write-Host "Leave this window open while you use BluePrint."
Write-Host "Stop later with Ctrl+C."
Write-Host ""
Write-Host "If Windows Firewall asks, allow access on private networks."
Write-Host ""

# Blocking — engines default on when --root is set.
& $script:Py.Exe @("-m", "protocolcity", "serve", "--root", $WorkspaceDir)
exit $LASTEXITCODE
