resource "google_cloud_run_v2_job" "this" {
  project             = var.project_id
  location            = var.region
  name                = var.job_name
  deletion_protection = false

  template {
    template {
      service_account = var.service_account_email

      containers {
        image = var.image

        env {
          name  = "DB_URL"
          value = "postgres://${var.app_user}@/${var.db_name}?host=/cloudsql/${var.instance_connection_name}"
        }
        env {
          name = "PGPASSWORD"
          value_source {
            secret_key_ref {
              secret  = var.app_user_password_secret_id
              version = "latest"
            }
          }
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [var.instance_connection_name]
        }
      }

      max_retries = 1
    }
  }
}
