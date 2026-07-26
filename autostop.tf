# Safety net: if the instance sits idle (CPU below threshold for 4 x 15 min),
# stop it automatically so a forgotten session never runs for a month.

resource "aws_cloudwatch_metric_alarm" "idle_autostop" {
  count = var.enable_idle_autostop ? 1 : 0

  alarm_name          = "${var.name}-idle-autostop"
  alarm_description   = "Stops ${var.name} after ~1 hour of idle CPU"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 900
  evaluation_periods  = 4
  threshold           = var.idle_cpu_threshold
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = aws_instance.this.id
  }

  # Stop the instance; also email the user (if alerting is enabled) so they
  # know the machine turned itself off.
  alarm_actions = concat(
    ["arn:aws:automate:${var.region}:ec2:stop"],
    local.alerts_enabled ? [aws_sns_topic.alerts[0].arn] : []
  )
}
