# /infrastructure/modules/cloud-run/variables.tf

variable "project_id" {
  type = string
  description = "The project ID to deploy to"
}

variable "service_name" {
  type = string
  description = "Name of Cloud Run service"
}

variable "image" {
  type = string
  description = "Docker image to deploy"
}

variable "region" {
  type = string
  description = "The GCP region to deploy to"
}

variable "min_instances" {
  type = string
  description = "Minimum Instances For High Avail."
  default = "1" #Min
}

variable "max_instances" {
  type = string
  description = "Maximum Instances"
  default = "3" #Max
}