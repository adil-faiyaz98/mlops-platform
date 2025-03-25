provider "helm" {
  kubernetes {
    config_path = var.kubernetes_config_path
  }
}

# Create namespace for monitoring stack
resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
    
    labels = {
      name = "monitoring"
      managed-by = "terraform"
    }
  }
}

# Deploy Prometheus using Helm
resource "helm_release" "prometheus" {
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = kubernetes_namespace.monitoring.metadata[0].name
  version    = "45.7.1"  # Specify a version for reproducibility
  
  # Custom values
  values = [
    file("${path.module}/monitoring/prometheus-values.yaml")
  ]
  
  set {
    name  = "prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues"
    value = "false"
  }
  
  set {
    name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
    value = "false"
  }
  
  set {
    name  = "grafana.adminPassword"
    value = var.grafana_admin_password
  }
  
  depends_on = [kubernetes_namespace.monitoring]
}

# Deploy OpenTelemetry Collector
resource "helm_release" "otel_collector" {
  name       = "otel-collector"
  repository = "https://open-telemetry.github.io/opentelemetry-helm-charts"
  chart      = "opentelemetry-collector"
  namespace  = kubernetes_namespace.monitoring.metadata[0].name
  version    = "0.49.0"
  
  values = [
    file("${path.module}/monitoring/otel-collector-values.yaml")
  ]
  
  set {
    name  = "mode"
    value = "deployment"
  }
  
  depends_on = [kubernetes_namespace.monitoring, helm_release.prometheus]
}

# Deploy Elasticsearch
resource "helm_release" "elasticsearch" {
  name       = "elasticsearch"
  repository = "https://helm.elastic.co"
  chart      = "elasticsearch"
  namespace  = kubernetes_namespace.monitoring.metadata[0].name
  version    = "7.17.3"
  
  values = [
    file("${path.module}/monitoring/elasticsearch-values.yaml")
  ]
  
  depends_on = [kubernetes_namespace.monitoring]
}

# Deploy Kibana
resource "helm_release" "kibana" {
  name       = "kibana"
  repository = "https://helm.elastic.co"
  chart      = "kibana"
  namespace  = kubernetes_namespace.monitoring.metadata[0].name
  version    = "7.17.3"
  
  values = [
    file("${path.module}/monitoring/kibana-values.yaml")
  ]
  
  set {
    name  = "elasticsearch.hosts"
    value = "http://elasticsearch-master:9200"
  }
  
  depends_on = [helm_release.elasticsearch]
}

# Deploy Jaeger
resource "helm_release" "jaeger" {
  name       = "jaeger"
  repository = "https://jaegertracing.github.io/helm-charts"
  chart      = "jaeger"
  namespace  = kubernetes_namespace.monitoring.metadata[0].name
  version    = "0.67.0"
  
  values = [
    file("${path.module}/monitoring/jaeger-values.yaml")
  ]
  
  set {
    name  = "provisionDataStore.cassandra"
    value = "false"
  }
  
  set {
    name  = "storage.type"
    value = "elasticsearch"
  }
  
  set {
    name  = "storage.elasticsearch.host"
    value = "elasticsearch-master"
  }
  
  depends_on = [helm_release.elasticsearch]
}

# Create ConfigMaps for Grafana dashboards
resource "kubernetes_config_map" "grafana_dashboards" {
  metadata {
    name      = "grafana-dashboards"
    namespace = kubernetes_namespace.monitoring.metadata[0].name
    
    labels = {
      grafana_dashboard = "1"
    }
  }
  
  data = {
    "api-performance.json" = file("${path.module}/monitoring/dashboards/api-performance.json")
    "model-metrics.json"   = file("${path.module}/monitoring/dashboards/model-metrics.json")
    "system-metrics.json"  = file("${path.module}/monitoring/dashboards/system-metrics.json")
    "platform-slo.json"    = file("${path.module}/monitoring/dashboards/platform-slo.json")
  }
  
  depends_on = [helm_release.prometheus]
}