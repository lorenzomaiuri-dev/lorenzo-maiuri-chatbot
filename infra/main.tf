terraform {
  required_version = ">= 1.8"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  backend "gcs" {
    # Bucket must be created manually before first `terraform init`:
    #   gsutil mb -p PROJECT_ID -l REGION gs://lorenzobot-tf-state
    #   gsutil versioning set on gs://lorenzobot-tf-state
    bucket = "lorenzobot-tf-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Enable required APIs ───────────────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "firestore.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

# ── Cloud Run service account (created here to break secrets↔cloudrun cycle) ──

resource "google_service_account" "cloudrun" {
  project      = var.project_id
  account_id   = "lorenzobot-cloudrun-sa"
  display_name = "LorenzoBot Cloud Run SA"

  depends_on = [google_project_service.apis]
}

# ── Modules ───────────────────────────────────────────────────────────────────

module "artifact_registry" {
  source     = "./modules/artifact_registry"
  project_id = var.project_id
  region     = var.region

  depends_on = [google_project_service.apis]
}

module "firestore" {
  source     = "./modules/firestore"
  project_id = var.project_id
  location   = var.firestore_location

  depends_on = [google_project_service.apis]
}

module "wif" {
  source      = "./modules/wif"
  project_id  = var.project_id
  github_org  = var.github_org
  github_repo = var.github_repo

  depends_on = [google_project_service.apis]
}

# Secrets are created + IAM bindings applied before Cloud Run deploys
module "secrets" {
  source                         = "./modules/secrets"
  project_id                     = var.project_id
  cloudrun_service_account_email = google_service_account.cloudrun.email

  depends_on = [google_service_account.cloudrun, google_project_service.apis]
}

module "cloudrun" {
  source                = "./modules/cloudrun"
  project_id            = var.project_id
  region                = var.region
  service_account_email = google_service_account.cloudrun.email
  image                 = "${var.region}-docker.pkg.dev/${var.project_id}/${module.artifact_registry.repository_id}/backend:latest"
  secrets_ready         = module.secrets.ready

  secret_env_vars = [
    { env_name = "GEMINI_API_KEY", secret_id = "GEMINI_API_KEY" },
    { env_name = "API_KEY", secret_id = "API_KEY" },
    { env_name = "PHOENIX_CLIENT_HEADERS", secret_id = "PHOENIX_CLIENT_HEADERS" },
    { env_name = "CALCOM_API_KEY", secret_id = "CALCOM_API_KEY" },
    { env_name = "CALCOM_USERNAME", secret_id = "CALCOM_USERNAME" },
  ]

  depends_on = [module.artifact_registry, module.secrets]
}

# Allow the frontend repo to authenticate as the same deploy SA.
# The WIF pool already exists; this adds a second repo binding without touching the module.
resource "google_service_account_iam_member" "wif_binding_website" {
  service_account_id = module.wif.deploy_service_account_name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${module.wif.pool_name}/attribute.repository/${var.github_org}/lorenzo-maiuri-website"

  depends_on = [module.wif]
}

# Allow deploy SA (GitHub Actions) to impersonate the Cloud Run SA
resource "google_service_account_iam_member" "deploy_impersonate_cloudrun" {
  service_account_id = google_service_account.cloudrun.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${module.wif.deploy_service_account_email}"
}
