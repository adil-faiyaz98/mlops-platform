resource "google_project_service" "monitoring" {
  service            = "monitoring.googleapis.com"
  disable_on_destroy = false
}
resource "google_project_service_identity" "gcp_sa" {
  provider = google
  service = "monitoring.googleapis.com"
  project = var.project_id
}

resource "google_project_iam_member" "service_identity" {
  project = var.project_id
  role = "roles/monitoring.metricWriter"
  member = "serviceAccount:${google_project_service_identity.gcp_sa.email}"
}

output "service_id" {
  value = google_project_service_identity.gcp_sa.email
  description = "Access For all function"
}