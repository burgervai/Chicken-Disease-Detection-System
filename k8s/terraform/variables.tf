# Terraform Variables for Chicken Disease Classification

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "prefix" {
  description = "Resource prefix"
  type        = string
  default     = "chicken-disease"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "domain" {
  description = "Domain for the application"
  type        = string
  default     = "chickendisease.com"
}

variable "db_username" {
  description = "Database username"
  type        = string
  sensitive   = true
  default     = "chicken_user"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_machine_type" {
  description = "Cloud SQL machine type"
  type        = string
  default     = "db-n1-standard-2"
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 100
}

variable "gke_machine_type" {
  description = "GKE node machine type"
  type        = string
  default     = "n2-standard-4"
}

variable "gke_gpu_machine_type" {
  description = "GKE GPU node machine type"
  type        = string
  default     = "n1-standard-4"
}

variable "gpu_type" {
  description = "GPU type"
  type        = string
  default     = "nvidia-tesla-t4"
}

variable "gpu_count" {
  description = "Number of GPUs per node"
  type        = number
  default     = 1
}

variable "gke_subnet_cidr" {
  description = "GKE subnet CIDR"
  type        = string
  default     = "10.0.0.0/24"
}

variable "sql_subnet_cidr" {
  description = "SQL subnet CIDR"
  type        = string
  default     = "10.1.0.0/24"
}

variable "master_cidr" {
  description = "Master CIDR block"
  type        = string
  default     = "172.16.0.0/28"
}