output "provider_name" {
  value = google_iam_workload_identity_pool_provider.github.name
}

output "deploy_service_account_email" {
  value = google_service_account.deploy.email
}

output "pool_name" {
  description = "WIF pool resource name — used to build principalSet member strings for additional repo bindings."
  value       = google_iam_workload_identity_pool.github.name
}

output "deploy_service_account_name" {
  description = "Full resource name of the deploy SA — used as service_account_id in IAM bindings."
  value       = google_service_account.deploy.name
}
