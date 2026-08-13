variable "bucket_arn" {
  description = "ARN del bucket S3 donde vive el modelo entrenado"
  type        = string
}

variable "ecr_repository_url" {
  description = "URL del repositorio ECR con la imagen del microservicio"
  type        = string
}

variable "model_s3_bucket" {
  type = string
}

variable "model_s3_key" {
  type = string
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "desired_count" {
  description = "Número de tareas activas. 0 = apagado (sin costo), 1 = encendido para pruebas"
  type        = number
  default     = 0
}