output "sagemaker_role_arn" {
  description = "ARN del IAM Role para SageMaker"
  value       = aws_iam_role.sagemaker_role.arn
}

output "sagemaker_role_name" {
  description = "Nombre del IAM Role para SageMaker"
  value       = aws_iam_role.sagemaker_role.name
}