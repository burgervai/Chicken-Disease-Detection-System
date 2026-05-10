# Terraform configuration for Chicken Disease Classification System
# Supports GKE, Cloud SQL, GCS, and related infrastructure

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "chicken-disease-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required GCP APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "container.googleapis.com",
    "sql-component.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com"
  ])

  service            = each.key
  disable_on_destroy = false
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "${var.prefix}-vpc"
  auto_create_subnetworks = false
  description             = "Main VPC for Chicken Disease Classification"
}

# Subnet for GKE
resource "google_compute_subnetwork" "gke" {
  name          = "${var.prefix}-gke-subnet"
  network       = google_compute_network.main.id
  ip_cidr_range = var.gke_subnet_cidr
  region        = var.region

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/16"
  }

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud SQL Subnet
resource "google_compute_subnetwork" "sql" {
  name          = "${var.prefix}-sql-subnet"
  network       = google_compute_network.main.id
  ip_cidr_range = var.sql_subnet_cidr
  region        = var.region

  private_ip_google_access = true
}

# VPC Connector for Serverless
resource "google_vpc_access_connector" "serverless" {
  name          = "${var.prefix}-vpc-connector"
  region        = var.region
  network       = google_compute_network.main.name
  ip_cidr_range = "10.8.0.0/28"
  min_instances = 2
  max_instances = 10
}

# Cloud NAT for outbound traffic
resource "google_compute_router" "nat" {
  name    = "${var.prefix}-router"
  network = google_compute_network.main.id
  region  = var.region
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.prefix}-nat"
  router                             = google_compute_router.nat.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Private Service Connect for Cloud SQL
resource "google_compute_global_address" "sql_private" {
  name          = "${var.prefix}-sql-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "sql_vpc_peering" {
  service       = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.sql_private.name]
  network       = google_compute_network.main.id
}

# Cloud SQL Instance
resource "google_sql_database_instance" "mongodb" {
  name             = "${var.prefix}-mongodb"
  database_version = "POSTGRES_16"
  region           = var.region

  deletion_protection = true

  settings {
    tier              = var.db_machine_type
    region            = var.region
    availability_type = "REGIONAL"
    disk_type         = "PD_SSD"
    disk_size         = var.db_disk_size
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
      require_ssl     = true
      # Authorized networks can be added for admin access
      # authorized_networks {
      #   name    = "admin-network"
      #   value   = "10.0.0.0/8"
      # }
    }
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 14
        retention_unit   = "COUNT"
      }
    }
    maintenance_window {
      day          = 7
      hour         = 4
      update_track = "stable"
    }
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = false
    }
  }

  timeouts {
    create = "60m"
    update = "60m"
  }

  depends_on = [
    google_service_networking_connection.sql_vpc_peering
  ]
}

resource "google_sql_user" "mongodb_user" {
  name     = var.db_username
  instance = google_sql_database_instance.mongodb.name
  password = var.db_password
}

# Cloud SQL IAM
resource "google_project_iam_member" "sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# GCS Bucket for MLflow Artifacts
resource "google_storage_bucket" "mlflow_artifacts" {
  name          = "${var.project_id}-mlflow-artifacts"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  logging {
    log_bucket = google_storage_bucket.logging.name
  }

  encryption {
    default_kms_key_name = google_kms_keyring.mlops.key[0].crypto_key[0].id
  }
}

# GCS Bucket for Model Storage
resource "google_storage_bucket" "model_storage" {
  name          = "${var.project_id}-model-storage"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_keyring.mlops.key[0].crypto_key[0].id
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# GCS Bucket for Data
resource "google_storage_bucket" "data_storage" {
  name          = "${var.project_id}-data-storage"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  encryption {
    default_kms_key_name = google_kms_keyring.mlops.key[0].crypto_key[0].id
  }
}

# GCS Bucket for Logs
resource "google_storage_bucket" "logging" {
  name          = "${var.project_id}-logs"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# GCS Bucket for Backups
resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-backups"
  location      = var.region
  storage_class = "NEARLINE"

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "Delete"
    }
  }

  encryption {
    default_kms_key_name = google_kms_keyring.mlops.key[0].crypto_key[0].id
  }
}

# KMS Keyring for Encryption
resource "google_kms_key_ring" "mlops" {
  name     = "${var.prefix}-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "storage_key" {
  name            = "storage-key"
  key_ring        = google_kms_key_ring.mlops.id
  rotation_period = "7776000s"

  destruction_policy = "destroy"

  lifecycle {
    prevent_destroy = true
  }
}

# Service Account for Backend
resource "google_service_account" "backend" {
  account_id   = "${var.prefix}-backend-sa"
  display_name = "Backend Service Account"
  description  = "Service account for the Chicken Disease Classification backend"
}

# Backend Service Account Roles
resource "google_project_iam_member" "backend_roles" {
  for_each = toset([
    "roles/storage.objectViewer",
    "roles/storage.objectCreator",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter"
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# GKE Cluster
resource "google_container_cluster" "primary" {
  name     = "${var.prefix}-cluster"
  location = var.region

  deletion_protection = true

  network    = google_compute_network.main.id
  subnetwork = google_compute_subnetwork.gke.name

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = var.master_cidr
  }

  # Master authorized networks
  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "10.0.0.0/8"
      display_name = "Internal Network"
    }
  }

  # Vertical Pod Autoscaling
  vertical_pod_autoscaling {
    enabled = true
  }

  # Node configuration
  node_config {
    machine_type    = var.gke_machine_type
    image_type      = "COS_CONTAINERD"
    disk_type       = "pd-ssd"
    disk_size_gb    = 100
    service_account = google_service_account.backend.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring"
    ]
    preemptible = false
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }

  # Node pools
  node_pool {
    name               = "cpu-pool"
    initial_node_count  = 3
    autoscaling {
      min_node_count = 2
      max_node_count = 10
    }
    node_config {
      machine_type    = var.gke_machine_type
      image_type      = "COS_CONTAINERD"
      disk_size_gb    = 100
      service_account = google_service_account.backend.email
    }
    management {
      auto_repair  = true
      auto_upgrade = true
    }
  }

  node_pool {
    name               = "gpu-pool"
    initial_node_count  = 0
    autoscaling {
      min_node_count = 0
      max_node_count = 4
    }
    node_config {
      machine_type    = var.gke_gpu_machine_type
      image_type      = "COS_CONTAINERD"
      disk_size_gb    = 100
      service_account = google_service_account.backend.email
      guest_accelerators {
        gpu_type   = var.gpu_type
        gpu_count  = var.gpu_count
      }
    }
    management {
      auto_repair  = true
      auto_upgrade = true
    }
  }

  # Monitoring and logging
  monitoring_service = "monitoring.googleapis.com"
  logging_service    = "logging.googleapis.com"

  # Binary authorization
  binary_authorization {
    enabled = true
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }

  # Database encryption
  database_encryption {
    key_name = google_kms_crypto_key.storage_key.id
    state    = "ENCRYPTED"
  }

  timeouts {
    create = "60m"
    update = "60m"
  }
}

# Get GKE credentials
resource "null_resource" "get_credentials" {
  provisioner "local-exec" {
    command = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${var.region} --project ${var.project_id}"
  }

  depends_on = [google_container_cluster.primary]
}

# Workload Identity for Backend
resource "google_service_account" "k8s_backend" {
  account_id   = "${var.prefix}-k8s-backend"
  display_name = "Kubernetes Backend Service Account"
}

resource "google_project_iam_binding" "workload_identity" {
  project = var.project_id
  role    = "roles/iam.workloadIdentityUser"
  members = ["serviceAccount:${var.project_id}.svc.id.goog[chicken-disease/backend-sa]"]
}

resource "google_kms_key_ring_iam_binding" "key_iam" {
  key_ring_id = google_kms_key_ring.mlops.id
  role        = "roles/kms.cryptoKeyEncrypterDecrypter"
  members     = ["serviceAccount:${google_service_account.backend.email}"]
}

# Artifact Registry
resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = "${var.prefix}-docker"
  description   = "Docker images for Chicken Disease Classification"
  format        = "DOCKER"

  cleanup_policies {
    rules {
      action          = "DELETE"
      older_than      = "30d"
      package_version = "latest"
    }
  }
}

# Cloud Armor for WAF
resource "google_compute_security_policy" "backend_waf" {
  name        = "${var.prefix}-backend-waf"
  description = "Web Application Firewall for Backend API"

  # Rate limiting
  rate_limit_threshold {
    rate = 1000
    interval_sec = 60
  }

  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
    }
  }

  # OWASP ModSecurity Core Rule Set
  rule {
    action   = "deny(403)"
    priority = 1000
    description = "Block SQL injection"
    match {
      expr = "evaluatePreconfiguredExpr('sqli-v33-stable')"
    }
  }

  rule {
    action   = "deny(403)"
    priority = 1001
    description = "Block XSS"
    match {
      expr = "evaluatePreconfiguredExpr('xss-v33-stable')"
    }
  }

  rule {
    action   = "deny(403)"
    priority = 1002
    description = "Block remote code execution"
    match {
      expr = "evaluatePreconfiguredExpr('rce-v33-stable')"
    }
  }

  rule {
    action   = "allow"
    priority = 2147483647
    description = "Default allow"
  }
}

# Cloud CDN for Frontend
resource "google_compute_url_map" "frontend" {
  name            = "${var.prefix}-frontend-url-map"
  default_service = google_compute_backend_service.frontend.id

  host_rule {
    hosts        = ["app.${var.domain}"]
    path_matcher = "frontend-paths"
  }

  path_matcher {
    name            = "frontend-paths"
    default_service = google_compute_backend_service.frontend.id

    path_rule {
      paths   = ["/*"]
      route_action {
        cors {
          allow_origins  = ["https://app.${var.domain}"]
          allow_methods  = ["GET", "HEAD", "OPTIONS"]
          allow_headers  = ["Authorization", "Content-Type"]
          expose_headers = ["ETag"]
          max_age        = 3600
        }
      }
    }
  }
}

# Backend Services
resource "google_compute_backend_service" "frontend" {
  name        = "${var.prefix}-frontend-backend"
  description = "Backend service for frontend"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 30

  health_checks = [google_compute_health_check.frontend.id]

  security_policy = google_compute_security_policy.backend_waf.id

  # Session affinity for WebSocket support
  session_affinity = "CLIENT_IP"
  affinity_cookie_ttl_sec = 3600

  log_config {
    enable      = true
    sample_rate = 0.5
  }
}

resource "google_compute_backend_service" "backend" {
  name        = "${var.prefix}-backend-backend"
  description = "Backend service for API"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 300  # Longer for ML predictions

  health_checks = [google_compute_health_check.backend.id]

  security_policy = google_compute_security_policy.backend_waf.id

  # Enable Cloud CDN for caching
  enable_cdn = true

  # Bypass cache for API endpoints
  bypass_cache_on_request_headers {
    header_name = "Authorization"
  }

  log_config {
    enable      = true
    sample_rate = 0.5
  }
}

# Health Checks
resource "google_compute_health_check" "frontend" {
  name               = "${var.prefix}-frontend-health"
  check_interval_sec = 10
  timeout_sec        = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3

  https_health_check {
    port = 443
    request_path = "/"
  }
}

resource "google_compute_health_check" "backend" {
  name               = "${var.prefix}-backend-health"
  check_interval_sec = 10
  timeout_sec        = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3

  http_health_check {
    port         = 8000
    request_path = "/health"
  }
}

# Global IP
resource "google_compute_global_address" "frontend" {
  name         = "${var.prefix}-frontend-ip"
  ip_version   = "IPV4"
  address_type = "EXTERNAL"
}

resource "google_compute_global_address" "backend" {
  name         = "${var.prefix}-backend-ip"
  ip_version   = "IPV4"
  address_type = "EXTERNAL"
}

# HTTPS Redirect
resource "google_compute_url_map" "https_redirect" {
  name = "${var.prefix}-https-redirect"

  default_url_redirect {
    https_redirect = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_https_proxy" "https_redirect" {
  name     = "${var.prefix}-https-redirect-proxy"
  url_map  = google_compute_url_map.https_redirect.id
}

resource "google_compute_global_forwarding_rule" "https_redirect" {
  name       = "${var.prefix}-https-redirect-rule"
  target     = google_compute_target_https_proxy.https_redirect.id
  port_range = "443"
}

# Load Balancer for Frontend
resource "google_compute_target_https_proxy" "frontend" {
  name            = "${var.prefix}-frontend-proxy"
  url_map         = google_compute_url_map.frontend.id
  ssl_certificates = [google_compute_managed_ssl_certificate.frontend.id]
}

resource "google_compute_global_forwarding_rule" "frontend_https" {
  name       = "${var.prefix}-frontend-https"
  target     = google_compute_target_https_proxy.frontend.id
  port_range = "443"
  ip_address = google_compute_global_address.frontend.id
}

resource "google_compute_global_forwarding_rule" "frontend_http" {
  name       = "${var.prefix}-frontend-http"
  target     = google_compute_target_https_proxy.https_redirect.id
  port_range = "80"
  ip_address = google_compute_global_address.frontend.id
}

# Managed SSL Certificates
resource "google_compute_managed_ssl_certificate" "frontend" {
  name = "${var.prefix}-frontend-cert"

  managed {
    domains = ["app.${var.domain}"]
  }
}

resource "google_compute_managed_ssl_certificate" "backend" {
  name = "${var.prefix}-backend-cert"

  managed {
    domains = ["api.${var.domain}"]
  }
}

# Load Balancer for Backend API
resource "google_compute_url_map" "backend" {
  name            = "${var.prefix}-backend-url-map"
  default_service = google_compute_backend_service.backend.id

  host_rule {
    hosts        = ["api.${var.domain}"]
    path_matcher = "backend-paths"
  }

  path_matcher {
    name            = "backend-paths"
    default_service = google_compute_backend_service.backend.id
  }
}

resource "google_compute_target_https_proxy" "backend" {
  name            = "${var.prefix}-backend-proxy"
  url_map         = google_compute_url_map.backend.id
  ssl_certificates = [google_compute_managed_ssl_certificate.backend.id]
}

resource "google_compute_global_forwarding_rule" "backend_https" {
  name       = "${var.prefix}-backend-https"
  target     = google_compute_target_https_proxy.backend.id
  port_range = "443"
  ip_address = google_compute_global_address.backend.id
}

# Cloud Monitoring Dashboard
resource "google_monitoring_dashboard" "mlops" {
  dashboard_json = templatefile("${path.module}/templates/dashboard.json.tftpl", {
    project_id = var.project_id
    prefix     = var.prefix
  })
}

# Cloud Armor for Frontend
resource "google_compute_security_policy" "frontend_waf" {
  name        = "${var.prefix}-frontend-waf"
  description = "WAF for frontend static site"

  # Rate limiting
  rate_limit_threshold {
    rate = 10000
    interval_sec = 60
  }

  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
    }
  }
}

# Outputs
output "project_id" {
  value = var.project_id
}

output "region" {
  value = var.region
}

output "gke_cluster_name" {
  value = google_container_cluster.primary.name
}

output "gke_cluster_endpoint" {
  value = google_container_cluster.primary.endpoint
}

output "gke_cluster_ca_certificate" {
  value     = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive = true
}

output "sql_instance_connection_name" {
  value = google_sql_database_instance.mongodb.connection_name
}

output "storage_bucket_mlflow" {
  value = google_storage_bucket.mlflow_artifacts.name
}

output "storage_bucket_models" {
  value = google_storage_bucket.model_storage.name
}

output "artifact_registry" {
  value = google_artifact_registry_repository.docker.id
}

output "frontend_ip" {
  value = google_compute_global_address.frontend.address
}

output "backend_ip" {
  value = google_compute_global_address.backend.address
}

output "backend_service_account" {
  value = google_service_account.backend.email
}

output "artifact_registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}