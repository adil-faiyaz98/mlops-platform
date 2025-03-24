# /infrastructure/main.tf
#Get all to the latest verison.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
  required_version = ">= 0.14.0"
}

provider "google" {
  project = var.gcp_project
  region  = var.region
}

# Cloud Run Function Name for the Model Endpoint
resource "google_cloudfunctions2_function" "function" {
  name = "gcpFunctionAPI" #Name it
  location = var.region
  build_config {
    runtime = "python39" #Set runtime
    entry_point = "predict" # Point here where it all starts.
    source {
      storage_source {
        bucket = var.gcs_bucket #Bucket where to get the code
        object = "version_code.zip" # what code we get.
      }
    }
    environment_variables = { # Important to hide keys or access here.
      API_URL = "TheRightAPI" #Set the data
      BUCKET_NAME = var.gcs_bucket
    }
  }
  service_config {
    max_instance_count = 10
    min_instance_count = 1

    available_memory  = "512M"
    timeout_seconds = 180
  }
}
  output "vertex_ai_endpoint" {
  value = google_cloudfunctions2_function.function.name
}