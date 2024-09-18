output "os-cluster-ip" {
  value = aws_instance.target-cluster.public_dns
}

output "load-generation-ip" {
  value = aws_instance.load-generation.public_dns
}
