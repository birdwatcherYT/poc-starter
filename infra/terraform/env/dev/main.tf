locals {
  repo_url      = module.artifact_registry.repository_url
  api_image     = "${local.repo_url}/api:${var.image_tag}"
  migrate_image = "${local.repo_url}/migrate:${var.image_tag}"
}

module "project_services" {
  source     = "../../modules/project_services"
  project_id = var.project_id
}

module "artifact_registry" {
  source     = "../../modules/artifact_registry"
  project_id = var.project_id
  region     = var.region

  depends_on = [module.project_services]
}

module "cloud_sql" {
  source          = "../../modules/cloud_sql"
  project_id      = var.project_id
  region          = var.region
  instance_name   = var.instance_name
  db_name         = var.db_name
  developer_group = var.developer_group

  depends_on = [module.project_services]
}

resource "google_service_account" "api" {
  project      = var.project_id
  account_id   = "${var.service_name}-sa"
  display_name = "PoC Starter API service account"
}

resource "google_project_iam_member" "api_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_secret_manager_secret_iam_member" "api_password_accessor" {
  project   = var.project_id
  secret_id = module.cloud_sql.app_user_password_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

module "cloud_run" {
  source                      = "../../modules/cloud_run"
  project_id                  = var.project_id
  region                      = var.region
  service_name                = var.service_name
  image                       = local.api_image
  service_account_email       = google_service_account.api.email
  instance_connection_name    = module.cloud_sql.instance_connection_name
  db_name                     = module.cloud_sql.db_name
  app_user                    = module.cloud_sql.app_user
  app_user_password_secret_id = module.cloud_sql.app_user_password_secret_id
  access_mode                 = var.access_mode
  allowed_group               = var.allowed_group
}

module "cloud_build_sa" {
  source                        = "../../modules/cloud_build_sa"
  project_id                    = var.project_id
  runtime_service_account_email = google_service_account.api.email

  depends_on = [module.project_services]
}

module "migrate_job" {
  source                      = "../../modules/cloud_run_job_migrate"
  project_id                  = var.project_id
  region                      = var.region
  image                       = local.migrate_image
  service_account_email       = google_service_account.api.email
  instance_connection_name    = module.cloud_sql.instance_connection_name
  db_name                     = module.cloud_sql.db_name
  app_user                    = module.cloud_sql.app_user
  app_user_password_secret_id = module.cloud_sql.app_user_password_secret_id
}
