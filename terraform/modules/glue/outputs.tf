output "bronze_to_silver_job_name" {
  description = "Nombre del Glue Job Bronze → Silver"
  value       = aws_glue_job.bronze_to_silver.name
}

output "silver_to_gold_job_name" {
  description = "Nombre del Glue Job Silver → Gold"
  value       = aws_glue_job.silver_to_gold.name
}