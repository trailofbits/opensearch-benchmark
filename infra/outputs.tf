output "target-cluster-ip" {
  value = var.target_cluster_type == "ElasticSearch" ? module.es-cluster[0].es-cluster-ip : null
}

output "load-generation-ip" {
  value = var.target_cluster_type == "ElasticSearch" ? module.es-cluster[0].load-generation-ip : null
}

output "cluster-password" {
  value     = random_password.cluster-password.result
  sensitive = true
}
