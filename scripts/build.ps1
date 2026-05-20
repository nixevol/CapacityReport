param(
    [ValidateSet("server", "desktop", "docker", "all")]
    [string]$Target = "all",

    [ValidateSet("current", "windows", "linux", "macos")]
    [string]$Platform = "current",

    [switch]$SkipDockerBuild,
    [switch]$SkipDesktopBuild,
    [switch]$NoArchive,
    [switch]$Clean,
    [Alias("h", "?")]
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$DistDir = Join-Path $Root "dist"
$ServerDistDir = Join-Path $DistDir "server"
$DesktopDistDir = Join-Path $DistDir "desktop"
$DockerDistDir = Join-Path $DistDir "docker"
$TempDir = Join-Path $DistDir ".tmp"
$PyInstallerDir = Join-Path $TempDir "pyinstaller"
$FrontendDir = Join-Path $Root "frontend"
$PackagingDir = Join-Path $Root "packaging"
$ServerName = "capareport-server"
$DesktopApiBase = "http://127.0.0.1:19082"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Green
}

function Write-Info($Message) {
    Write-Host "    $Message"
}

function Show-Usage {
    Write-Host "Usage: scripts\build.bat [server|desktop|docker|all] [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Platform current|windows|linux|macos"
    Write-Host "  -NoArchive"
    Write-Host "  -Clean"
    Write-Host "  -SkipDockerBuild"
    Write-Host "  -SkipDesktopBuild"
}

function Assert-InWorkspace($Path) {
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if (!$resolved.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside workspace: $resolved"
    }
    return $resolved
}

function Remove-Tree($Path) {
    if (Test-Path -LiteralPath $Path) {
        $resolved = Assert-InWorkspace $Path
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}

function Invoke-Checked($Command, $WorkingDirectory = $Root) {
    Write-Info $Command
    Push-Location $WorkingDirectory
    try {
        cmd /c $Command
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE`: $Command"
        }
    }
    finally {
        Pop-Location
    }
}

function Get-CurrentPlatform {
    if ($Platform -ne "current") {
        return $Platform
    }
    if ($env:OS -eq "Windows_NT") {
        return "windows"
    }
    $uname = (uname -s 2>$null)
    if ($uname -eq "Darwin") {
        return "macos"
    }
    return "linux"
}

function Get-ExecutableName($PlatformName) {
    if ($PlatformName -eq "windows") {
        return "$ServerName.exe"
    }
    return $ServerName
}

function Get-RustHostTriple {
    $output = rustc -vV
    foreach ($line in $output) {
        if ($line -like "host:*") {
            return $line.Substring(5).Trim()
        }
    }
    throw "Unable to detect Rust host triple"
}

function Test-TauriCli {
    cmd /c "cargo tauri --version >nul 2>nul"
    return $LASTEXITCODE -eq 0
}

function Ensure-PythonEnvironment {
    Write-Step "Preparing Python environment"
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (!(Test-Path $venvPython)) {
        Invoke-Checked "uv venv" $Root
    }
    Invoke-Checked "uv pip install -r requirements.txt" $Root
    Invoke-Checked "uv pip install pyinstaller" $Root
}

function Build-Frontend($ApiBase) {
    Write-Step "Building frontend"
    if (!(Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Invoke-Checked "npm ci" $FrontendDir
    }

    $previousApiBase = $env:VITE_API_BASE
    if ($ApiBase) {
        $env:VITE_API_BASE = $ApiBase
    }
    else {
        Remove-Item Env:\VITE_API_BASE -ErrorAction SilentlyContinue
    }

    try {
        Invoke-Checked "npm run build" $FrontendDir
    }
    finally {
        if ($null -ne $previousApiBase) {
            $env:VITE_API_BASE = $previousApiBase
        }
        else {
            Remove-Item Env:\VITE_API_BASE -ErrorAction SilentlyContinue
        }
    }
}

function Build-ServerBinary([switch]$OneFile) {
    Ensure-PythonEnvironment
    Write-Step "Building server binary"
    Remove-Tree $PyInstallerDir
    New-Item -ItemType Directory -Force -Path $PyInstallerDir | Out-Null

    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $workPath = Join-Path $PyInstallerDir "work"
    $distPath = Join-Path $PyInstallerDir "dist"
    $specPath = Join-Path $PackagingDir "capareport-server.spec"
    $previousOneFile = $env:CAPAREPORT_ONEFILE

    if ($OneFile) {
        $env:CAPAREPORT_ONEFILE = "1"
    }
    else {
        Remove-Item Env:\CAPAREPORT_ONEFILE -ErrorAction SilentlyContinue
    }

    try {
        Invoke-Checked "`"$python`" -m PyInstaller --clean --noconfirm --workpath `"$workPath`" --distpath `"$distPath`" `"$specPath`"" $Root
    }
    finally {
        if ($null -ne $previousOneFile) {
            $env:CAPAREPORT_ONEFILE = $previousOneFile
        }
        else {
            Remove-Item Env:\CAPAREPORT_ONEFILE -ErrorAction SilentlyContinue
        }
    }

    if ($OneFile) {
        $binaryDir = $distPath
        $binaryPath = Join-Path $binaryDir (Get-ExecutableName (Get-CurrentPlatform))
        if (!(Test-Path $binaryPath)) {
            throw "PyInstaller output not found: $binaryPath"
        }
    }
    else {
        $binaryDir = Join-Path $distPath $ServerName
        if (!(Test-Path $binaryDir)) {
            throw "PyInstaller output not found: $binaryDir"
        }
    }
    return $binaryDir
}

function Write-TextFile($Path, $Content, [switch]$Lf) {
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    if ($Lf) {
        [System.IO.File]::WriteAllText($Path, $Content.Replace("`r`n", "`n"), [System.Text.UTF8Encoding]::new($false))
    }
    else {
        [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
    }
}

function Copy-RuntimeFiles($OutputDir) {
    Copy-Item -Path (Join-Path $Root "Configure.json") -Destination (Join-Path $OutputDir "Configure.json") -Force
    Copy-Item -Path (Join-Path $Root "ReportScript.sql") -Destination (Join-Path $OutputDir "ReportScript.sql") -Force
    New-Item -ItemType Directory -Force -Path (Join-Path $OutputDir "cache") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $OutputDir "logs") | Out-Null

    $frontendDist = Join-Path $FrontendDir "dist"
    if (!(Test-Path $frontendDist)) {
        throw "Frontend dist not found: $frontendDist"
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $OutputDir "frontend") | Out-Null
    Copy-Item -Path $frontendDist -Destination (Join-Path $OutputDir "frontend") -Recurse -Force
}

function Write-ServerLaunchers($OutputDir, $PlatformName) {
    $exe = Get-ExecutableName $PlatformName
    $bat = @"
@echo off
setlocal
cd /d "%~dp0"
if not exist cache mkdir cache
if not exist logs mkdir logs
echo Starting CapacityReport server...
echo URL: http://localhost:9081
"%~dp0$exe" --host 0.0.0.0 --port 9081
pause
"@
    Write-TextFile (Join-Path $OutputDir "run.bat") $bat

    $sh = @'
#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p cache logs
chmod +x "./__SERVER_EXE__" 2>/dev/null || true
echo "Starting CapacityReport server..."
echo "URL: http://localhost:9081"
exec "./__SERVER_EXE__" --host 0.0.0.0 --port 9081
'@
    $sh = $sh.Replace("__SERVER_EXE__", $exe)
    Write-TextFile (Join-Path $OutputDir "start.sh") $sh -Lf
}

function Build-ServerPortable {
    $platformName = Get-CurrentPlatform
    if ($platformName -ne "windows" -and $env:OS -eq "Windows_NT") {
        Write-Host "Native $platformName portable packages must be built on $platformName." -ForegroundColor Yellow
        Write-Host "The Windows build will continue for the current host." -ForegroundColor Yellow
        $platformName = "windows"
    }

    $outputDir = Join-Path $ServerDistDir "CapacityReport-Server-$platformName-x64"
    $archive = "$outputDir.zip"
    Remove-Tree $outputDir
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue

    Build-Frontend $null
    $binaryDir = Build-ServerBinary

    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    Copy-Item -Path (Join-Path $binaryDir "*") -Destination $outputDir -Recurse -Force
    Copy-RuntimeFiles $outputDir
    Write-ServerLaunchers $outputDir $platformName

    if (!$NoArchive) {
        Compress-Archive -Path (Join-Path $outputDir "*") -DestinationPath $archive -Force
        Write-Info "Archive: $archive"
    }

    Write-Info "Server package: $outputDir"
}

function Copy-DockerBundle {
    Remove-Tree $DockerDistDir
    New-Item -ItemType Directory -Force -Path $DockerDistDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $DockerDistDir "cache") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $DockerDistDir "logs") | Out-Null
    Copy-Item -Path (Join-Path $PackagingDir "docker-compose.yml") -Destination (Join-Path $DockerDistDir "docker-compose.yml") -Force
    Copy-Item -Path (Join-Path $PackagingDir "mysql") -Destination (Join-Path $DockerDistDir "mysql") -Recurse -Force
    Copy-Item -Path (Join-Path $Root "Configure.json") -Destination (Join-Path $DockerDistDir "Configure.json") -Force
    Copy-Item -Path (Join-Path $Root "ReportScript.sql") -Destination (Join-Path $DockerDistDir "ReportScript.sql") -Force
}

function Build-DockerImage {
    Remove-Tree $DockerDistDir

    if ($SkipDockerBuild) {
        Write-Host "Docker image build skipped."
        Copy-DockerBundle
        Invoke-Checked "docker compose -f `"$DockerDistDir\docker-compose.yml`" config" $Root
        Write-Info "Docker package: $DockerDistDir"
        return
    }

    Write-Step "Building Docker image"
    Invoke-Checked "docker build --progress=plain -f `"$PackagingDir\Dockerfile`" -t capacity-report-app:latest ." $Root

    Write-Step "Packaging Docker output"
    Copy-DockerBundle
    Invoke-Checked "docker save -o `"$DockerDistDir\capacity-report-app-latest.tar`" capacity-report-app:latest" $Root
    Invoke-Checked "docker compose -f `"$DockerDistDir\docker-compose.yml`" config" $Root
    Write-Info "Docker package: $DockerDistDir"
}

function Build-DesktopPackage {
    if ($SkipDesktopBuild) {
        Write-Host "Desktop build skipped."
        return
    }

    if (!(Get-Command rustc -ErrorAction SilentlyContinue)) {
        throw "Rust is required for the Tauri desktop build"
    }

    Remove-Tree $DesktopDistDir

    Build-Frontend $DesktopApiBase
    $binaryDir = Build-ServerBinary -OneFile
    $platformName = Get-CurrentPlatform
    $exe = Get-ExecutableName $platformName
    $triple = Get-RustHostTriple
    $sidecarDir = Join-Path $Root "src-tauri\binaries"
    New-Item -ItemType Directory -Force -Path $sidecarDir | Out-Null
    $sidecarName = if ($platformName -eq "windows") { "$ServerName-$triple.exe" } else { "$ServerName-$triple" }
    Copy-Item -Path (Join-Path $binaryDir $exe) -Destination (Join-Path $sidecarDir $sidecarName) -Force

    if (!(Test-TauriCli)) {
        Write-Step "Installing Tauri CLI"
        Invoke-Checked "cargo install tauri-cli --locked" $Root
    }

    Remove-Tree (Join-Path $Root "src-tauri\target\release\bundle")
    Write-Step "Building Tauri desktop package"
    Invoke-Checked "cargo tauri build" (Join-Path $Root "src-tauri")

    New-Item -ItemType Directory -Force -Path $DesktopDistDir | Out-Null
    $bundleDir = Join-Path $Root "src-tauri\target\release\bundle"
    Get-ChildItem -Path $bundleDir -Recurse -File -Include "*.msi", "*.exe" |
        Copy-Item -Destination $DesktopDistDir -Force
    Write-Info "Desktop package: $DesktopDistDir"
}

function Clean-Intermediates {
    Write-Step "Cleaning intermediate output"
    Remove-Tree $TempDir
    Remove-Tree (Join-Path $Root "frontend\dist")
    Remove-Tree (Join-Path $Root "src-tauri\binaries")
    Remove-Tree (Join-Path $Root "src-tauri\target")
}

if ($Help) {
    Show-Usage
    exit 0
}

if ($Clean) {
    Write-Step "Cleaning dist output"
    Remove-Tree $DistDir
    Remove-Tree (Join-Path $Root "frontend\dist")
    Remove-Tree (Join-Path $Root "src-tauri\binaries")
    Remove-Tree (Join-Path $Root "src-tauri\target")
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

switch ($Target) {
    "server" { Build-ServerPortable }
    "docker" { Build-DockerImage }
    "desktop" { Build-DesktopPackage }
    "all" {
        Build-ServerPortable
        Build-DockerImage
        Build-DesktopPackage
    }
}

Clean-Intermediates

Write-Step "Build finished"
