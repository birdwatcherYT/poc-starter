output "service_uri" {
  value = module.cloud_run.service_uri
}

output "instance_connection_name" {
  value = module.cloud_sql.instance_connection_name
}

output "app_user_password_secret_id" {
  value = module.cloud_sql.app_user_password_secret_id
}

output "app_user" {
  value = module.cloud_sql.app_user
}

output "db_name" {
  value = module.cloud_sql.db_name
}

output "artifact_registry_url" {
  value = module.artifact_registry.repository_url
}

output "migrate_job_name" {
  value = module.migrate_job.job_name
}

output "cloud_build_sa_email" {
  value = module.cloud_build_sa.email
}
