# /infrastructure/modules/cloud-run/main.tf

resource "google_cloud_run_service" "default" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    spec {
      containers {
        image = var.image
        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }
      }
    }
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.min_instances
        "autoscaling.knative.dev/maxScale" = var.max_instances
        "run.googleapis.com/ingress" = "all"
      }
    }
  }

  traffic {
    percent     = 100
    type        = "REVISION"
    revision_name = google_cloud_run_service.default.name
  }
  autogenerate_revision_name = true
}

resource "google_cloud_run_service_iam_binding" "allUsers" {
  location = var.region
  member   = "allUsers"
  project  = var.project_id
  role     = "roles/run.invoker"
  service  = google_cloud_run_service.default.name
}

output "service_url" {
  value = google_cloud_run_service.default.status[0].url
}