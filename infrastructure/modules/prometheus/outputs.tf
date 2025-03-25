# /infrastructure/modules/prometheus/outputs.tf
output "email" {
  value = google_project_service_identity.gcp_sa.email
  description = "Email to used for account"
}