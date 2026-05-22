terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
  }
}

locals {
  iap_enabled = var.iap_allowed_group != ""
}

# iap_enabled は GA されたが、stable provider への反映待ちのため google-beta を使う。
# 将来 provider 7.x で stable に下りたらこの provider 指定を消せる。
resource "google_cloud_run_v2_service" "this" {
  provider    = google-beta
  project     = var.project_id
  location    = var.region
  name        = var.service_name
  ingress     = "INGRESS_TRAFFIC_ALL"
  iap_enabled = local.iap_enabled

  template {
    service_account = var.service_account_email

    containers {
      image = var.image

      ports {
        container_port = 8080
      }

      env {
        name  = "DB_HOST"
        value = "/cloudsql/${var.instance_connection_name}"
      }
      env {
        name  = "DB_PORT"
        value = "5432"
      }
      env {
        name  = "DB_NAME"
        value = var.db_name
      }
      env {
        name  = "DB_USER"
        value = var.app_user
      }
      env {
        name  = "LOG_FORMAT"
        value = "json"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name = "DB_PASSWORD"
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

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }
}

data "google_project" "current" {
  project_id = var.project_id
}

# IAP の Service Agent (gcp-sa-iap) に roles/run.invoker を付与。
# これがないと IAP 経由でもリクエストが Cloud Run に届かない。
resource "google_cloud_run_v2_service_iam_member" "iap_sa_invoker" {
  count    = local.iap_enabled ? 1 : 0
  project  = var.project_id
  location = google_cloud_run_v2_service.this.location
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-iap.iam.gserviceaccount.com"
}

# IAP 経由のアクセスを許可する Google Group を指定。
resource "google_iap_web_cloud_run_service_iam_member" "iap_group_access" {
  count                  = local.iap_enabled ? 1 : 0
  project                = data.google_project.current.number
  location               = var.region
  cloud_run_service_name = google_cloud_run_v2_service.this.name
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = "group:${var.iap_allowed_group}"
}
