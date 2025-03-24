# /infrastructure/modules/gke-cluster/variables.tf

variable "project_id" {
  type = string
  description = "GCP project ID"
}

variable "cluster_name" {
  type = string
  description = "Name of the GKE cluster"
}

variable "region" {
  type = string
  description = "GCP region"
}

variable "num_nodes" {
  type = number
  description = "Initial number of nodes"
  default = 1
}

variable "min_nodes" {
  type = number
  description = "Minimum number of nodes for autoscaling"
  default = 1
}

variable "max_nodes" {
  type = number
  description = "Maximum number of nodes for autoscaling"
  default = 3
}

variable "machine_type" {
  type = string
  description = "Machine type for the nodes"
  default = "n1-standard-1"
}

variable "disk_size_gb" {
  type = number
  description = "Disk size for the nodes"
  default = 100
}