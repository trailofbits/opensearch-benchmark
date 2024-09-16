resource "aws_instance" "target-cluster" {
  ami             = var.ami_id
  instance_type   = var.instance_type
  key_name        = var.ssh_key_name
  security_groups = var.security_groups

  associate_public_ip_address = true

  subnet_id = var.subnet_id

  user_data = templatefile("${path.module}/../../scripts/init.sh", {
    hostname = "os-cluster",
    args     = "${var.password} ${var.os_version}",
  })

  provisioner "file" {
    source      = "${path.module}/os_cluster.sh"
    destination = "/home/ubuntu/init_machine.sh"
  }

  connection {
    type        = "ssh"
    user        = "ubuntu"
    private_key = file(var.ssh_priv_key)
    host        = self.public_ip
  }

  private_dns_name_options {
    hostname_type = "resource-name"
  }

  tags = var.tags
}

resource "aws_instance" "load-generation" {
  ami             = var.ami_id
  instance_type   = var.instance_type
  key_name        = var.ssh_key_name
  security_groups = var.security_groups

  associate_public_ip_address = true

  subnet_id = var.subnet_id

  user_data = templatefile("${path.module}/../../scripts/init.sh", {
    hostname = "load-generation",
    args     = "https://${aws_instance.target-cluster.public_dns}:9200 ${var.password} ${var.os_version}",
  })

  provisioner "file" {
    source      = "${path.module}/os_load_generation.sh"
    destination = "/home/ubuntu/init_machine.sh"
  }

  provisioner "file" {
    source      = "${path.module}/ingest.sh"
    destination = "/home/ubuntu/ingest.sh"
  }

  provisioner "file" {
    source      = "${path.module}/benchmark.sh"
    destination = "/home/ubuntu/benchmark.sh"
  }

  connection {
    type        = "ssh"
    user        = "ubuntu"
    private_key = file(var.ssh_priv_key)
    host        = self.public_ip
  }

  provisioner "remote-exec" {
    inline = [
      "echo 'Waiting for user data script to finish'",
      "cloud-init status --wait > /dev/null"
    ]
  }

  private_dns_name_options {
    hostname_type = "resource-name"
  }

  tags = {
    Name = "load-generation"
  }

  # Ensure the load-generation instance is created after the target-cluster
  # instance so we can connect to it
  depends_on = [aws_instance.target-cluster]
}
