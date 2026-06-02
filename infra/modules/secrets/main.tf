# Secret Manager secrets for LorenzoBot.
# Secret values are NOT managed by Terraform — create them manually:
#   gcloud secrets versions add SECRET_NAME --data-file=-

locals {
  secret_names = [
    "GEMINI_API_KEY",
    "API_KEY",
    "PHOENIX_CLIENT_HEADERS",
    "CALCOM_API_KEY",
    "CALCOM_USERNAME",
  ]
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(local.secret_names)
  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }
}

# Grant the Cloud Run SA read access to all secrets
resource "google_secret_manager_secret_iam_member" "cloudrun_accessor" {
  for_each  = toset(local.secret_names)
  project   = var.project_id
  secret_id = google_secret_manager_secret.secrets[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.cloudrun_service_account_email}"
}
