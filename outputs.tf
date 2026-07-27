output "instance_id" {
  description = "EC2 instance ID of the Windows workstation."
  value       = aws_instance.this.id
}

output "region" {
  description = "AWS region the workstation lives in."
  value       = var.region
}

output "public_ip_at_apply_time" {
  description = "Public IP right now. NOTE: it changes on every stop/start — scripts/start.sh always prints the current one."
  value       = aws_instance.this.public_ip
}

output "private_key_file" {
  description = "Key file used to decrypt the Windows Administrator password (keep it safe, it is gitignored)."
  value       = local_sensitive_file.private_key.filename
}

output "how_to_connect" {
  description = "Quick reference."
  value       = <<-EOT
    1. ./scripts/start.sh                  -> starts the machine, prints browser + RDP address
    2. ./scripts/get-password.sh           -> prints the Administrator password
    3. Browser: https://<ip>:8443          (Amazon DCV, login as Administrator)
       or RDP:  <ip>:3389                  (Microsoft Remote Desktop app)
       or AWS Console -> Systems Manager -> Fleet Manager -> Remote Desktop (works even if your IP changed)
    4. ./scripts/stop.sh when done         (or it auto-stops after ~1h idle)
  EOT
}

output "user_passwords" {
  description = "Generated passwords for the default fenced users (Accountant, Auditor). Print with scripts/get-password.sh."
  value       = { for name, _ in local.default_users : name => random_password.vm_user[name].result }
  sensitive   = true
}
