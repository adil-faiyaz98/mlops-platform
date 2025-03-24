# /infrastructure/modules/gke-cluster/outputs.tf

output "cluster_name" {
  value = google_container_cluster.primary.name
  description = "Name of the GKE cluster"
}

output "cluster_endpoint" {
  value = google_container_cluster.primary.endpoint
  description = "Endpoint of the GKE cluster"
}