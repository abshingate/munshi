# Renders a BGInfo-style desktop wallpaper with live system facts and applies
# it for the current user. -RenderOnly regenerates the image without applying
# (used at boot by SYSTEM; each user's logon startup applies it).
param([switch]$RenderOnly)
$ErrorActionPreference = "SilentlyContinue"
Add-Type -AssemblyName System.Drawing

function Get-FileVer($path) {
    if (Test-Path $path) { (Get-Item $path).VersionInfo.ProductVersion } else { $null }
}

$tallyVer = Get-FileVer "C:\Program Files\TallyPrime\tally.exe"
$tally = if ($tallyVer) { "installed ($tallyVer)" } else { "NOT installed - it auto-opens at login, or see READ-ME" }
$chrome = Get-FileVer "C:\Program Files\Google\Chrome\Application\chrome.exe"; if (-not $chrome) { $chrome = "-" }
$node = Get-FileVer "C:\Program Files\nodejs\node.exe"; if (-not $node) { $node = "-" }
$claude = & "C:\Program Files\nodejs\claude.cmd" --version 2>$null
if (-not $claude) { $claude = "-" }
$java64 = "-"; if (Test-Path "C:\Program Files\Java") { $java64 = (Get-ChildItem "C:\Program Files\Java" | Select-Object -First 1).Name }
$java32 = "-"; if (Test-Path "C:\Program Files (x86)\Java") { $java32 = (Get-ChildItem "C:\Program Files (x86)\Java" | Select-Object -First 1).Name }
$dcvSvc = Get-Service dcvserver -ErrorAction SilentlyContinue
$dcv = if ($dcvSvc) { "$($dcvSvc.Status)" } else { "not installed" }

$title = "TALLY  CLOUD  WORKSTATION"
$lines = @(
    "",
    "WHERE THINGS ARE",
    "   Your Tally data (keep everything here)   C:\TallyData",
    "   Staged installers                        C:\Installers",
    "   Logs / health reports                    C:\HealthCheck",
    "",
    "SOFTWARE ON THIS COMPUTER",
    "   TallyPrime    $tally",
    "   Java 8        64-bit: $java64    32-bit: $java32",
    "   Chrome        $chrome",
    "   Node.js       $node       Claude Code: $claude",
    "   Amazon DCV    $dcv  (browser desktop, port 8443)",
    "",
    "IF SOMETHING IS WRONG - IN THIS ORDER",
    "   1.  Double-click  'Check System Health'   - PASS / FAIL for everything",
    "   2.  Double-click  'Repair This Computer'  - reinstalls whatever is broken",
    "   3.  Open          'Help and User Guide'   - full manual + troubleshooting",
    "",
    "GOOD TO KNOW",
    "   This computer switches itself OFF after ~1 hour of no activity.",
    "   Nothing is ever lost - full backup is taken every night at 2 AM.",
    "   Government portals are in the 'Govt Portals' desktop folder.",
    "",
    "Updated: $(Get-Date -Format 'dd-MMM-yyyy HH:mm') IST"
)

$w = 1920; $h = 1080
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

$bg = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 24, 38, 58))
$g.FillRectangle($bg, 0, 0, $w, $h)
$accent = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 240, 178, 50))
$g.FillRectangle($accent, 0, 0, 14, $h)

$titleFont = New-Object System.Drawing.Font("Segoe UI", 42, [System.Drawing.FontStyle]::Bold)
$headFont  = New-Object System.Drawing.Font("Consolas", 21, [System.Drawing.FontStyle]::Bold)
$bodyFont  = New-Object System.Drawing.Font("Consolas", 21)
$white  = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 235, 240, 248))
$gold   = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 240, 178, 50))
$grey   = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 150, 165, 190))

$x = 120; $y = 70
$g.DrawString($title, $titleFont, $gold, $x, $y)
$y += 110
foreach ($line in $lines) {
    if ($line -match '^[A-Z][A-Z ]+[A-Z-]$' -or $line -match '^GOOD TO KNOW|^IF SOMETHING') {
        $g.DrawString($line, $headFont, $gold, $x, $y)
    } elseif ($line -like "Updated:*") {
        $g.DrawString($line, $bodyFont, $grey, $x, $y)
    } else {
        $g.DrawString($line, $bodyFont, $white, $x, $y)
    }
    $y += 34
}

$out = "C:\HealthCheck\wallpaper.bmp"
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Bmp)
$g.Dispose(); $bmp.Dispose()

if (-not $RenderOnly) {
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name Wallpaper -Value $out
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name WallpaperStyle -Value "10"
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name TileWallpaper -Value "0"
    Add-Type @"
using System.Runtime.InteropServices;
public class WP {
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
}
"@
    [WP]::SystemParametersInfo(20, 0, $out, 3) | Out-Null
}
