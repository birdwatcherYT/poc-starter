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
  browser_mode    = var.access_mode == "browser"
  terminal_mode   = var.access_mode == "terminal"
  iap_enabled     = local.browser_mode && var.allowed_group != ""
  invoker_enabled = local.terminal_mode && var.allowed_group != ""
}

# iap_enabled は GA されたが、stable provider への反映待ちのため google-beta を使う。
# 将来 provider 7.x で stable に下りたらこの provider 指定を消せる。
#
# access_mode によるトレードオフ:
#   - "browser": Cloud Run IAP を有効化。ブラウザ OAuth フローで簡単に通せるが、ターミナルから curl / runner で叩くには追加の手動セットアップが必要:
#       - 素の `gcloud auth print-identity-token`（audience 未指定）は Cloud Run IAM 直向けの token になり、IAP の audience チェックで 401。
#       - IAP の Google-managed OAuth client は audience として使えない仕様。
#       - 手動で OAuth client を作り `gcloud iap settings set` で programmatic_clients allowlist に登録すれば、その client ID を audience として token を発行できる（https://cloud.google.com/iap/docs/sharing-oauth-clients 参照）。
#         ただし OAuth 同意画面の設定など Console での手動操作が必要で terraform 化困難。
#   - "terminal": IAP を外し、Google Group に直接 roles/run.invoker を付与（実験で動作確認済み）。
#       `gcloud auth print-identity-token` で取得した ID token をそのまま Authorization ヘッダに載せれば叩ける。
#       ブラウザからは認証画面が出ないため、ブラウザアクセスの用途には向かない。
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

# IAP 経由のアクセスを許可する Google Group を指定（browser モード）。
resource "google_iap_web_cloud_run_service_iam_member" "iap_group_access" {
  count                  = local.iap_enabled ? 1 : 0
  project                = data.google_project.current.number
  location               = var.region
  cloud_run_service_name = google_cloud_run_v2_service.this.name
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = "group:${var.allowed_group}"
}

# terminal モードでは IAP を介さず、Google Group に直接 roles/run.invoker を付与する。
# ID token (audience = Cloud Run URL) で叩けるようになる。
resource "google_cloud_run_v2_service_iam_member" "group_invoker" {
  count    = local.invoker_enabled ? 1 : 0
  project  = var.project_id
  location = google_cloud_run_v2_service.this.location
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "group:${var.allowed_group}"
}
