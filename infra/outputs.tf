output "cloud_run_url" {
  description = "Public URL of the Cloud Run service"
  value       = module.cloudrun.service_url
}

output "artifact_registry_repo" {
  description = "Full Artifact Registry repo path for Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${module.artifact_registry.repository_id}"
}

output "wif_provider" {
  description = "WIF provider resource name — set as GitHub Actions variable WIF_PROVIDER"
  value       = module.wif.provider_name
}

output "deploy_service_account" {
  description = "Deploy SA email — set as GitHub Actions variable DEPLOY_SERVICE_ACCOUNT"
  value       = module.wif.deploy_service_account_email
}

output "cloudrun_service_account" {
  description = "Cloud Run runtime SA email — set as GitHub Actions variable CLOUDRUN_SERVICE_ACCOUNT"
  value       = google_service_account.cloudrun.email
}

