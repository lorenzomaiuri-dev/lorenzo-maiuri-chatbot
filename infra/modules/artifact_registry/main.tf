resource "google_artifact_registry_repository" "backend" {
  repository_id = "lorenzobot"
  format        = "DOCKER"
  location      = var.region
  project       = var.project_id
  description   = "Docker images for lorenzobot backend"

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "delete-old-versions"
    action = "DELETE"
    condition {
      tag_state = "ANY"
    }
  }

  cleanup_policies {
    id     = "keep-latest-image"
    action = "KEEP"
    most_recent_versions {
      keep_count = 1
    }
  }
}