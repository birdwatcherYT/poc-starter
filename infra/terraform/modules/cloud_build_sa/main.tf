resource "google_service_account" "this" {
  project      = var.project_id
  account_id   = var.account_id
  display_name = "Cloud Build SA (gcloud builds submit)"
}

resource "google_project_iam_member" "roles" {
  for_each = toset([
    "roles/cloudbuild.builds.builder",
    "roles/logging.logWriter",
    "roles/artifactregistry.writer",
    "roles/run.developer",
    "roles/storage.admin",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.this.email}"
}

# Cloud Build SA が Cloud Run デプロイ時にランタイム SA を impersonate できるようにする。
resource "google_service_account_iam_member" "act_as_runtime_sa" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.runtime_service_account_email}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.this.email}"
}
