<powershell>
# Thin first-boot loader. All real logic lives in vm/*.ps1, which terraform
# uploads to a private S3 bucket in this account — the VM pulls from there
# (and re-pulls at every boot), so scripts are updatable and there is no
# 16 KB user-data limit and no dependency on any external repository.
Start-Transcript -Path "C:\bootstrap-log.txt" -Append
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path "C:\HealthCheck\vm" | Out-Null
"__ASSETS_BUCKET__" | Out-File "C:\HealthCheck\bucket.txt" -Encoding ascii

Import-Module AWSPowerShell -ErrorAction SilentlyContinue
foreach ($try in 1..5) {
    try {
        Read-S3Object -BucketName "__ASSETS_BUCKET__" -KeyPrefix "vm" -Folder "C:\HealthCheck\vm" | Out-Null
        if (Test-Path "C:\HealthCheck\vm\bootstrap.ps1") { break }
    } catch {
        Write-Output "S3 fetch attempt $try failed: $($_.Exception.Message)"
        Start-Sleep -Seconds 20
    }
}

if (Test-Path "C:\HealthCheck\vm\bootstrap.ps1") {
    & powershell -ExecutionPolicy Bypass -File "C:\HealthCheck\vm\bootstrap.ps1"
} else {
    Write-Output "FATAL: could not fetch vm assets from S3 - check the instance role and bucket."
}
Stop-Transcript
</powershell>
<persist>false</persist>
