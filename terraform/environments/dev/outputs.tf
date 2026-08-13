output "bucket_name" {
  value = module.s3_data_bucket.bucket_name
}

output "bucket_arn" {
  value = module.s3_data_bucket.bucket_arn
}

output "glue_role_arn" {
  value = module.iam_glue_role.glue_role_arn
}

output "glue_role_name" {
  value = module.iam_glue_role.glue_role_name
}

output "bronze_to_silver_job_name" {
  value = module.glue_job.bronze_to_silver_job_name
}

output "silver_to_gold_job_name" {
  value = module.glue_job.silver_to_gold_job_name
}

output "sagemaker_role_arn" {
  value = module.sagemaker_role.sagemaker_role_arn
}

output "sagemaker_role_name" {
  value = module.sagemaker_role.sagemaker_role_name
}

output "ecr_repository_url" {
  value = module.ecr.repository_url
}

output "ecr_repository_arn" {
  value = module.ecr.repository_arn
}

output "api_gateway_url" {
  value = module.api_gateway.api_endpoint
}