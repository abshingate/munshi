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
# VirtualHere client: lets a DSC token plugged into the user's local computer
# appear on this machine (pair with the free single-device server locally).
try {
    Invoke-WebRequest -Uri "https://www.virtualhere.com/sites/default/files/usbclient/vhui64.exe" `
        -OutFile "$dsc\VirtualHere Client.exe" -UseBasicParsing
} catch { Write-Output "VirtualHere client download failed: $_" }

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
WELCOME! READ THIS FIRST (5 minutes)
====================================

This is your accounting computer. Everything you need is already here.
Nothing you save is ever lost - even when the computer is switched off,
and a backup copy is taken automatically every night at 2 AM.

DOING THIS FOR THE FIRST TIME? Just 2 steps:

  STEP 1: A Tally installation window opens by itself.
          Click Install and keep clicking Next.
          One important thing: when it asks where to keep DATA,
          choose:  C:\TallyData

  STEP 2: Open Tally (icon on this desktop) and enter your
          Tally serial number and Tally.net login to activate it.

That's it. You are ready.

WHERE IS EVERYTHING?
  - Tally            : icon on this desktop
  - Government sites : "Govt Portals" folder on this desktop
                       (GST, Income Tax, TDS, PF, ESIC, MCA - just double-click)
  - Chrome browser   : on this desktop
  - Your data        : always keep it in C:\TallyData

IS SOMETHING NOT WORKING?
  Double-click "Check System Health" on this desktop. Every line will say
  PASS (good) or FAIL (problem + how to fix). Show the result to whoever
  manages this computer for you.

SIGNING WITH YOUR DSC (the USB token):
  The token stays plugged into YOUR computer at home - it reaches this
  computer over the internet:
  - From a Windows laptop: connect with the Remote Desktop app and switch on
    "Local Resources -> Smart cards" in its settings before connecting.
  - From a Mac: use the VirtualHere program (it is in the "DSC Setup"
    folder here; the server part goes on your Mac - one-time setup).
  - No DSC needed for many filings: GST and Income-tax accept an OTP on
    your Aadhaar-linked mobile (proprietorship/partnership only).
  First time only: install your token's driver from the "DSC Setup" folder
  (pick the link matching your token brand: ePass2003 / ProxKey / mToken).

FIRST TIME ON EACH GOVERNMENT SITE (one double-click each, only when needed):
  - GST with DSC : log in to GST -> Register/Update DSC -> download emSigner
  - TDS (TRACES) : Downloads -> TRACES WebSigner
  - MCA          : "MCA emBridge signer" link in the "DSC Setup" folder
  (These sites only give their signing tool AFTER you log in with your own
   account - that is why they could not be pre-installed for you.)

EXTRA: "Claude Code" on this desktop is an AI assistant that can help you
right on this computer - double-click it and sign in once.

Don't worry about switching off - this computer turns itself off when you
stop using it, and everything will be exactly here when you come back.
"@ | Out-File "$desktop\READ-ME-FIRST.txt" -Encoding ascii

"Bootstrap finished $(Get-Date -Format o)" | Out-File "C:\bootstrap-complete.txt" -Encoding ascii
Stop-Transcript
</powershell>
<persist>false</persist>
