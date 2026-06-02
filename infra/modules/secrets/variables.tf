variable "project_id" { type = string }

variable "cloudrun_service_account_email" {
  type        = string
  description = "Email of the Cloud Run SA that needs secretAccessor on all secrets"
}
