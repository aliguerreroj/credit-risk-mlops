resource "aws_security_group" "ecs_task" {
  name        = "credit-risk-api-sg"
  description = "Security group for the credit risk API ECS task"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Allow inbound traffic on port 8000"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}