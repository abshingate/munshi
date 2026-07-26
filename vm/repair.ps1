# TallyCloud repair - idempotent installer for every software component.
# Runs at first boot, at every boot (scheduled task), and on demand via the
# desktop "Repair This Computer" button or scripts/repair.sh (SSM).
# Present components are left untouched; missing ones are (re)installed with
# retries and fallback URLs. Log: C:\HealthCheck\repair-log.txt
Start-Transcript -Path "C:\HealthCheck\repair-log.txt" -Append
$ErrorActionPreference = "Continue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
New-Item -ItemType Directory -Force -Path "C:\Installers" | Out-Null
$script:fails = 0
function Report($state, $name) {
    if ($state -eq "FAILED") { $script:fails++ }
    Write-Output ("{0,-6} {1}" -f $state, $name)
}
function Get-File($urls, $out, $minBytes) {
    foreach ($u in $urls) {
        foreach ($try in 1..2) {
            try {
                Invoke-WebRequest -Uri $u -OutFile $out -UseBasicParsing -TimeoutSec 300
                if ((Get-Item $out -ErrorAction SilentlyContinue).Length -ge $minBytes) { return $true }
            } catch { Write-Output "  download failed ($u, try ${try}): $($_.Exception.Message)" }
        }
    }
    return $false
}

# --- Chocolatey (package manager everything else rides on) -------------------
$choco = "C:\ProgramData\chocolatey\bin\choco.exe"
if (-not (Test-Path $choco)) {
    try {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    } catch { Write-Output "  choco bootstrap failed: $($_.Exception.Message)" }
}
if (Test-Path $choco) { Report "OK" "Chocolatey" } else { Report "FAILED" "Chocolatey (everything below may also fail)" }

# --- Desktop software (checked by real file, not package metadata) -----------
# Each package lists every install location seen across vendor versions —
# present at ANY of them counts as installed.
$apps = [ordered]@{
    "googlechrome"    = @("C:\Program Files\Google\Chrome\Application\chrome.exe")
    "7zip"            = @("C:\Program Files\7-Zip\7z.exe")
    "adobereader"     = @("C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
                          "C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe")
    "notepadplusplus" = @("C:\Program Files\Notepad++\notepad++.exe")
    "git"             = @("C:\Program Files\Git\cmd\git.exe")
    "nodejs-lts"      = @("C:\Program Files\nodejs\node.exe")
}
function Test-AnyPath($paths) { @($paths | Where-Object { Test-Path $_ }).Count -gt 0 }
foreach ($pkg in $apps.Keys) {
    if (Test-AnyPath $apps[$pkg]) { Report "OK" $pkg; continue }
    & $choco install -y $pkg *> $null
    if (-not (Test-AnyPath $apps[$pkg])) { & $choco install -y $pkg --ignore-checksums *> $null }
    if (Test-AnyPath $apps[$pkg]) { Report "FIXED" $pkg } else { Report "FAILED" $pkg }
}

# --- Java 8, 32-bit AND 64-bit (GST emSigner / TRACES WebSigner) -------------
if ((Test-Path "C:\Program Files\Java") -and (Test-Path "C:\Program Files (x86)\Java")) {
    Report "OK" "Java 8 (32+64-bit)"
} else {
    & $choco install -y jre8 *> $null
    if ((Test-Path "C:\Program Files\Java") -and (Test-Path "C:\Program Files (x86)\Java")) {
        Report "FIXED" "Java 8 (32+64-bit)"
    } else { Report "FAILED" "Java 8 (32+64-bit)" }
}

# --- Claude Code (verified by executing it, not by file presence) ------------
$claudeCmd = "C:\Program Files\nodejs\claude.cmd"
$claudeOk = $false
try { $claudeOk = (& $claudeCmd --version 2>$null) -match "Claude" } catch {}
if ($claudeOk) { Report "OK" "Claude Code" }
elseif (Test-Path "C:\Program Files\nodejs\npm.cmd") {
    foreach ($try in 1..2) {
        & "C:\Program Files\nodejs\npm.cmd" install -g --force --prefix "C:\Program Files\nodejs" "@anthropic-ai/claude-code" *> $null
        try { if ((& $claudeCmd --version 2>$null) -match "Claude") { $claudeOk = $true; break } } catch {}
    }
    if ($claudeOk) { Report "FIXED" "Claude Code" } else { Report "FAILED" "Claude Code" }
} else { Report "FAILED" "Claude Code (Node.js missing)" }

# --- Amazon DCV (browser desktop) --------------------------------------------
if (Get-Service dcvserver -ErrorAction SilentlyContinue) { Report "OK" "Amazon DCV" }
else {
    $msi = "C:\Installers\dcv-server.msi"
    $ok = Get-File @(
        "https://d1uj6qtbmh3dt5.cloudfront.net/nice-dcv-server-x64-Release.msi"
    ) $msi 30MB
    if ($ok) {
        Start-Process msiexec.exe -Wait -ArgumentList "/i `"$msi`" ADDLOCAL=ALL /quiet /norestart AUTOMATIC_SESSION_OWNER=Administrator"
    }
    if (Get-Service dcvserver -ErrorAction SilentlyContinue) { Report "FIXED" "Amazon DCV" }
    else { Report "FAILED" "Amazon DCV (RDP and Fleet Manager still work)" }
}

# --- TallyPrime installer -----------------------------------------------------
# URL is discovered live from Tally's own site JS (newest release wins), with
# last-known-good mirrors as fallback. Skipped once Tally is installed.
if (Test-Path "C:\Program Files\TallyPrime\tally.exe") { Report "OK" "TallyPrime (installed)" }
elseif (Test-Path "C:\Installers\TallyPrimeSetup.exe") { Report "OK" "TallyPrime installer (staged)" }
else {
    $urls = @()
    foreach ($js in @("https://tallysolutions.com/utility/js/DownloadUtility-india.js",
                      "https://tallysolutions.com/utility/js/DownloadUtility.js")) {
        try {
            $body = (Invoke-WebRequest -Uri $js -UseBasicParsing -TimeoutSec 60).Content -replace '\\/', '/'
            $urls += [regex]::Matches($body, 'https://tallymirror\.tallysolutions\.com/download_centre/Rel[._]?[0-9]+\.[0-9]+/TP/Full/setup\.exe') |
                ForEach-Object { $_.Value }
        } catch { Write-Output "  Tally JS fetch failed ($js)" }
    }
    $urls = @($urls | Sort-Object -Unique -Descending -Property `
        @{Expression = { [version]($_ -replace '.*Rel[._]?([0-9]+\.[0-9]+).*', '$1') }})
    $urls += @("https://tallymirror.tallysolutions.com/download_centre/Rel7.1/TP/Full/setup.exe",
               "https://tallymirror.tallysolutions.com/download_centre/Rel6.2/TP/Full/setup.exe")
    if (Get-File $urls "C:\Installers\TallyPrimeSetup.exe" 10MB) {
        Report "FIXED" "TallyPrime installer"
    } else { Report "FAILED" "TallyPrime installer (use the Download TallyPrime desktop shortcut)" }
}

# --- VirtualHere client (DSC token over USB-over-IP) --------------------------
$vh = "C:\Users\Public\Desktop\DSC Setup\VirtualHere Client.exe"
if (Test-Path $vh) { Report "OK" "VirtualHere client" }
elseif (Get-File @("https://www.virtualhere.com/sites/default/files/usbclient/vhui64.exe") $vh 500KB) {
    Report "FIXED" "VirtualHere client"
} else { Report "FAILED" "VirtualHere client (download from virtualhere.com when needed)" }

Write-Output ""
if ($script:fails -gt 0) {
    Write-Output "REPAIR RESULT: $($script:fails) component(s) still broken - will retry at next boot, or double-click Repair This Computer after checking the internet connection."
} else {
    Write-Output "REPAIR RESULT: ALL COMPONENTS OK"
}
Stop-Transcript
exit $script:fails
