# TallyCloud repair - idempotent installer for every software component.
# Runs at first boot, at every boot (scheduled task), and on demand via the
# desktop "Repair This Computer" button or scripts/repair.sh (SSM).
# Present components are left untouched; missing ones are (re)installed with
# retries and fallback URLs. Log: C:\HealthCheck\repair-log.txt
Start-Transcript -Path "C:\HealthCheck\repair-log.txt" -Append
$ErrorActionPreference = "Continue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
New-Item -ItemType Directory -Force -Path "C:\Installers" | Out-Null
$script:fails = 0
function Report($state, $name) {
    if ($state -eq "FAILED") { $script:fails++ }
    Write-Output ("{0,-6} {1}" -f $state, $name)
}
function Get-File($urls, $out, $minBytes) {
    foreach ($u in $urls) {
        foreach ($try in 1..2) {
            try {
                Invoke-WebRequest -Uri $u -OutFile $out -UseBasicParsing -TimeoutSec 300
                if ((Get-Item $out -ErrorAction SilentlyContinue).Length -ge $minBytes) { return $true }
            } catch { Write-Output "  download failed ($u, try ${try}): $($_.Exception.Message)" }
        }
    }
    return $false
}

# --- Chocolatey (package manager everything else rides on) -------------------
$choco = "C:\ProgramData\chocolatey\bin\choco.exe"
if (-not (Test-Path $choco)) {
    try {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    } catch { Write-Output "  choco bootstrap failed: $($_.Exception.Message)" }
}
if (Test-Path $choco) { Report "OK" "Chocolatey" } else { Report "FAILED" "Chocolatey (everything below may also fail)" }

# --- Desktop software (checked by real file, not package metadata) -----------
# Each package lists every install location seen across vendor versions —
# present at ANY of them counts as installed.
$apps = [ordered]@{
    "googlechrome"    = @("C:\Program Files\Google\Chrome\Application\chrome.exe")
    "7zip"            = @("C:\Program Files\7-Zip\7z.exe")
    "adobereader"     = @("C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
                          "C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe")
    "notepadplusplus" = @("C:\Program Files\Notepad++\notepad++.exe")
    "git"             = @("C:\Program Files\Git\cmd\git.exe")
    "nodejs-lts"      = @("C:\Program Files\nodejs\node.exe")
}
function Test-AnyPath($paths) { @($paths | Where-Object { Test-Path $_ }).Count -gt 0 }
foreach ($pkg in $apps.Keys) {
    if (Test-AnyPath $apps[$pkg]) { Report "OK" $pkg; continue }
    & $choco install -y $pkg *> $null
    if (-not (Test-AnyPath $apps[$pkg])) { & $choco install -y $pkg --ignore-checksums *> $null }
    if (Test-AnyPath $apps[$pkg]) { Report "FIXED" $pkg } else { Report "FAILED" $pkg }
}

# --- Java 8, 32-bit AND 64-bit (GST emSigner / TRACES WebSigner) -------------
if ((Test-Path "C:\Program Files\Java") -and (Test-Path "C:\Program Files (x86)\Java")) {
    Report "OK" "Java 8 (32+64-bit)"
} else {
    & $choco install -y jre8 *> $null
    if ((Test-Path "C:\Program Files\Java") -and (Test-Path "C:\Program Files (x86)\Java")) {
        Report "FIXED" "Java 8 (32+64-bit)"
    } else { Report "FAILED" "Java 8 (32+64-bit)" }
}

# --- Claude Code (verified by executing it, not by file presence) ------------
$claudeCmd = "C:\Program Files\nodejs\claude.cmd"
$claudeOk = $false
try { $claudeOk = (& $claudeCmd --version 2>$null) -match "Claude" } catch {}
if ($claudeOk) { Report "OK" "Claude Code" }
elseif (Test-Path "C:\Program Files\nodejs\npm.cmd") {
    foreach ($try in 1..2) {
        & "C:\Program Files\nodejs\npm.cmd" install -g --force --prefix "C:\Program Files\nodejs" "@anthropic-ai/claude-code" *> $null
        try { if ((& $claudeCmd --version 2>$null) -match "Claude") { $claudeOk = $true; break } } catch {}
    }
    if ($claudeOk) { Report "FIXED" "Claude Code" } else { Report "FAILED" "Claude Code" }
} else { Report "FAILED" "Claude Code (Node.js missing)" }

# --- Amazon DCV (browser desktop) --------------------------------------------
if (Get-Service dcvserver -ErrorAction SilentlyContinue) { Report "OK" "Amazon DCV" }
else {
    $msi = "C:\Installers\dcv-server.msi"
    $ok = Get-File @(
        "https://d1uj6qtbmh3dt5.cloudfront.net/nice-dcv-server-x64-Release.msi"
    ) $msi 30MB
    if ($ok) {
        Start-Process msiexec.exe -Wait -ArgumentList "/i `"$msi`" ADDLOCAL=ALL /quiet /norestart AUTOMATIC_SESSION_OWNER=Administrator"
    }
    if (Get-Service dcvserver -ErrorAction SilentlyContinue) { Report "FIXED" "Amazon DCV" }
    else { Report "FAILED" "Amazon DCV (RDP and Fleet Manager still work)" }
}

# --- TallyPrime installer (edition-aware) ------------------------------------
# Edition comes from vm/tally-edition.txt (written by terraform): "editlog"
# (TPEL build — always-on audit trail, MCA-compliant, the default) or
# "standard" (TP build). URL is discovered live from Tally's own site JS
# (newest release wins), with last-known-good mirrors as fallback.
$edition = "editlog"
$edFile = "C:\HealthCheck\vm\tally-edition.txt"
if (Test-Path $edFile) {
    $t = (Get-Content $edFile -Raw).Trim()
    if ($t -in @("standard", "editlog")) { $edition = $t }
}
$sub = "TPEL"; $edLabel = "Edit Log edition"
if ($edition -eq "standard") { $sub = "TP"; $edLabel = "standard edition" }
$edMarker = "C:\Installers\tally-installer-edition.txt"
$stagedEdition = ""
if (Test-Path $edMarker) { $stagedEdition = (Get-Content $edMarker -Raw).Trim() }
$installerOk = (Test-Path "C:\Installers\TallyPrimeSetup.exe") -and ($stagedEdition -eq $edition)

if (-not $installerOk) {
    $urls = @()
    foreach ($js in @("https://tallysolutions.com/utility/js/DownloadUtility-india.js",
                      "https://tallysolutions.com/utility/js/DownloadUtility.js")) {
        try {
            $body = (Invoke-WebRequest -Uri $js -UseBasicParsing -TimeoutSec 60).Content -replace '\\/', '/'
            $urls += [regex]::Matches($body, "https://tallymirror\.tallysolutions\.com/download_centre/Rel[._]?[0-9]+\.[0-9]+/$sub/Full/setup\.exe") |
                ForEach-Object { $_.Value }
        } catch { Write-Output "  Tally JS fetch failed ($js)" }
    }
    $urls = @($urls | Sort-Object -Unique -Descending -Property `
        @{Expression = { [version]($_ -replace '.*Rel[._]?([0-9]+\.[0-9]+).*', '$1') }})
    $urls += @("https://tallymirror.tallysolutions.com/download_centre/Rel7.1/$sub/Full/setup.exe",
               "https://tallymirror.tallysolutions.com/download_centre/Rel6.2/$sub/Full/setup.exe")
    if (Get-File $urls "C:\Installers\TallyPrimeSetup.exe" 10MB) {
        $edition | Out-File $edMarker -Encoding ascii
        Copy-Item "C:\Installers\TallyPrimeSetup.exe" "C:\Users\Public\Desktop\TallyPrimeSetup.exe" -Force
        if (Test-Path "C:\Program Files\TallyPrime\tally.exe") {
            Report "FIXED" "TallyPrime installer ($edLabel) staged - run TallyPrimeSetup.exe on the desktop to switch editions"
        } else {
            Report "FIXED" "TallyPrime installer ($edLabel) staged"
        }
    } else { Report "FAILED" "TallyPrime installer ($edLabel) (use the Download TallyPrime desktop shortcut)" }
} elseif (Test-Path "C:\Program Files\TallyPrime\tally.exe") {
    Report "OK" "TallyPrime (installed; $edLabel installer staged)"
} else {
    Report "OK" "TallyPrime installer staged ($edLabel)"
}

# --- OpenSSH server (carries the DSC-token reverse tunnel) -------------------
$sshd = Get-Service sshd -ErrorAction SilentlyContinue
if ($sshd -and $sshd.Status -eq "Running") { Report "OK" "OpenSSH server" }
else {
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
    Set-Service sshd -StartupType Automatic -ErrorAction SilentlyContinue
    Start-Service sshd -ErrorAction SilentlyContinue
    if ((Get-Service sshd -ErrorAction SilentlyContinue).Status -eq "Running") { Report "FIXED" "OpenSSH server" }
    else { Report "FAILED" "OpenSSH server (DSC tunnel unavailable; RDP smart-card still works)" }
}
$akSrc = "C:\HealthCheck\vm\authorized_keys"
$akDst = "C:\ProgramData\ssh\administrators_authorized_keys"
if (Test-Path $akSrc) {
    $current = ""; if (Test-Path $akDst) { $current = Get-Content $akDst -Raw }
    $wanted = Get-Content $akSrc -Raw
    if ($current.Trim() -eq $wanted.Trim()) { Report "OK" "SSH authorized key" }
    else {
        Copy-Item $akSrc $akDst -Force
        icacls $akDst /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F" | Out-Null
        Report "FIXED" "SSH authorized key"
    }
} else { Report "FAILED" "SSH authorized key (missing from assets bucket)" }

# --- Google Drive for Desktop (file sharing between machines and the VM) -----
$gdInstalled = @(Get-ChildItem "C:\Program Files\Google\Drive File Stream" -Recurse -Filter "GoogleDriveFS.exe" -ErrorAction SilentlyContinue).Count -gt 0
if ($gdInstalled) { Report "OK" "Google Drive" }
else {
    $gdSetup = "C:\Installers\GoogleDriveSetup.exe"
    if (Get-File @("https://dl.google.com/drive-file-stream/GoogleDriveSetup.exe") $gdSetup 50MB) {
        Start-Process $gdSetup -Wait -ArgumentList "--silent --desktop_shortcut"
        $gdInstalled = @(Get-ChildItem "C:\Program Files\Google\Drive File Stream" -Recurse -Filter "GoogleDriveFS.exe" -ErrorAction SilentlyContinue).Count -gt 0
        if ($gdInstalled) { Report "FIXED" "Google Drive (sign in once from the desktop icon)" }
        else { Report "FAILED" "Google Drive install did not complete" }
    } else { Report "FAILED" "Google Drive download" }
}

# --- VirtualHere client (DSC token over USB-over-IP) --------------------------
$vh = "C:\Users\Public\Desktop\DSC Setup\VirtualHere Client.exe"
if (Test-Path $vh) { Report "OK" "VirtualHere client" }
elseif (Get-File @("https://www.virtualhere.com/sites/default/files/usbclient/vhui64.exe") $vh 500KB) {
    Report "FIXED" "VirtualHere client"
} else { Report "FAILED" "VirtualHere client (download from virtualhere.com when needed)" }

# --- AI Accountant app (Node web app on https://<machine>:8444) --------------
$appSrc = "C:\HealthCheck\vm\app"
$appDst = "C:\TallyAI"
if (Test-Path "$appSrc\server.js") {
    New-Item -ItemType Directory -Force -Path $appDst, "$appDst\data" | Out-Null
    robocopy $appSrc $appDst /E /XD data node_modules /NFL /NDL /NJH /NJS /NP | Out-Null

    if (-not (Test-Path "$appDst\cert.pfx")) {
        $cert = New-SelfSignedCertificate -DnsName "tally-ai" -CertStoreLocation Cert:\LocalMachine\My -NotAfter (Get-Date).AddYears(5)
        # The PFX passphrase is deliberately fixed and non-secret: it wraps a
        # self-signed localhost cert and the app must know it to serve HTTPS.
        $pw = [System.Security.SecureString]::new()
        foreach ($ch in "tallyai".ToCharArray()) { $pw.AppendChar($ch) }
        Export-PfxCertificate -Cert $cert -FilePath "$appDst\cert.pfx" -Password $pw | Out-Null
    }

    if (-not (Test-Path "$appDst\node_modules\@anthropic-ai\sdk")) {
        Push-Location $appDst
        & "C:\Program Files\nodejs\npm.cmd" install --omit=dev --no-audit --no-fund *> $null
        Pop-Location
    }
    $depsOk = Test-Path "$appDst\node_modules\@anthropic-ai\sdk"

    if (-not (Get-NetFirewallRule -DisplayName "TallyAI" -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName "TallyAI" -Direction Inbound -Protocol TCP -LocalPort 8444 -Action Allow | Out-Null
    }
    schtasks /Create /TN "TallyAIApp" /SC ONSTART /RU SYSTEM /RL HIGHEST /F `
        /TR "\`"C:\Program Files\nodejs\node.exe\`" C:\TallyAI\server.js" | Out-Null

    # Restart only when the code changed or the app isn't running, so a routine
    # repair never drops an in-flight chat.
    $hashSrc = (Get-ChildItem "$appDst\server.js", "$appDst\package.json", "$appDst\lib\*.js", "$appDst\public\*.html", "$appDst\public\*.css" |
        Get-FileHash -Algorithm SHA256 | ForEach-Object Hash) -join ""
    $verFile = "$appDst\data\app-version.txt"
    $prev = ""; if (Test-Path $verFile) { $prev = Get-Content $verFile -Raw }
    $listening = (Test-NetConnection localhost -Port 8444 -WarningAction SilentlyContinue).TcpTestSucceeded
    if ($depsOk -and ((-not $listening) -or ($hashSrc.Trim() -ne $prev.Trim()))) {
        schtasks /End /TN "TallyAIApp" 2>$null | Out-Null
        Start-Sleep -Seconds 2
        schtasks /Run /TN "TallyAIApp" | Out-Null
        Start-Sleep -Seconds 4
        $hashSrc | Out-File $verFile -Encoding ascii
        $listening = (Test-NetConnection localhost -Port 8444 -WarningAction SilentlyContinue).TcpTestSucceeded
        if ($listening) { Report "FIXED" "AI Accountant app (port 8444)" }
        else { Report "FAILED" "AI Accountant app not listening on 8444 (schtasks /Run TallyAIApp; node C:\TallyAI\server.js for logs)" }
    } elseif ($depsOk -and $listening) {
        Report "OK" "AI Accountant app (port 8444)"
    } else {
        Report "FAILED" "AI Accountant dependencies (npm install @anthropic-ai/sdk failed)"
    }
} else {
    Report "FAILED" "AI Accountant app files missing from assets sync"
}

Write-Output ""
if ($script:fails -gt 0) {
    Write-Output "REPAIR RESULT: $($script:fails) component(s) still broken - will retry at next boot, or double-click Repair This Computer after checking the internet connection."
} else {
    Write-Output "REPAIR RESULT: ALL COMPONENTS OK"
}
Stop-Transcript
exit $script:fails
