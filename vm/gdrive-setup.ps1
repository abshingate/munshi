# One-time Google Drive sync setup. Run interactively on the VM (desktop
# button "Set up Google Drive") — it opens a Google sign-in page once, then
# registers a task that syncs C:\TallyData\Drive with the "TallyCloud"
# folder in the user's Google Drive every 5 minutes (two-way).
#
# Note: ErrorActionPreference stays "Continue" — rclone writes routine
# NOTICEs to stderr (e.g. "config file not found" on first run), which
# PowerShell 5.1 would otherwise escalate into a terminating error.
$ErrorActionPreference = "Continue"
$rclone = "C:\ProgramData\chocolatey\bin\rclone.exe"
$conf = "C:\ProgramData\rclone\rclone.conf"
$local = "C:\TallyData\Drive"

if (-not (Test-Path $rclone)) {
    Write-Host "rclone is not installed yet - double-click 'Repair This Computer' first, then run this again."
    exit 1
}
New-Item -ItemType Directory -Force -Path (Split-Path $conf), $local | Out-Null

# cmd handles the stderr redirect so PowerShell never sees rclone's NOTICEs
$remotes = @(cmd /c "`"$rclone`" --config `"$conf`" listremotes 2>nul")
if (-not ($remotes -match "^gdrive:")) {
    Write-Host ""
    Write-Host "A Google sign-in page will open in your browser."
    Write-Host "Sign in with your Google account and click Allow, then come back here."
    Write-Host ""
    & $rclone --config $conf config create gdrive drive scope=drive
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "The Google sign-in did not complete. Run this again to retry."
        exit 1
    }
}

# Which folder in Drive to sync — root-level "TallyCloud" by default, but any
# path works (e.g. Accounts/Tally). Re-running this script lets you change it.
$folderFile = "C:\ProgramData\rclone\sync-folder.txt"
$default = "TallyCloud"
if (Test-Path $folderFile) { $default = (Get-Content $folderFile -Raw).Trim() }
Write-Host ""
$folder = Read-Host "Folder in your Google Drive to sync (can be a path like Accounts/Tally) [$default]"
if ([string]::IsNullOrWhiteSpace($folder)) { $folder = $default }
$folder = $folder.Trim().Trim("/").Replace("\", "/")
$folder | Out-File $folderFile -Encoding ascii
$remote = "gdrive:$folder"

Write-Host ""
Write-Host "Doing the first sync (this creates '$folder' in your Google Drive if it doesn't exist)..."
cmd /c "`"$rclone`" --config `"$conf`" mkdir `"$remote`" 2>nul" | Out-Null
& $rclone --config $conf bisync $remote $local --create-empty-src-dirs --resync
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "The first sync did not complete - check the messages above and run this again."
    exit 1
}

schtasks /Create /TN "TallyCloudDriveSync" /SC MINUTE /MO 5 /RU SYSTEM /RL HIGHEST /F `
    /TR "`"$rclone`" --config $conf bisync `"$remote`" C:\TallyData\Drive --create-empty-src-dirs" | Out-Null

Write-Host ""
Write-Host "Done! From now on:"
Write-Host "  - Anything you put in the '$folder' folder of your Google Drive"
Write-Host "    (from any phone or computer) appears in C:\TallyData\Drive here."
Write-Host "  - Anything you put in C:\TallyData\Drive appears in your Google Drive."
Write-Host "  - Syncs every 5 minutes, both ways."
