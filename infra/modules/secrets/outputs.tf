output "secret_ids" {
  value = { for k, v in google_secret_manager_secret.secrets : k => v.secret_id }
}

# Pass this to the cloudrun module's secrets_ready variable to enforce ordering
output "ready" {
  value       = google_secret_manager_secret_iam_member.cloudrun_accessor
  description = "Dependency token: secrets + IAM bindings are fully applied"
}
