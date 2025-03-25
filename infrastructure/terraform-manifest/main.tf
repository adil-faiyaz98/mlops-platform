module "gke_cluster" {
  source = "../gke-cluster"

  project_id     = var.gcp_project_id
  cluster_name   = "mlops-cluster"
  cluster_region = var.gcp_region
}