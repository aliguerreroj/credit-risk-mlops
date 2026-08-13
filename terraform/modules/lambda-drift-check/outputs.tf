output "lambda_function_arn" {
  value = aws_lambda_function.check_drift.arn
}

output "lambda_function_name" {
  value = aws_lambda_function.check_drift.function_name
}