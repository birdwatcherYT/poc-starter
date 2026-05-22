output "instance_connection_name" {
  value = google_sql_database_instance.this.connection_name
}

output "app_user_password_secret_id" {
  value = google_secret_manager_secret.app_user_password.secret_id
}

output "db_name" {
  value = google_sql_database.this.name
}

output "app_user" {
  value = google_sql_user.app_user.name
}
