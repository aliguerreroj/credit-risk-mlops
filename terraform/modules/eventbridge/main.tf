resource "aws_cloudwatch_event_rule" "daily_drift_check" {
  name                = "credit-risk-daily-drift-check-dev"
  description         = "Dispara la Lambda de detección de drift una vez al día"
  schedule_expression = "rate(1 day)"
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_drift_check.name
  target_id = "check-drift-lambda"
  arn       = var.lambda_function_arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_drift_check.arn
}