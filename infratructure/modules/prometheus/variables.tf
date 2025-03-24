# /infrastructure/modules/prometheus/variables.tf
variable "project_id" {
  type = string
  description = "The project ID to deploy to"
}

variable "location" {
  type = string
  description = "location for cloud service"
}