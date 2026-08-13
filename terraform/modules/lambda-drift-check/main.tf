data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../../../lambda/check_drift_lambda.py"
  output_path = "${path.module}/lambda_package.zip"
}

resource "aws_iam_role" "lambda_execution_role" {
  name = "credit-risk-lambda-drift-role-dev"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3_and_sagemaker_access" {
  name = "credit-risk-lambda-drift-policy-dev"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          var.bucket_arn,
          "${var.bucket_arn}/monitoring/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["sagemaker:StartPipelineExecution"]
        Resource = var.pipeline_arn
      }
    ]
  })
}

resource "aws_lambda_function" "check_drift" {
  function_name    = "credit-risk-check-drift-dev"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  handler          = "check_drift_lambda.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_execution_role.arn
  timeout          = 60
  memory_size      = 256
}