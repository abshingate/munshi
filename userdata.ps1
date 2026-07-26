<powershell>
# Bootstrap script — runs once on first boot. Full log: C:\bootstrap-log.txt
Start-Transcript -Path "C:\bootstrap-log.txt" -Append
$ErrorActionPreference = "Continue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Set-TimeZone -Id "India Standard Time"

New-Item -ItemType Directory -Force -Path "C:\Installers"  | Out-Null
New-Item -ItemType Directory -Force -Path "C:\TallyData"   | Out-Null
New-Item -ItemType Directory -Force -Path "C:\HealthCheck" | Out-Null
$desktop = "C:\Users\Public\Desktop"

function New-UrlShortcut($Path, $Url) {
    "[InternetShortcut]`r`nURL=$Url" | Out-File $Path -Encoding ascii
}

# --- Chocolatey + everyday software -----------------------------------------
Set-ExecutionPolicy Bypass -Scope Process -Force
Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
$choco = "C:\ProgramData\chocolatey\bin\choco.exe"
& $choco install -y googlechrome 7zip adobereader notepadplusplus

# Java 8: GST emSigner needs Java 8; TRACES WebSigner needs the 32-bit JRE.
# The jre8 package installs both the x86 and x64 JRE by default.
& $choco install -y jre8

# --- Claude Code (plus its prerequisites: Git + Node.js LTS) -----------------
& $choco install -y git nodejs-lts
$npm = "C:\Program Files\nodejs\npm.cmd"
# --prefix drops claude.cmd next to node.exe, which is on every user's PATH
& $npm install -g --prefix "C:\Program Files\nodejs" "@anthropic-ai/claude-code"
@"
@echo off
powershell -NoExit -Command "claude"
"@ | Out-File "$desktop\Claude Code.cmd" -Encoding ascii

# --- Amazon DCV server (browser access on https://<ip>:8443, free on EC2) ---
$dcvMsi = "C:\Installers\dcv-server.msi"
try {
    Invoke-WebRequest -Uri "https://d1uj6qtbmh3dt5.cloudfront.net/nice-dcv-server-x64-Release.msi" -OutFile $dcvMsi
    Start-Process msiexec.exe -Wait -ArgumentList `
        "/i `"$dcvMsi`" ADDLOCAL=ALL /quiet /norestart /l*v C:\Installers\dcv-install.log AUTOMATIC_SESSION_OWNER=Administrator"
} catch {
    Write-Output "DCV install failed: $_  (RDP and Fleet Manager still work)"
}

# --- TallyPrime installer (no silent mode exists; auto-launched at first login)
$tallyExe = "C:\Installers\TallyPrimeSetup.exe"
# Primary URL is Tally's own mirror (found via their download page's JS);
# adjust the release segment (Rel7.1) when Tally ships a newer version.
foreach ($u in @("https://tallymirror.tallysolutions.com/download_centre/Rel7.1/TP/Full/setup.exe",
                 "https://tallymirror.tallysolutions.com/download_centre/Rel6.2/TP/Full/setup.exe")) {
    try {
        Invoke-WebRequest -Uri $u -OutFile $tallyExe -UseBasicParsing
        if ((Get-Item $tallyExe).Length -gt 10MB) { break }
    } catch { Write-Output "Tally download from $u failed: $_" }
}
New-UrlShortcut "$desktop\Download TallyPrime.url" "https://tallysolutions.com/download/"

# --- Compliance portal shortcuts on the desktop ------------------------------
$portals = "$desktop\Govt Portals"
New-Item -ItemType Directory -Force -Path $portals | Out-Null
New-UrlShortcut "$portals\GST Portal.url"        "https://www.gst.gov.in/"
New-UrlShortcut "$portals\Income Tax Portal.url" "https://www.incometax.gov.in/"
New-UrlShortcut "$portals\TRACES (TDS).url"      "https://www.tdscpc.gov.in/"
New-UrlShortcut "$portals\EPFO Employer.url"     "https://unifiedportal-emp.epfindia.gov.in/"
New-UrlShortcut "$portals\ESIC.url"              "https://www.esic.gov.in/"
New-UrlShortcut "$portals\MCA.url"               "https://www.mca.gov.in/"

# Signer utilities are only downloadable AFTER portal login — stage links.
$dsc = "$desktop\DSC Setup"
New-Item -ItemType Directory -Force -Path $dsc | Out-Null
New-UrlShortcut "$dsc\GST emSigner (login, then Register-Update DSC).url" "https://www.gst.gov.in/"
New-UrlShortcut "$dsc\MCA emBridge signer.url"                            "https://embridge.emudhra.com/"
New-UrlShortcut "$dsc\ePass2003 token driver.url"                         "https://www.epass2003.com/"
New-UrlShortcut "$dsc\WD ProxKey token driver.url"                        "https://www.wdproxkey.com/"
New-UrlShortcut "$dsc\Capricorn-mToken drivers (repository).url"          "https://www.certificate.digital/repository/"

# --- On-VM health check (also runnable remotely via SSM) ---------------------
@'
$r = @(); $script:fails = 0
function Check($name, [scriptblock]$test, $hint, [switch]$WarnOnly) {
    try { $ok = & $test } catch { $ok = $false }
    if ($ok) { $script:r += "PASS  $name" }
    elseif ($WarnOnly) { $script:r += "WARN  $name -> $hint" }
    else { $script:r += "FAIL  $name -> $hint"; $script:fails++ }
}
Check "Bootstrap completed"        { Test-Path "C:\bootstrap-complete.txt" } "still installing or failed - see C:\bootstrap-log.txt"
Check "Amazon DCV service running" { (Get-Service dcvserver -ErrorAction SilentlyContinue).Status -eq "Running" } "Restart-Service dcvserver; RDP/Fleet Manager still work"
Check "DCV listening on 8443"      { (Test-NetConnection localhost -Port 8443 -WarningAction SilentlyContinue).TcpTestSucceeded } "Restart-Service dcvserver"
Check "Chrome installed"           { Test-Path "C:\Program Files\Google\Chrome\Application\chrome.exe" } "choco install -y googlechrome"
Check "Java 64-bit installed"      { Test-Path "C:\Program Files\Java" } "choco install -y jre8 (needed by GST emSigner)"
Check "Java 32-bit installed"      { Test-Path "C:\Program Files (x86)\Java" } "choco install -y jre8 (needed by TRACES WebSigner)"
Check "Claude Code installed"      { Test-Path "C:\Program Files\nodejs\claude.cmd" } "npm install -g --prefix 'C:\Program Files\nodejs' @anthropic-ai/claude-code"
Check "Tally data folder exists"   { Test-Path "C:\TallyData" } "mkdir C:\TallyData"
Check "Disk free space > 15 GB"    { (Get-PSDrive C).Free -gt 15GB } "raise volume_size_gb in terraform and apply"
Check "Internet: GST portal"       { (Test-NetConnection www.gst.gov.in -Port 443 -WarningAction SilentlyContinue).TcpTestSucceeded } "check security group egress / AWS networking"
Check "Internet: Income-tax portal" { (Test-NetConnection www.incometax.gov.in -Port 443 -WarningAction SilentlyContinue).TcpTestSucceeded } "check security group egress / AWS networking"
Check "TallyPrime installed"       { Test-Path "C:\Program Files\TallyPrime\tally.exe" } "one-time step: run TallyPrimeSetup (auto-opens at first login)" -WarnOnly
$report = ($r | Out-String).Trim()
$report | Tee-Object "C:\HealthCheck\last-report.txt"
if ($script:fails -gt 0) { Write-Output "`nRESULT: $($script:fails) ISSUE(S) FOUND - see FAIL lines above" ; exit 1 }
else { Write-Output "`nRESULT: ALL CHECKS PASSED" ; exit 0 }
'@ | Out-File "C:\HealthCheck\health-check.ps1" -Encoding ascii

@"
@echo off
powershell -ExecutionPolicy Bypass -File C:\HealthCheck\health-check.ps1
pause
"@ | Out-File "$desktop\Check System Health.cmd" -Encoding ascii

# --- First-login auto-setup: Tally wizard opens by itself; user clicks Next --
$startup = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
@"
@echo off
if exist "C:\Program Files\TallyPrime\tally.exe" (del "%~f0" & exit /b)
start "" notepad "C:\Users\Public\Desktop\READ-ME-FIRST.txt"
if exist "C:\Installers\TallyPrimeSetup.exe" start "" "C:\Installers\TallyPrimeSetup.exe"
"@ | Out-File "$startup\FirstTimeSetup.cmd" -Encoding ascii

# --- First-login instructions on the desktop ---------------------------------
@"
WELCOME — READ ME FIRST
=======================

Almost everything is pre-installed. On this FIRST login only:

1. The TallyPrime installer opens by itself — click Install (keep defaults),
   then set the DATA folder to  C:\TallyData
   (If it did not open, double-click "Download TallyPrime" on the desktop.)
2. Open TallyPrime and activate your Tally license (serial + Tally.net login).
3. Optional: double-click "Claude Code" on the desktop and sign in to your
   Anthropic account — after that, Claude runs on this machine any time.

Any time you want to verify the machine: double-click "Check System Health" —
it prints PASS/FAIL for every component and how to fix anything broken.

Only when you first need each portal (they require YOUR portal login to
download their signer, so this cannot be pre-installed — one double-click):
- GST with DSC : log in to GST -> Register/Update DSC -> download emSigner.
- TRACES (TDS) : Downloads -> TRACES WebSigner. (32-bit Java is installed.)
- MCA (companies/LLP) : install emBridge from the "DSC Setup" folder link.
- Your DSC token's driver: run the matching link in "DSC Setup" once.

USING YOUR DSC (USB TOKEN) FROM HOME:
- Keep the token plugged into your LOCAL computer.
- From a Windows PC: Remote Desktop -> Local Resources -> enable Smart cards.
- From a Mac or browser: use VirtualHere (free for one device).
- Many filings need no DSC: GST/Income-tax accept Aadhaar-OTP (EVC)
  for proprietors and partnerships.

Already installed: Chrome, Adobe Reader, 7-Zip, Notepad++, Java 8 (32+64 bit),
Git, Node.js, Claude Code, Amazon DCV. Timezone is IST.
ALL data persists across stop/start and is snapshotted daily.
Keep every Tally company under C:\TallyData.
"@ | Out-File "$desktop\READ-ME-FIRST.txt" -Encoding ascii

"Bootstrap finished $(Get-Date -Format o)" | Out-File "C:\bootstrap-complete.txt" -Encoding ascii
Stop-Transcript
</powershell>
<persist>false</persist>
