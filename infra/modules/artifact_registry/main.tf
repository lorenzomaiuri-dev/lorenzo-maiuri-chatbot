resource "google_artifact_registry_repository" "backend" {
  repository_id = "lorenzobot"
  format        = "DOCKER"
  location      = var.region
  project       = var.project_id
  description   = "Docker images for lorenzobot backend"
}
