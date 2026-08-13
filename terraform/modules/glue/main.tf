resource "aws_s3_object" "bronze_to_silver_script" {
  bucket = var.bucket_name
  key    = "scripts/bronze_to_silver.py"
  source = "${path.module}/../../../glue-scripts/bronze_to_silver.py"
  etag   = filemd5("${path.module}/../../../glue-scripts/bronze_to_silver.py")
}

resource "aws_s3_object" "silver_to_gold_script" {
  bucket = var.bucket_name
  key    = "scripts/silver_to_gold.py"
  source = "${path.module}/../../../glue-scripts/silver_to_gold.py"
  etag   = filemd5("${path.module}/../../../glue-scripts/silver_to_gold.py")
}

resource "aws_glue_job" "bronze_to_silver" {
  name     = "credit-risk-bronze-to-silver-${var.environment}"
  role_arn = var.glue_role_arn

  command {
    name            = "glueetl"
    script_location = "s3://${var.bucket_name}/${aws_s3_object.bronze_to_silver_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--S3_BUCKET"                        = var.bucket_name
    "--job-language"                     = "python"
    "--enable-continuous-cloudwatch-log" = "true"
  }

  glue_version      = "4.0"
  number_of_workers = 2
  worker_type       = "G.1X"
  timeout           = 30

  tags = {
    Project     = "credit-risk-mlops"
    Environment = var.environment
    Layer       = "bronze-to-silver"
  }
}

resource "aws_glue_job" "silver_to_gold" {
  name     = "credit-risk-silver-to-gold-${var.environment}"
  role_arn = var.glue_role_arn

  command {
    name            = "glueetl"
    script_location = "s3://${var.bucket_name}/${aws_s3_object.silver_to_gold_script.key}"
    python_version  = "3"
  }

  default_arguments = {
    "--S3_BUCKET"                        = var.bucket_name
    "--job-language"                     = "python"
    "--enable-continuous-cloudwatch-log" = "true"
  }

  glue_version      = "4.0"
  number_of_workers = 2
  worker_type       = "G.1X"
  timeout           = 30

  tags = {
    Project     = "credit-risk-mlops"
    Environment = var.environment
    Layer       = "silver-to-gold"
  }
}