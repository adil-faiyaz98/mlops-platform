# infrastructure/modules/sagemaker_training_job/main.tf

resource "aws_sagemaker_training_job" "training_job" {
  training_job_name = var.training_job_name
  algorithm_specification {
    training_image   = var.training_image
    training_input_mode = "File"
  }

  input_data_config {
    channel_name = "training"
    content_type = "text/csv"
    data_type    = "S3Prefix"
    s3_data_type = "S3Prefix"
    s3_uri       = var.training_data_uri
  }

  input_data_config {
    channel_name = "validation"
    content_type = "text/csv"
    data_type    = "S3Prefix"
    s3_data_type = "S3Prefix"
    s3_uri       = var.validation_data_uri
  }

  output_data_config {
    s3_output_path = var.output_data_uri
  }

  resource_config {
    instance_count  = var.instance_count
    instance_type   = var.instance_type
    volume_size_in_gb = var.volume_size_in_gb
  }

  role_arn = var.sagemaker_role_arn

  stopping_condition {
    max_runtime_in_seconds = var.max_runtime_in_seconds
  }

  static_hyperparameters = var.static_hyperparameters

  tags = {
    Name = var.training_job_name
  }
}

output "training_job_arn" {
  value = aws_sagemaker_training_job.training_job.arn
}


module "gke" {
  source = "./modules/gke-cluster"

  project_id     = var.project_id
  cluster_name   = "${var.model_name}-gke"
  region         = var.region
  num_nodes      = 3
  min_nodes      = 1
  max_nodes      = 5 # Autoscaling
  machine_type   = "e2-medium"
  disk_size_gb   = 50
}

module "cloud_run" {
  source = "./modules/cloud_run"

  project_id    = var.project_id
  service_name  = "${var.model_name}-api"
  image         = "us-central1-docker.pkg.dev/gcp-ml-model/gcpFunctionAPI:123"  #UPDATE WITH VERSION
  region         = var.region
  min_instances      = "1" #Min
  max_instances      = "5"  # Scalbility
}

module "dataflow_load" {
  source = "./modules/prometheus"
  project_id = var.project_id
  location = var.region
}