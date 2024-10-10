output "target-cluster-ip" {
  value = var.target_cluster_type == "ElasticSearch" ? module.es-cluster[0].es-cluster-ip : module.os-cluster[0].os-cluster-ip
}

output "load-generation-ip" {
  value = var.target_cluster_type == "ElasticSearch" ? module.es-cluster[0].load-generation-ip : module.os-cluster[0].load-generation-ip
}

output "cluster-password" {
  value     = random_password.cluster-password.result
  sensitive = true
}

output "snapshot-version" {
  value = data.external.latest_snapshot_version.result.latest_version
}
