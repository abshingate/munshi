# update-dns.ps1 — keep the workstation's stable hostname pointing at its
# current public IP (see ADR-0018). Runs at every boot (TallyCloudDnsUpdate
# task, created by repair.ps1) and again during every repair. No-op unless the
# deployment sets the dns_hostname/dns_zone Terraform variables, which deliver
# vm/dns-config.json through the assets bucket.
$ErrorActionPreference = "Stop"
$log = "C:\HealthCheck\dns-update.log"
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $m" | Add-Content $log }

$cfgPath = "C:\HealthCheck\vm\dns-config.json"
if (-not (Test-Path $cfgPath)) { exit 0 }   # feature not configured
$cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json

# The Windows AMI ships the monolithic AWSPowerShell module; child sessions
# must import it explicitly before the Route 53 types are available.
Import-Module AWSPowerShell -ErrorAction Stop

try {
    # Public IP from instance metadata (IMDSv2)
    $token = Invoke-RestMethod -Method PUT -Uri "http://169.254.169.254/latest/api/token" `
        -Headers @{ "X-aws-ec2-metadata-token-ttl-seconds" = "60" } -TimeoutSec 10
    $ip = Invoke-RestMethod -Uri "http://169.254.169.254/latest/meta-data/public-ipv4" `
        -Headers @{ "X-aws-ec2-metadata-token" = $token } -TimeoutSec 10

    $rrs = New-Object Amazon.Route53.Model.ResourceRecordSet
    $rrs.Name = $cfg.hostname
    $rrs.Type = "A"
    $rrs.TTL  = 60
    $rrs.ResourceRecords = New-Object 'System.Collections.Generic.List[Amazon.Route53.Model.ResourceRecord]'
    $rrs.ResourceRecords.Add((New-Object Amazon.Route53.Model.ResourceRecord($ip)))
    $change = New-Object Amazon.Route53.Model.Change
    $change.Action = "UPSERT"
    $change.ResourceRecordSet = $rrs
    Edit-R53ResourceRecordSet -HostedZoneId $cfg.zone_id -ChangeBatch_Change $change | Out-Null
    Log "OK: $($cfg.hostname) -> $ip"
} catch {
    Log "FAILED: $($_.Exception.Message)"
    exit 1
}
