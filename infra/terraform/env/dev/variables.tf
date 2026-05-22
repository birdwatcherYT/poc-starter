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

variable "iap_allowed_group" {
  type        = string
  default     = ""
  description = "IAP 経由で API にアクセスを許可する Google Group（例: api-users@example.com）。空文字でスキップ。"
}
