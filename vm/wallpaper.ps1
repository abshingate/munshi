# Renders the info wallpaper and applies it for the current user.
# Layout: a readable panel on the RIGHT side of the screen — desktop icons
# stack on the left, so the two never overlap. -RenderOnly regenerates the
# image without applying (used at boot by SYSTEM; user logons apply it).
param([switch]$RenderOnly)
$ErrorActionPreference = "SilentlyContinue"
Add-Type -AssemblyName System.Drawing

function Get-FileVer($path) {
    if (Test-Path $path) { (Get-Item $path).VersionInfo.ProductVersion } else { $null }
}

$tallyVer = Get-FileVer "C:\Program Files\TallyPrime\tally.exe"
$tally = if ($tallyVer) { "installed  ($tallyVer)" } else { "not installed yet - opens at login" }
$chrome = Get-FileVer "C:\Program Files\Google\Chrome\Application\chrome.exe"; if (-not $chrome) { $chrome = "-" }
$claude = & "C:\Program Files\nodejs\claude.cmd" --version 2>$null
$claude = if ($claude) { ($claude -replace '\s*\(Claude Code\)', '') } else { "-" }
$java = "-"; if (Test-Path "C:\Program Files\Java") { $java = ((Get-ChildItem "C:\Program Files\Java" | Select-Object -First 1).Name -replace 'jre', '') }
$dcvSvc = Get-Service dcvserver -ErrorAction SilentlyContinue
$dcv = if ($dcvSvc -and $dcvSvc.Status -eq "Running") { "running" } else { "NOT RUNNING" }

# (heading, rows) sections; rows are (label, value) pairs
$sections = @(
    @{ h = "WHERE THINGS ARE"; rows = @(
        @("Tally data - keep everything in", "C:\TallyData"),
        @("Installers", "C:\Installers"),
        @("Logs and reports", "C:\HealthCheck")) },
    @{ h = "SOFTWARE"; rows = @(
        @("TallyPrime", $tally),
        @("Java 8 (32+64-bit)", $java),
        @("Chrome", $chrome),
        @("Claude Code", $claude),
        @("Browser desktop (DCV)", $dcv)) },
    @{ h = "SOMETHING WRONG?  DO THIS, IN ORDER"; rows = @(
        @("1.", "Double-click  Check System Health"),
        @("2.", "Double-click  Repair This Computer"),
        @("3.", "Open  Help and User Guide")) },
    @{ h = "GOOD TO KNOW"; rows = @(
        @("*", "Switches itself OFF after ~1 hour idle"),
        @("*", "Full backup every night at 2 AM - nothing is ever lost"),
        @("*", "Govt portals: 'Govt Portals' folder on this desktop")) }
)

$w = 1920; $h = 1080
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

# Background: deep navy, plain (keeps desktop icons on the left legible)
$g.FillRectangle((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 20, 30, 46))), 0, 0, $w, $h)

# Right-side panel
$px = 850; $pw = 990; $py = 90; $ph = 880
$panel = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 30, 44, 66))
$g.FillRectangle($panel, $px, $py, $pw, $ph)
$gold = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 240, 178, 50))
$g.FillRectangle($gold, $px, $py, 8, $ph)

$titleFont = New-Object System.Drawing.Font("Segoe UI", 30, [System.Drawing.FontStyle]::Bold)
$headFont  = New-Object System.Drawing.Font("Segoe UI", 17, [System.Drawing.FontStyle]::Bold)
$labelFont = New-Object System.Drawing.Font("Segoe UI", 16)
$valueFont = New-Object System.Drawing.Font("Consolas", 16, [System.Drawing.FontStyle]::Bold)
$smallFont = New-Object System.Drawing.Font("Segoe UI", 12)
$white = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 236, 241, 248))
$grey  = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 160, 175, 198))
$line  = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 55, 72, 98))

$x = $px + 42; $y = $py + 30
$g.DrawString("TALLY CLOUD WORKSTATION", $titleFont, $gold, $x - 6, $y)
$y += 74

foreach ($s in $sections) {
    $g.DrawString($s.h, $headFont, $gold, $x - 4, $y)
    $y += 40
    foreach ($row in $s.rows) {
        $g.DrawString($row[0], $labelFont, $grey, $x, $y)
        $g.DrawString($row[1], $valueFont, $white, $x + 330, $y)
        $y += 34
    }
    $y += 10
    $g.FillRectangle($line, $x - 4, $y, $pw - 80, 2)
    $y += 20
}

$g.DrawString("Updated $(Get-Date -Format 'dd-MMM-yyyy HH:mm') IST  -  refreshes at every login", $smallFont, $grey, $x - 4, $py + $ph - 40)

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
