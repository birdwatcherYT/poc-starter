variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "job_name" {
  type    = string
  default = "migrate-job"
}

variable "image" {
  type        = string
  description = "マイグレーション用コンテナイメージ（database/migrate.Dockerfile からビルド）。"
}

variable "service_account_email" {
  type = string
}

variable "instance_connection_name" {
  type = string
}

variable "db_name" {
  type = string
}

variable "app_user" {
  type = string
}

variable "app_user_password_secret_id" {
  type = string
}
