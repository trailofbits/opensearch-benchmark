output "es-cluster-ip" {
  value = aws_instance.target-cluster.public_dns
}

output "load-generation-ip" {
  value = aws_eip_association.eip_assoc.public_ip
}
