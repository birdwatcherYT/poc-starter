variable "project_id" {
  type = string
}

variable "account_id" {
  type    = string
  default = "cloud-build-sa"
}

variable "runtime_service_account_email" {
  type        = string
  description = "Cloud Build が Cloud Run にデプロイする際に impersonate するランタイム SA（iam.serviceAccountUser が必要）。"
}
