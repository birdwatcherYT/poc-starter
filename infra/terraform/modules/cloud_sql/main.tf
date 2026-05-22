resource "google_sql_database_instance" "this" {
  project          = var.project_id
  region           = var.region
  name             = var.instance_name
  database_version = "POSTGRES_16"

  settings {
    edition           = "ENTERPRISE"
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_autoresize   = true

    backup_configuration {
      enabled = false
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "this" {
  project  = var.project_id
  instance = google_sql_database_instance.this.name
  name     = var.db_name
}

resource "random_password" "app_user" {
  length  = 32
  special = true
}

resource "google_secret_manager_secret" "app_user_password" {
  project   = var.project_id
  secret_id = "${var.instance_name}-app-user-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "app_user_password" {
  secret      = google_secret_manager_secret.app_user_password.id
  secret_data = random_password.app_user.result
}

resource "google_sql_user" "app_user" {
  project  = var.project_id
  instance = google_sql_database_instance.this.name
  name     = var.app_user
  type     = "BUILT_IN"
  password = random_password.app_user.result
}

resource "google_sql_user" "developer_group" {
  count    = var.developer_group != "" ? 1 : 0
  project  = var.project_id
  instance = google_sql_database_instance.this.name
  name     = var.developer_group
  type     = "CLOUD_IAM_GROUP"
}

resource "google_project_iam_member" "developer_group_roles" {
  for_each = var.developer_group != "" ? toset([
    "roles/cloudsql.instanceUser",
    "roles/cloudsql.client",
    "roles/cloudsql.studioUser",
  ]) : []
  project = var.project_id
  role    = each.value
  member  = "group:${var.developer_group}"
}
