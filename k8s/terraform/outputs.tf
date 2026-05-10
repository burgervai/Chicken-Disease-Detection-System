# Terraform Outputs for Chicken Disease Classification

output "cluster_credentials_command" {
  description = "Command to get GKE credentials"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${var.region} --project ${var.project_id}"
}

output "artifact_registry_full_name" {
  description = "Full Artifact Registry name"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "sql_private_ip" {
  description = "Private IP of Cloud SQL instance"
  value       = google_sql_database_instance.mongodb.first_ip_address
}

output "vpc_network_name" {
  description = "VPC Network name"
  value       = google_compute_network.main.name
}

output "vpc_connector_id" {
  description = "VPC Connector ID for serverless"
  value       = google_vpc_access_connector.serverless.id
}

output "kms_key_id" {
  description = "KMS Key ID for encryption"
  value       = google_kms_crypto_key.storage_key.id
}

output "workload_identity_service_account" {
  description = "Workload Identity Service Account email"
  value       = google_service_account.k8s_backend.email
}

output "security_policy_backend_id" {
  description = "Backend Security Policy ID"
  value       = google_compute_security_policy.backend_waf.id
}

output "security_policy_frontend_id" {
  description = "Frontend Security Policy ID"
  value       = google_compute_security_policy.frontend_waf.id
}

output "dashboard_url" {
  description = "URL to the monitoring dashboard"
  value       = "https://console.cloud.google.com/monitoring/dashboards?project=${var.project_id}"
}

output "gke_cluster_status" {
  description = "GKE Cluster status"
  value       = google_container_cluster.primary.status
}