variable "project_id" {
  type = string
}

variable "services" {
  type = list(string)
  default = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "iap.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
  ]
}
