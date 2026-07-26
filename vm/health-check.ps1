# On-VM health check - runnable via the desktop button or remotely via SSM.
# Prints PASS / WARN / FAIL per component; exit code = number of FAILs.
$r = @(); $script:fails = 0
function Check($name, [scriptblock]$test, $hint, [switch]$WarnOnly) {
    try { $ok = & $test } catch { $ok = $false }
    if ($ok) { $script:r += "PASS  $name" }
    elseif ($WarnOnly) { $script:r += "WARN  $name -> $hint" }
    else { $script:r += "FAIL  $name -> $hint"; $script:fails++ }
}
$fix = "double-click Repair This Computer (or scripts/repair.sh from your computer)"
Check "Bootstrap completed"        { Test-Path "C:\bootstrap-complete.txt" } "still installing or failed - see C:\bootstrap-log.txt"
Check "Amazon DCV service running" { (Get-Service dcvserver -ErrorAction SilentlyContinue).Status -eq "Running" } "Restart-Service dcvserver, or $fix"
Check "DCV listening on 8443"      { (Test-NetConnection localhost -Port 8443 -WarningAction SilentlyContinue).TcpTestSucceeded } "Restart-Service dcvserver"
Check "Chrome installed"           { Test-Path "C:\Program Files\Google\Chrome\Application\chrome.exe" } $fix
Check "Google Drive sync (rclone)" { Test-Path "C:\ProgramData\chocolatey\bin\rclone.exe" } $fix
Check "Google Drive sync configured" { Test-Path "C:\ProgramData\rclone\rclone.conf" } "one-time: run 'Set up Google Drive' on the desktop" -WarnOnly
Check "Google Drive sync healthy"  {
    if (-not (Test-Path "C:\ProgramData\rclone\rclone.conf")) { $true }
    elseif (Test-Path "C:\TallyData\_DriveSyncStatus.txt") { -not (Select-String -Path "C:\TallyData\_DriveSyncStatus.txt" -Pattern "SYNC PROBLEM" -Quiet) }
    else { $true }
} "see C:\TallyData\_DriveSyncStatus.txt; re-run 'Set up Google Drive' if it persists" -WarnOnly
Check "Java 64-bit installed"      { Test-Path "C:\Program Files\Java" } $fix
Check "Java 32-bit installed"      { Test-Path "C:\Program Files (x86)\Java" } $fix
Check "Claude Code installed"      { (& "C:\Program Files\nodejs\claude.cmd" --version 2>$null) -match "Claude" } $fix
Check "Help page available"        { Test-Path "C:\HealthCheck\vm\help.html" } $fix
Check "AI Accountant app (8444)"   { (Test-NetConnection localhost -Port 8444 -WarningAction SilentlyContinue).TcpTestSucceeded } $fix
Check "Info wallpaper rendered"    { Test-Path "C:\HealthCheck\wallpaper.bmp" } "run C:\HealthCheck\vm\wallpaper.ps1"
Check "Self-repair task registered" { schtasks /Query /TN "TallyCloudRepair" 2>$null } "re-run C:\HealthCheck\vm\bootstrap.ps1"
Check "Tally data folder exists"   { Test-Path "C:\TallyData" } "mkdir C:\TallyData"
Check "Disk free space > 15 GB"    { (Get-PSDrive C).Free -gt 15GB } "raise volume_size_gb in terraform and apply"
Check "Internet: GST portal"       { (Test-NetConnection www.gst.gov.in -Port 443 -WarningAction SilentlyContinue).TcpTestSucceeded } "check security group egress / AWS networking"
Check "Internet: Income-tax portal" { (Test-NetConnection www.incometax.gov.in -Port 443 -WarningAction SilentlyContinue).TcpTestSucceeded } "check security group egress / AWS networking"
Check "TallyPrime installed"       { Test-Path "C:\Program Files\TallyPrime\tally.exe" } "one-time step: run TallyPrimeSetup (auto-opens at first login); Repair restages the installer if missing" -WarnOnly
$report = ($r | Out-String).Trim()
$report | Tee-Object "C:\HealthCheck\last-report.txt"
if ($script:fails -gt 0) { Write-Output "`nRESULT: $($script:fails) ISSUE(S) FOUND - see FAIL lines above" ; exit 1 }
else { Write-Output "`nRESULT: ALL CHECKS PASSED" ; exit 0 }
