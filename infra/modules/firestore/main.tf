# Firestore Native mode database.
# If already created manually, import with:
#   terraform import module.firestore.google_firestore_database.default projects/PROJECT_ID/databases/(default)

resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.location
  type        = "FIRESTORE_NATIVE"

  # TTL policy for inactive sessions (30 days) is managed via Firestore console
  # or with google_firestore_field resource — see README.
}
