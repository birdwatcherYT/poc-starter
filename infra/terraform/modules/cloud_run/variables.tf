variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "service_name" {
  type = string
}

variable "image" {
  type = string
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

variable "iap_allowed_group" {
  type        = string
  description = "IAP 経由のアクセスを許可する Google Group（例: api-users@example.com）。空文字なら IAP IAM バインディングをスキップ。"
  default     = ""
}
