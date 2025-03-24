# /infrastructure/modules/cloud-run/outputs.tf

output "service_url" {
  value = google_cloud_run_service.default.status[0].url
  description = "URL to access the deployed Cloud Run service"
}