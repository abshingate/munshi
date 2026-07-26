# Recurring Google Drive sync (run every 5 min by the TallyCloudDriveSync
# task). Wraps rclone bisync and maintains a human-readable status file so
# users — and the health check — always know whether a sync is running,
# when the last one finished, and whether any file is still incomplete.
$ErrorActionPreference = "Continue"
$rclone = "C:\ProgramData\chocolatey\bin\rclone.exe"
$conf = "C:\ProgramData\rclone\rclone.conf"
$local = "C:\TallyData\Drive"
$status = "C:\TallyData\_DriveSyncStatus.txt"
$folderFile = "C:\ProgramData\rclone\sync-folder.txt"

if (-not (Test-Path $conf)) { exit 0 }   # not set up yet
$folder = "TallyCloud"
if (Test-Path $folderFile) { $f = (Get-Content $folderFile -Raw).Trim(); if ($f) { $folder = $f } }
$remote = "gdrive:$folder"
New-Item -ItemType Directory -Force -Path $local | Out-Null

# A one-time explainer inside the synced folder (visible on the phone too)
$readme = Join-Path $local "_READ-ME how syncing works.txt"
if (-not (Test-Path $readme)) {
    @"
HOW THIS FOLDER SYNCS
=====================
This folder and the '$folder' folder in Google Drive are the same folder -
they sync BOTH WAYS every 5 minutes.

IS MY FILE FULLY DOWNLOADED?
A file that is still arriving has a name ending in  .partial
The moment you can see the normal file name, the file is COMPLETE.

The file _DriveSyncStatus.txt next to this folder (in C:\TallyData) shows
whether a sync is running right now and when the last one finished.
"@ | Out-File $readme -Encoding ascii
}

# Janitor: a .partial not touched for an hour is an orphan from an
# interrupted transfer (live transfers are being written continuously) —
# delete it; the next sync re-transfers the file cleanly from source.
$cutoff = (Get-Date).AddHours(-1)
$orphans = @(Get-ChildItem $local -Recurse -Filter "*.partial" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt $cutoff })
foreach ($o in $orphans) { Remove-Item $o.FullName -Force -ErrorAction SilentlyContinue }

"SYNCING NOW (started $(Get-Date -Format 'dd-MMM-yyyy HH:mm:ss')).
Files still arriving end in .partial - a file with its normal name is complete." | Out-File $status -Encoding ascii

# --recover / --max-lock let bisync survive interruptions and stale locks
$flags = "--create-empty-src-dirs --workdir C:\ProgramData\rclone\bisync --recover --max-lock 15m --conflict-resolve newer"
cmd /c "`"$rclone`" --config `"$conf`" bisync `"$remote`" `"$local`" $flags 2>nul" | Out-Null
$code = $LASTEXITCODE
$recovered = $false
if ($code -ne 0) {
    # Self-recovery: a critically interrupted bisync refuses to run again
    # until re-baselined; do that automatically rather than staying stuck.
    cmd /c "`"$rclone`" --config `"$conf`" bisync `"$remote`" `"$local`" $flags --resync 2>nul" | Out-Null
    $code = $LASTEXITCODE
    if ($code -eq 0) { $recovered = $true }
}

$partials = @(Get-ChildItem $local -Recurse -Filter "*.partial" -ErrorAction SilentlyContinue)
$now = Get-Date -Format "dd-MMM-yyyy HH:mm:ss"
$notes = @()
if ($recovered) { $notes += "(sync self-recovered from an earlier interruption)" }
if ($orphans.Count -gt 0) { $notes += "(cleaned $($orphans.Count) leftover incomplete file(s) from an interrupted transfer)" }
$noteText = ""
if ($notes.Count -gt 0) { $noteText = "`r`n" + ($notes -join "`r`n") }
if ($code -eq 0 -and $partials.Count -eq 0) {
    "OK - last sync finished $now.
Every file currently in the Drive folder is COMPLETE.
Next sync within 5 minutes.$noteText" | Out-File $status -Encoding ascii
} elseif ($code -eq 0) {
    "OK - last sync finished $now, BUT these files are still incomplete:
$($partials.Name -join "`r`n")
They will finish in a following sync - do not use them yet.$noteText" | Out-File $status -Encoding ascii
} else {
    "SYNC PROBLEM (rclone exit $code) at $now - will retry in 5 minutes.
If this persists, run 'Set up Google Drive' on the desktop again.$noteText" | Out-File $status -Encoding ascii
}
