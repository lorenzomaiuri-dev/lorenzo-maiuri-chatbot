# Workload Identity Federation for GitHub Actions.
# Allows GitHub Actions to authenticate to GCP without service account keys.

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions Pool"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Actions OIDC Provider"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  # Restrict to your GitHub org only
  attribute_condition = "assertion.repository_owner == '${var.github_org}'"
}

# Service account used by GitHub Actions (CI/CD + Terraform)
resource "google_service_account" "deploy" {
  project      = var.project_id
  account_id   = "github-actions-sa"
  display_name = "GitHub Actions Deploy SA"
}

# Allow the GitHub repo to impersonate this SA
resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_org}/${var.github_repo}"

  depends_on = [google_project_iam_member.deploy_roles]
}

# IAM roles for the deploy SA
resource "google_project_iam_member" "deploy_roles" {
  for_each = toset([
    "roles/run.admin",                       # deploy Cloud Run
    "roles/artifactregistry.writer",         # push Docker images
    "roles/secretmanager.admin",             # manage secrets (Terraform)
    "roles/iam.serviceAccountUser",          # use Cloud Run SA
    "roles/editor",                          # broad access for Terraform
    "roles/resourcemanager.projectIamAdmin", # manage project IAM (for WIF setup)
    "roles/iam.serviceAccountAdmin",         # manage IAM
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.deploy.email}"
}
