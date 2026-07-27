variable "name" {
  description = "Name prefix for all resources."
  type        = string
  default     = "tally-workstation"
}

variable "region" {
  description = "AWS region to deploy in."
  type        = string
  default     = "ap-south-1"
}

variable "allowed_cidr" {
  description = "CIDR allowed to reach RDP (3389) and DCV (8443). Use your own public IP, e.g. \"1.2.3.4/32\" (find it with: curl -s https://checkip.amazonaws.com). If your ISP changes your IP, update this and re-run terraform apply."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type. t3.large (2 vCPU / 8 GB) is comfortable for TallyPrime + browser."
  type        = string
  default     = "t3.large"
}

variable "volume_size_gb" {
  description = "Root EBS volume size in GB (holds Windows, Tally, and all data)."
  type        = number
  default     = 100
}

variable "snapshot_retention_days" {
  description = "How many daily EBS snapshots to keep."
  type        = number
  default     = 14
}

variable "enable_idle_autostop" {
  description = "Automatically stop the instance after ~1 hour of idle CPU, so forgetting to stop it never costs a full month."
  type        = bool
  default     = true
}

variable "tally_edition" {
  description = "Which TallyPrime build to stage: 'editlog' (TallyPrime Edit Log — always-on audit trail, required for companies under MCA Companies (Accounts) Rules since 1 Apr 2023; the safe default) or 'standard' (edit log optional; fine for proprietorships/partnerships). Same Tally license works for both."
  type        = string
  default     = "editlog"
  validation {
    condition     = contains(["editlog", "standard"], var.tally_edition)
    error_message = "tally_edition must be 'editlog' or 'standard'."
  }
}

variable "alert_email" {
  description = "Email address for alerts (auto-stop events, budget warnings). Empty string disables alerting. AWS sends a one-time confirmation email you must accept."
  type        = string
  default     = ""
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget in USD; email alerts fire at 80% actual and 100% forecasted spend."
  type        = number
  default     = 25
}

variable "idle_cpu_threshold" {
  description = "CPU percentage below which the instance is considered idle."
  type        = number
  default     = 2
}

variable "dns_hostname" {
  description = "Optional stable DNS name for the workstation (e.g. tally.example.com). The VM upserts this Route 53 A record with its current public IP at every boot, so the address never changes for users. Requires dns_zone. Empty string disables the feature."
  type        = string
  default     = ""
}

variable "dns_zone" {
  description = "Route 53 hosted zone that dns_hostname belongs to (e.g. example.com). Must already exist in this AWS account; only a single A record for dns_hostname is ever touched, so an existing website/email on the domain is unaffected."
  type        = string
  default     = ""

  validation {
    condition     = (var.dns_hostname == "") == (var.dns_zone == "")
    error_message = "dns_hostname and dns_zone must be set together (or both left empty)."
  }
}

variable "create_default_users" {
  description = "Create the default fenced, non-administrator RDP users at every converge: 'Accountant' (Tally + documents read/write) and 'Auditor' (documents read-only; Tally display-only is enforced via Tally's own security users). Their generated passwords are printed by scripts/get-password.sh. Additional users: scripts/add-vm-user.sh."
  type        = bool
  default     = true
}
