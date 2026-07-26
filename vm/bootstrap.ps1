# One-time machine setup (idempotent - safe to re-run any time).
# Software installation lives in repair.ps1; this wires up the desktop,
# scheduled tasks, help page, wallpaper and read-me.
$ErrorActionPreference = "Continue"
$desktop = "C:\Users\Public\Desktop"
$vm = "C:\HealthCheck\vm"
New-Item -ItemType Directory -Force -Path "C:\Installers", "C:\TallyData", "C:\HealthCheck" | Out-Null

Set-TimeZone -Id "India Standard Time"

function New-UrlShortcut($Path, $Url) {
    "[InternetShortcut]`r`nURL=$Url" | Out-File $Path -Encoding ascii
}

# --- Self-update + self-heal: sync scripts from the account's S3 bucket, then
# --- repair; registered to run at every boot ---------------------------------
@'
try {
    $b = Get-Content "C:\HealthCheck\bucket.txt" -ErrorAction Stop
    Read-S3Object -BucketName $b -KeyPrefix "vm" -Folder "C:\HealthCheck\vm" | Out-Null
} catch { Write-Output "S3 sync skipped: $($_.Exception.Message)" }
& powershell -ExecutionPolicy Bypass -File "C:\HealthCheck\vm\repair.ps1"
'@ | Out-File "C:\HealthCheck\update-and-repair.ps1" -Encoding ascii

schtasks /Create /TN "TallyCloudRepair" /SC ONSTART /RU SYSTEM /RL HIGHEST /F `
    /TR "powershell -ExecutionPolicy Bypass -File C:\HealthCheck\update-and-repair.ps1" | Out-Null

# --- Desktop buttons and shortcuts -------------------------------------------
@"
@echo off
echo Checking and repairing this computer's software - please wait, this can
echo take several minutes. Every line will say OK, FIXED or FAILED.
echo.
powershell -ExecutionPolicy Bypass -File C:\HealthCheck\update-and-repair.ps1
pause
"@ | Out-File "$desktop\Repair This Computer.cmd" -Encoding ascii

@"
@echo off
powershell -ExecutionPolicy Bypass -File C:\HealthCheck\vm\health-check.ps1
pause
"@ | Out-File "$desktop\Check System Health.cmd" -Encoding ascii

@"
@echo off
powershell -NoExit -Command "claude"
"@ | Out-File "$desktop\Claude Code.cmd" -Encoding ascii

New-UrlShortcut "$desktop\Help and User Guide.url" "file:///C:/HealthCheck/vm/help.html"
New-UrlShortcut "$desktop\AI Accountant.url"       "https://localhost:8444"
New-UrlShortcut "$desktop\Download TallyPrime.url" "https://tallysolutions.com/download/"

$portals = "$desktop\Govt Portals"
New-Item -ItemType Directory -Force -Path $portals | Out-Null
New-UrlShortcut "$portals\GST Portal.url"        "https://www.gst.gov.in/"
New-UrlShortcut "$portals\Income Tax Portal.url" "https://www.incometax.gov.in/"
New-UrlShortcut "$portals\TRACES (TDS).url"      "https://www.tdscpc.gov.in/"
New-UrlShortcut "$portals\EPFO Employer.url"     "https://unifiedportal-emp.epfindia.gov.in/"
New-UrlShortcut "$portals\ESIC.url"              "https://www.esic.gov.in/"
New-UrlShortcut "$portals\MCA.url"               "https://www.mca.gov.in/"

$dsc = "$desktop\DSC Setup"
New-Item -ItemType Directory -Force -Path $dsc | Out-Null
New-UrlShortcut "$dsc\GST emSigner (login, then Register-Update DSC).url" "https://www.gst.gov.in/"
New-UrlShortcut "$dsc\MCA emBridge signer.url"                            "https://embridge.emudhra.com/"
New-UrlShortcut "$dsc\ePass2003 token driver.url"                         "https://www.epass2003.com/"
New-UrlShortcut "$dsc\WD ProxKey token driver.url"                        "https://www.wdproxkey.com/"
New-UrlShortcut "$dsc\Capricorn-mToken drivers (repository).url"          "https://www.certificate.digital/repository/"

Copy-Item "$vm\READ-ME-FIRST.txt" "$desktop\READ-ME-FIRST.txt" -Force

# --- Wallpaper: regenerate + apply at every user logon -----------------------
$startup = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
@"
@echo off
powershell -ExecutionPolicy Bypass -File C:\HealthCheck\vm\wallpaper.ps1 >nul 2>&1
"@ | Out-File "$startup\SetInfoWallpaper.cmd" -Encoding ascii

# --- First-login auto-setup: Tally wizard opens by itself --------------------
@"
@echo off
if exist "C:\Program Files\TallyPrime\tally.exe" (del "%~f0" & exit /b)
start "" notepad "C:\Users\Public\Desktop\READ-ME-FIRST.txt"
if exist "C:\Installers\TallyPrimeSetup.exe" start "" "C:\Installers\TallyPrimeSetup.exe"
"@ | Out-File "$startup\FirstTimeSetup.cmd" -Encoding ascii

# --- Install everything, pre-render the wallpaper image ----------------------
& powershell -ExecutionPolicy Bypass -File "$vm\repair.ps1"
& powershell -ExecutionPolicy Bypass -File "$vm\wallpaper.ps1" -RenderOnly

"Bootstrap finished $(Get-Date -Format o)" | Out-File "C:\bootstrap-complete.txt" -Encoding ascii
