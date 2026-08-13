output "bucket_name" {
  description = "Nombre del bucket creado"
  value       = aws_s3_bucket.data_bucket.id
}

output "bucket_arn" {
  description = "ARN del bucket creado"
  value       = aws_s3_bucket.data_bucket.arn
}