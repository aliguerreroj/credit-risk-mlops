variable "environment" {
  description = "Ambiente (dev, prod)"
  type        = string
  default     = "dev"
}

variable "bucket_name" {
  description = "Nombre del bucket S3 donde están los datos y el script"
  type        = string
}

variable "glue_role_arn" {
  description = "ARN del IAM Role que Glue va a usar para ejecutarse"
  type        = string
}