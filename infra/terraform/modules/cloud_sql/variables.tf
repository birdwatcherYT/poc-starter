variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "instance_name" {
  type = string
}

variable "db_name" {
  type = string
}

variable "app_user" {
  type        = string
  description = "アプリ用サービスアカウントが利用する BUILT_IN ユーザー名。"
  default     = "app_user"
}

variable "developer_group" {
  type        = string
  description = "Cloud SQL Auth Proxy 経由でアクセスを許可する IAM グループのメール（例: devs@example.com）。空文字なら IAM グループユーザーを作成しない。"
  default     = ""
}
