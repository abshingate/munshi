# Daily EBS snapshots of the workstation via Data Lifecycle Manager.
# Snapshots are incremental; for a mostly-idle machine this costs well under $1/month.

data "aws_iam_policy_document" "dlm_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["dlm.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "dlm" {
  name               = "${var.name}-dlm-role"
  assume_role_policy = data.aws_iam_policy_document.dlm_assume.json
}

resource "aws_iam_role_policy_attachment" "dlm" {
  role       = aws_iam_role.dlm.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"
}

resource "aws_dlm_lifecycle_policy" "daily" {
  description        = "Daily snapshots for ${var.name}"
  execution_role_arn = aws_iam_role.dlm.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["INSTANCE"]

    target_tags = {
      Backup = var.name
    }

    schedule {
      name      = "daily-2am-ist"
      copy_tags = true

      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["20:30"] # UTC = 02:00 IST
      }

      retain_rule {
        count = var.snapshot_retention_days
      }
    }
  }
}
