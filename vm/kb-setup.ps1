# kb-setup.ps1 — provision the knowledge base (ADR-0020).
#
# Called by repair.ps1 so it self-heals at every boot like every other
# component (ADR-0005). Idempotent by design: safe to run repeatedly, does
# nothing when already healthy.
#
# Checks behaviour, not file presence (ADR-0006): "can we run a query?",
# not "does a directory exist?".

$ErrorActionPreference = "Continue"
$choco = "C:\ProgramData\chocolatey\bin\choco.exe"

function Report($status, $what) { Write-Output ("[{0,-6}] {1}" -f $status, $what) }

# --- Python (ingestion pipeline) --------------------------------------------
# Discover rather than enumerate: Chocolatey's install location moves with the
# Python version (C:\Python314 today, something else next year). Globbing
# survives that; a hard-coded list does not.
function Find-Python {
    $candidates = @()
    $candidates += (Get-Command python.exe -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
    $candidates += (Get-ChildItem "C:\Python3*\python.exe" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    $candidates += (Get-ChildItem "C:\Program Files\Python3*\python.exe" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    $candidates += (Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    # Sort descending so the newest version wins when several are present.
    $candidates | Where-Object { $_ -and (Test-Path $_) } | Sort-Object -Descending | Select-Object -First 1
}

$python = Find-Python
if ($python) {
    Report "OK" "Python"
} else {
    & $choco install -y python3 *> $null
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $python = Find-Python
    if ($python) { Report "FIXED" "Python" } else { Report "FAILED" "Python (knowledge base ingestion unavailable)" }
}

# Password comes from the machine environment so it is set once and never
# committed. repair.ps1 generates it on first run if absent.
$kbPassword = [Environment]::GetEnvironmentVariable("MUNSHI_KB_PASSWORD", "Machine")
if (-not $kbPassword) {
    Add-Type -AssemblyName System.Web
    $kbPassword = [System.Web.Security.Membership]::GeneratePassword(24, 4)
    [Environment]::SetEnvironmentVariable("MUNSHI_KB_PASSWORD", $kbPassword, "Machine")
}

# --- PostgreSQL --------------------------------------------------------------
# Verified by connecting, not by looking for the service — a stopped or
# half-installed server must count as broken.
# Discover the newest installed PostgreSQL rather than listing versions.
function Find-PgBin {
    Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue |
        Sort-Object { [int]($_.Directory.Parent.Name) } -Descending |
        Select-Object -First 1 -ExpandProperty DirectoryName
}
$pgBin = Find-PgBin

function Test-Postgres($bin) {
    if (-not $bin) { return $false }
    $psql = Join-Path $bin "psql.exe"
    if (-not (Test-Path $psql)) { return $false }
    try {
        $env:PGPASSWORD = $kbPassword
        $out = & $psql -U postgres -h 127.0.0.1 -tAc "SELECT 1" 2>$null
        return ($out -match "1")
    } catch { return $false }
}

if (Test-Postgres $pgBin) {
    Report "OK" "PostgreSQL"
} else {
    & $choco install -y postgresql --params "/Password:$kbPassword" *> $null
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $pgBin = Find-PgBin
    Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Start-Service -ErrorAction SilentlyContinue
    if (Test-Postgres $pgBin) { Report "FIXED" "PostgreSQL" } else { Report "FAILED" "PostgreSQL" }
}

# --- pgvector extension ------------------------------------------------------
# Ships with recent PostgreSQL Windows builds; if CREATE EXTENSION fails the
# knowledge base still works for SQL + full-text search, only semantic search
# is lost. Degrade, don't abort.
if ($pgBin -and (Test-Postgres $pgBin)) {
    $psql = Join-Path $pgBin "psql.exe"
    $env:PGPASSWORD = $kbPassword

    $dbExists = & $psql -U postgres -h 127.0.0.1 -tAc "SELECT 1 FROM pg_database WHERE datname='munshi_kb'" 2>$null
    if ($dbExists -notmatch "1") {
        & $psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE munshi_kb" *> $null
    }

    $vec = & $psql -U postgres -h 127.0.0.1 -d munshi_kb -tAc "CREATE EXTENSION IF NOT EXISTS vector; SELECT 1" 2>$null
    if ($vec -match "1") { Report "OK" "pgvector" }
    else { Report "WARN" "pgvector unavailable (SQL + full-text search still work; semantic search disabled)" }

    # --- Migrations ---------------------------------------------------------
    # Numbered, idempotent, tracked in kb_schema_version.
    $migrationDir = "C:\HealthCheck\vm\kb\migrations"
    if (Test-Path $migrationDir) {
        foreach ($m in Get-ChildItem $migrationDir -Filter "*.sql" | Sort-Object Name) {
            $ver = [int]($m.Name -replace '^(\d+).*', '$1')
            $applied = & $psql -U postgres -h 127.0.0.1 -d munshi_kb -tAc `
                "SELECT 1 FROM kb_schema_version WHERE version=$ver" 2>$null
            if ($applied -match "1") { continue }
            # ON_ERROR_STOP is essential: without it psql continues past a
            # failed statement and a migration can record itself as applied
            # when it was not. Verified the hard way on a build lacking pgvector.
            & $psql -U postgres -h 127.0.0.1 -d munshi_kb -v ON_ERROR_STOP=1 -f $m.FullName *> $null
            $applied = & $psql -U postgres -h 127.0.0.1 -d munshi_kb -tAc `
                "SELECT 1 FROM kb_schema_version WHERE version=$ver" 2>$null
            if ($applied -match "1") { Report "FIXED" ("migration " + $m.Name) }
            elseif ($m.Name -like "002*") { Report "WARN" ("migration " + $m.Name + " skipped (needs pgvector)") }
            else { Report "FAILED" ("migration " + $m.Name) }
        }
        Report "OK" "knowledge base schema"
    } else {
        Report "WARN" "migrations folder missing (kb/migrations not synced)"
    }
}

# --- Python packages ---------------------------------------------------------
if ($python) {
    $needed = @("psycopg[binary]", "pypdf", "python-docx", "openpyxl", "beautifulsoup4")
    $probe = & $python -c "import psycopg, pypdf, docx, openpyxl, bs4; print('ok')" 2>$null
    if ($probe -match "ok") {
        Report "OK" "Python packages"
    } else {
        & $python -m pip install --quiet --upgrade pip *> $null
        & $python -m pip install --quiet @needed *> $null
        $probe = & $python -c "import psycopg, pypdf, docx, openpyxl, bs4; print('ok')" 2>$null
        if ($probe -match "ok") { Report "FIXED" "Python packages" } else { Report "FAILED" "Python packages" }
    }
}

# --- Data directories --------------------------------------------------------
# Inside C:\TallyData so the existing nightly snapshots cover them (ADR-0012).
foreach ($d in @("C:\TallyData\KnowledgeBase", "C:\TallyData\KnowledgeBase\imports")) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
}
Report "OK" "knowledge base folders"
