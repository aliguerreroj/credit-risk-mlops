variable "environment" {
  description = "Ambiente (dev, prod)"
  type        = string
  default     = "dev"
}

variable "bucket_arn" {
  description = "ARN del bucket S3 al que Glue necesita acceso"
  type        = string
}