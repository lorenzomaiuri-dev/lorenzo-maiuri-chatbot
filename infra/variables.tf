variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Cloud Run and Artifact Registry region"
  type        = string
  default     = "europe-west3"
}

variable "firestore_location" {
  description = "Firestore location (must be a supported Firestore region)"
  type        = string
  default     = "europe-west3"
}

variable "github_org" {
  description = "GitHub organization or username owning the repo"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (without org prefix)"
  type        = string
  default     = "lorenzo-maiuri-chatbot"
}
