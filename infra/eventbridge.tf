# ── EventBridge Scheduled Rule ─────────────────────────────────────────────────

# Daily job scan trigger
resource "aws_cloudwatch_event_rule" "daily_scan" {
  name                = "${var.project_name}-daily-scan"
  description         = "Triggers the job scanner Lambda daily"
  schedule_expression = var.schedule_expression

  tags = {
    Name = "${var.project_name}-daily-scan"
  }
}

resource "aws_cloudwatch_event_target" "daily_scan_target" {
  rule      = aws_cloudwatch_event_rule.daily_scan.name
  target_id = "job-scanner-target"
  arn       = aws_lambda_function.job_scanner.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.job_scanner.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_scan.arn
}
