resource "aws_ecs_cluster" "credit_risk_cluster" {
  name = "credit-risk-cluster-dev"
}

resource "aws_cloudwatch_log_group" "ecs_task_logs" {
  name              = "/ecs/credit-risk-api-dev"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "credit_risk_api" {
  family                   = "credit-risk-api-dev"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn             = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "credit-risk-api"
      image     = "${var.ecr_repository_url}:v1"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "MODEL_S3_BUCKET", value = var.model_s3_bucket },
        { name = "MODEL_S3_KEY", value = var.model_s3_key },
        { name = "AWS_DEFAULT_REGION", value = var.aws_region }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_task_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "credit_risk_api" {
  name            = "credit-risk-api-service-dev"
  cluster         = aws_ecs_cluster.credit_risk_cluster.id
  task_definition = aws_ecs_task_definition.credit_risk_api.arn
  desired_count = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_task.id]
    assign_public_ip = true
  }
}