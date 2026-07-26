# Renders the info wallpaper and applies it for the current user.
# Compact panel anchored TOP-RIGHT (desktop icons stack on the left), rendered
# at the screen's actual resolution so it always fits — DCV resizes the display
# to the browser window, so this varies. -RenderOnly regenerates the image
# without applying (used at boot by SYSTEM; user logons apply it).
param([switch]$RenderOnly)
$ErrorActionPreference = "SilentlyContinue"
Add-Type -AssemblyName System.Drawing

function Get-FileVer($path) {
    if (Test-Path $path) { (Get-Item $path).VersionInfo.ProductVersion } else { $null }
}

$tallyVer = Get-FileVer "C:\Program Files\TallyPrime\tally.exe"
$tally = if ($tallyVer) { "installed ($tallyVer)" } else { "not installed - opens at login" }
$chrome = Get-FileVer "C:\Program Files\Google\Chrome\Application\chrome.exe"; if (-not $chrome) { $chrome = "-" }
$claude = & "C:\Program Files\nodejs\claude.cmd" --version 2>$null
$claude = if ($claude) { ($claude -replace '\s*\(Claude Code\)', '') } else { "-" }
$java = "-"; if (Test-Path "C:\Program Files\Java") { $java = ((Get-ChildItem "C:\Program Files\Java" | Select-Object -First 1).Name -replace 'jre', '') }
$dcvSvc = Get-Service dcvserver -ErrorAction SilentlyContinue
$dcv = if ($dcvSvc -and $dcvSvc.Status -eq "Running") { "running" } else { "NOT RUNNING" }

$sections = @(
    @{ h = "WHERE THINGS ARE"; rows = @(
        @("Tally data", "C:\TallyData"),
        @("Installers", "C:\Installers"),
        @("Logs / reports", "C:\HealthCheck")) },
    @{ h = "SOFTWARE"; rows = @(
        @("TallyPrime", $tally),
        @("Java 8 (32+64)", $java),
        @("Chrome", $chrome),
        @("Claude Code", $claude),
        @("DCV desktop", $dcv)) },
    @{ h = "SOMETHING WRONG?"; rows = @(
        @("1.", "Check System Health  (desktop)"),
        @("2.", "Repair This Computer (desktop)"),
        @("3.", "Help and User Guide  (desktop)")) },
    @{ h = "GOOD TO KNOW"; rows = @(
        @("-", "Auto-OFF after ~1 hour idle"),
        @("-", "Nightly 2 AM backup, nothing lost"),
        @("-", "Portals: 'Govt Portals' folder")) }
)

# Use the real display size when running in a user session; sane default otherwise
$w = 1920; $h = 1080
try {
    Add-Type -AssemblyName System.Windows.Forms
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    if ($b.Width -ge 800 -and $b.Height -ge 600) { $w = $b.Width; $h = $b.Height }
} catch {}

$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

$g.FillRectangle((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 20, 30, 46))), 0, 0, $w, $h)

# Compact top-right panel
$pw = 640; $px = $w - $pw - 36; $py = 42
$titleFont = New-Object System.Drawing.Font("Segoe UI", 19, [System.Drawing.FontStyle]::Bold)
$headFont  = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
$labelFont = New-Object System.Drawing.Font("Segoe UI", 11)
$valueFont = New-Object System.Drawing.Font("Consolas", 11, [System.Drawing.FontStyle]::Bold)
$smallFont = New-Object System.Drawing.Font("Segoe UI", 9)
$rowH = 25; $headH = 30; $divH = 14

# Panel height computed from content so nothing is ever cut off
$ph = 58 + 26
foreach ($s in $sections) { $ph += $headH + ($s.rows.Count * $rowH) + $divH }

$panel = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 30, 44, 66))
$gold  = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 240, 178, 50))
$white = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 236, 241, 248))
$grey  = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 160, 175, 198))
$line  = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 55, 72, 98))
$g.FillRectangle($panel, $px, $py, $pw, $ph)
$g.FillRectangle($gold, $px, $py, 6, $ph)

$x = $px + 28; $y = $py + 18
$g.DrawString("TALLY CLOUD WORKSTATION", $titleFont, $gold, $x - 4, $y)
$y += 52

foreach ($s in $sections) {
    $g.DrawString($s.h, $headFont, $gold, $x - 2, $y)
    $y += $headH
    foreach ($row in $s.rows) {
        $g.DrawString($row[0], $labelFont, $grey, $x, $y)
        $g.DrawString($row[1], $valueFont, $white, $x + 150, $y)
        $y += $rowH
    }
    $g.FillRectangle($line, $x - 2, $y + 3, $pw - 56, 1)
    $y += $divH
}
$g.DrawString("Updated $(Get-Date -Format 'dd-MMM HH:mm') - refreshes at login", $smallFont, $grey, $x - 2, $y - 4)

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
