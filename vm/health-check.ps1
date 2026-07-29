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
Check "Stable DNS name current"    {
    if (-not (Test-Path "C:\HealthCheck\vm\dns-config.json")) { $true }   # feature off
    else {
        $cfg = Get-Content "C:\HealthCheck\vm\dns-config.json" -Raw | ConvertFrom-Json
        $token = Invoke-RestMethod -Method PUT -Uri "http://169.254.169.254/latest/api/token" -Headers @{ "X-aws-ec2-metadata-token-ttl-seconds" = "60" } -TimeoutSec 5
        $ip = Invoke-RestMethod -Uri "http://169.254.169.254/latest/meta-data/public-ipv4" -Headers @{ "X-aws-ec2-metadata-token" = $token } -TimeoutSec 5
        (Resolve-DnsName -Name $cfg.hostname -Type A -Server 1.1.1.1 -ErrorAction Stop | Where-Object Type -eq "A").IPAddress -contains $ip
    }
} "run C:\HealthCheck\vm\update-dns.ps1 or 'Repair This Computer'; see C:\HealthCheck\dns-update.log" -WarnOnly
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

# --- Knowledge base (ADR-0020) ----------------------------------------------
# Optional component: absent is a WARN, broken-when-present is a FAIL. Tests
# behaviour (can we query?) rather than file presence, per ADR-0006.
$kbPg  = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue |
         Sort-Object { [int]($_.Directory.Parent.Name) } -Descending | Select-Object -First 1
$kbPwd = [Environment]::GetEnvironmentVariable("MUNSHI_KB_PASSWORD", "Machine")
function Invoke-Kb($sql) {
    if (-not $kbPg -or -not $kbPwd) { return $null }
    $env:PGPASSWORD = $kbPwd
    & $kbPg.FullName -U postgres -h 127.0.0.1 -d munshi_kb -tAc $sql 2>$null
}

Check "Knowledge base: PostgreSQL installed" { $null -ne $kbPg } "optional; run 'Repair This Computer' to install (ADR-0020)" -WarnOnly
Check "Knowledge base: database responds" {
    if (-not $kbPg) { $true }                      # not installed: covered by the WARN above
    else { (Invoke-Kb "SELECT 1") -match "1" }
} "PostgreSQL is installed but not answering: Start-Service postgresql*, then $fix"
Check "Knowledge base: schema present" {
    if (-not $kbPg) { $true }
    else { (Invoke-Kb "SELECT count(*) FROM kb_schema_version") -match "[1-9]" }
} "migrations have not run: $fix (see C:\HealthCheck\vm\kb\migrations)"
Check "Knowledge base: search works" {
    if (-not $kbPg) { $true }
    else {
        # End-to-end behaviour test: the full-text path must actually return.
        $null -ne (Invoke-Kb "SELECT count(*) FROM kb_document WHERE tsv @@ plainto_tsquery('english','tax')")
    }
} "full-text search failing; check the FTS triggers in migration 001"
Check "Knowledge base: has documents" {
    if (-not $kbPg) { $true }
    else { (Invoke-Kb "SELECT count(*) FROM kb_document") -match "[1-9]" }
} "empty index: run 'python C:\HealthCheck\vm\kb\ingest.py --source filesystem --path C:\TallyData\Documents'" -WarnOnly
Check "Knowledge base: semantic search" {
    if (-not $kbPg) { $true }
    else { (Invoke-Kb "SELECT count(*) FROM information_schema.columns WHERE table_name='kb_chunk' AND column_name='embedding'") -match "1" }
} "pgvector not installed - SQL and full-text search still work; see vm/kb/README.md to enable" -WarnOnly
Check "Rules engine: computes correctly" {
    $py = @(Get-Command python.exe -ErrorAction SilentlyContinue | ForEach-Object { $_.Source }) +
          @(Get-ChildItem "C:\Python3*\python.exe" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }) |
          Where-Object { $_ } | Sort-Object -Descending | Select-Object -First 1
    if (-not $py) { $false }
    else { & $py "C:\HealthCheck\vm\rules\tds_engine.py" *> $null; $LASTEXITCODE -eq 0 }
} "statutory arithmetic is failing its own self-test - do NOT rely on computed TDS until fixed"

Check "Knowledge base: Python pipeline" {
    $py = @(Get-Command python.exe -ErrorAction SilentlyContinue | ForEach-Object { $_.Source }) +
          @(Get-ChildItem "C:\Python3*\python.exe" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }) |
          Where-Object { $_ } | Sort-Object -Descending | Select-Object -First 1
    if (-not $py) { $false }
    else { (& $py -c "import psycopg, pypdf, docx, openpyxl, bs4; print('ok')" 2>$null) -match "ok" }
} "ingestion unavailable: $fix (installs Python + packages)" -WarnOnly
$report = ($r | Out-String).Trim()
$report | Tee-Object "C:\HealthCheck\last-report.txt"
if ($script:fails -gt 0) { Write-Output "`nRESULT: $($script:fails) ISSUE(S) FOUND - see FAIL lines above" ; exit 1 }
else { Write-Output "`nRESULT: ALL CHECKS PASSED" ; exit 0 }
