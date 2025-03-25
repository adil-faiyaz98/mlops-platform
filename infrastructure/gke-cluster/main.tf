# /infrastructure/modules/gke-cluster/main.tf

resource "google_container_cluster" "primary" {
  name               = var.cluster_name
  location           = var.region
  remove_default_node_pool = true
  initial_node_count = 1

  # GKE 1.24 and later defaults to cos_containerd
  default_pod_cidr_config {
    create_range = true
    range_name   = "cluster-ip-range"
  }
}

resource "google_container_node_pool" "primary_nodes" {
  name           = "default-node-pool"
  project        = var.project_id
  location       = var.region
  cluster        = google_container_cluster.primary.name
  node_count     = var.num_nodes

  management {
    auto_upgrade  = true
    auto_repair   = true
  }

  autoscaling {
    min_node_count = var.min_nodes
    max_node_count = var.max_nodes
  }

  node_config {
    machine_type = var.machine_type
    disk_size_gb = var.disk_size_gb
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
  }
}