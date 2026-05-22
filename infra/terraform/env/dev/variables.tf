variable "project_id" {
  type        = string
  description = "dev 環境の GCP プロジェクト ID。"
}

variable "region" {
  type    = string
  default = "asia-northeast1"
}

variable "service_name" {
  type    = string
  default = "poc-starter-api"
}

variable "instance_name" {
  type    = string
  default = "poc-starter-db"
}

variable "db_name" {
  type    = string
  default = "poc"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "developer_group" {
  type        = string
  default     = ""
  description = "開発者の Cloud SQL アクセス用 IAM グループメール（例: devs@example.com）。空文字でスキップ。"
}

variable "access_mode" {
  type        = string
  default     = "browser"
  description = "API のアクセスモード。'browser' = IAP 経由でブラウザアクセス（ターミナルから curl は追加セットアップ要）、'terminal' = IAP を使わず Group に run.invoker を付与（ID token で curl 可、ブラウザ認証画面なし）。"
}

variable "allowed_group" {
  type        = string
  default     = ""
  description = "API へのアクセスを許可する Google Group（例: api-users@example.com）。空文字でスキップ（外部からアクセス不可になる）。access_mode に応じて IAP 経由 / Cloud Run invoker として付与される。"
}
