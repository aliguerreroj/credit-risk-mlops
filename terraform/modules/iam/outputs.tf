output "glue_role_arn" {
  description = "ARN del IAM Role para Glue"
  value       = aws_iam_role.glue_role.arn
}

output "glue_role_name" {
  description = "Nombre del IAM Role para Glue"
  value       = aws_iam_role.glue_role.name
}