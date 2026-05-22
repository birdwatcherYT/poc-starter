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

variable "access_mode" {
  type        = string
  description = "アクセスモード。'browser' = IAP 経由のブラウザアクセス、'terminal' = ID token によるターミナル/curl アクセス。"
  default     = "browser"

  validation {
    condition     = contains(["browser", "terminal"], var.access_mode)
    error_message = "access_mode は 'browser' または 'terminal' のいずれかでなければならない。"
  }
}

variable "allowed_group" {
  type        = string
  description = "アクセスを許可する Google Group（例: api-users@example.com）。空文字ならアクセス権バインディングをスキップ（外部からアクセス不可になる）。browser モードでは IAP 経由、terminal モードでは Cloud Run invoker として付与される。"
  default     = ""
}
