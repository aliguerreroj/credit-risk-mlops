resource "aws_apigatewayv2_api" "credit_risk_api" {
  name          = "credit-risk-api-gateway-dev"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "ecs_task_integration" {
  api_id             = aws_apigatewayv2_api.credit_risk_api.id
  integration_type   = "HTTP_PROXY"
  integration_method = "ANY"
  integration_uri    = "http://${var.task_public_ip}:8000/{proxy}"
}

resource "aws_apigatewayv2_route" "proxy_route" {
  api_id    = aws_apigatewayv2_api.credit_risk_api.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.ecs_task_integration.id}"
}

resource "aws_apigatewayv2_stage" "dev" {
  api_id      = aws_apigatewayv2_api.credit_risk_api.id
  name        = "$default"
  auto_deploy = true
}