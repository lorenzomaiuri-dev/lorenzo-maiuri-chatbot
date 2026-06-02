variable "project_id" { type = string }
variable "region" { type = string }

variable "service_account_email" {
  type        = string
  description = "Email of the pre-created Cloud Run service account"
}

variable "service_name" {
  type    = string
  default = "lorenzobot-backend"
}

variable "image" {
  type        = string
  description = "Full Docker image URI (e.g. europe-west8-docker.pkg.dev/PROJECT/lorenzobot/backend:latest)"
}

variable "gemini_model" {
  type    = string
  default = "gemini-3.5-flash"
}

variable "calcom_event_slug" {
  type    = string
  default = "30min"
}

variable "cpu" {
  type    = string
  default = "1"
}

variable "memory" {
  type    = string
  default = "512Mi"
}

variable "max_instances" {
  type    = number
  default = 3
}

variable "secret_env_vars" {
  type = list(object({
    env_name  = string
    secret_id = string
  }))
  description = "Secrets to mount as env vars from Secret Manager"
  default     = []
}

# Dependency token — pass module.secrets to ensure secrets exist before Cloud Run deploys
variable "secrets_ready" {
  type    = any
  default = null
}
