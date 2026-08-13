module "s3_data_bucket" {
  source      = "../../modules/s3"
  bucket_name = "ali-credit-risk-mlops-dev"
  environment = "dev"
}

module "iam_glue_role" {
  source      = "../../modules/iam"
  environment = "dev"
  bucket_arn  = module.s3_data_bucket.bucket_arn
}

module "glue_job" {
  source        = "../../modules/glue"
  environment   = "dev"
  bucket_name   = module.s3_data_bucket.bucket_name
  glue_role_arn = module.iam_glue_role.glue_role_arn
}

module "sagemaker_role" {
  source      = "../../modules/sagemaker"
  environment = "dev"
  bucket_arn  = module.s3_data_bucket.bucket_arn
}

module "ecr" {
  source = "../../modules/ecr"
}

module "ecs" {
  source             = "../../modules/ecs"
  bucket_arn         = module.s3_data_bucket.bucket_arn
  ecr_repository_url = module.ecr.repository_url
  model_s3_bucket    = module.s3_data_bucket.bucket_name
  model_s3_key       = "models/pipelines-dqz60kgv2j2g-TrainModel-fqBLQa2h5g/output/model.tar.gz"
}

module "api_gateway" {
  source          = "../../modules/api_gateway"
  task_public_ip  = "3.88.20.175"
}

module "lambda_drift_check" {
  source       = "../../modules/lambda-drift-check"
  bucket_arn   = module.s3_data_bucket.bucket_arn
  pipeline_arn = "arn:aws:sagemaker:us-east-1:637992521859:pipeline/credit-risk-training-pipeline"
}

module "eventbridge" {
  source                = "../../modules/eventbridge"
  lambda_function_arn   = module.lambda_drift_check.lambda_function_arn
  lambda_function_name  = module.lambda_drift_check.lambda_function_name
}