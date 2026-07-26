# Email alerting: auto-stop notifications + monthly budget guard.
# Both are created only when alert_email is set.

locals {
  alerts_enabled = var.alert_email != ""
}

resource "aws_sns_topic" "alerts" {
  count = local.alerts_enabled ? 1 : 0
  name  = "${var.name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  count     = local.alerts_enabled ? 1 : 0
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
  # NOTE: AWS sends a confirmation email — the subscription only works after
  # clicking the "Confirm subscription" link in it.
}

# Hard guard on monthly spend: emails at 80% actual and 100% forecasted.
resource "aws_budgets_budget" "monthly" {
  count        = local.alerts_enabled ? 1 : 0
  name         = "${var.name}-monthly-budget"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
