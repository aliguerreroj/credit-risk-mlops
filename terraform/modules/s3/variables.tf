variable "bucket_name" {
  description = "Nombre del bucket S3 para el proyecto"
  type        = string
}

variable "environment" {
  description = "Ambiente (dev, prod)"
  type        = string
  default     = "dev"
}