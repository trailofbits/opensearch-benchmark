resource "aws_instance" "target-cluster" {
  ami             = var.ami_id
  instance_type   = var.instance_type
  key_name        = var.ssh_key_name
  security_groups = var.security_groups

  associate_public_ip_address = true

  subnet_id = var.subnet_id

  user_data = templatefile("${path.module}/os-cluster.yaml",
    {
      os_cluster_script = yamlencode(filebase64("${path.module}/os_cluster.sh")),
      os_password       = var.password,
      os_version        = var.os_version,
    }
  )

  private_dns_name_options {
    hostname_type = "resource-name"
  }

  tags = var.tags
}

data "aws_eip" "load-gen-eip" {
  public_ip = var.load_gen_ip
}

resource "aws_instance" "load-generation" {
  ami             = var.ami_id
  instance_type   = var.instance_type
  key_name        = var.ssh_key_name
  security_groups = var.security_groups

  # Temporarily assign public IP before EIP so that provisioner can connect to instance
  # NOTE: self.public_ip will be outdated after the aws_eip_association
  associate_public_ip_address = true

  subnet_id = var.subnet_id

  user_data = templatefile("${path.module}/os-load-generation.yaml",
    {
      os_load_script = yamlencode(filebase64("${path.module}/os_load_generation.sh")),
      os_cluster     = aws_instance.target-cluster.public_dns
      os_password    = var.password,
      os_version     = var.os_version,

      ingest_script = yamlencode(
        base64encode(templatefile("${path.module}/../../scripts/ingest.sh",
          {
            workload_params = var.workload_params,
            s3_bucket_name  = "",
          }
        ))
      ),
      benchmark_script = yamlencode(
        base64encode(templatefile("${path.module}/benchmark.sh",
          {
            workload_params = var.workload_params,
          }
        ))
      ),
    }
  )

  provisioner "remote-exec" {
    inline = [
      "echo 'Waiting for user data script to finish'",
      "cloud-init status --wait > /dev/null",
      "echo 'User data script finished'",
    ]
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

  tags = {
    Name = "load-generation"
  }

  # Ensure the load-generation instance is created after the target-cluster
  # instance so we can connect to it
  depends_on = [aws_instance.target-cluster]
}

resource "aws_eip_association" "eip_assoc" {
  instance_id   = aws_instance.load-generation.id
  allocation_id = data.aws_eip.load-gen-eip.id
}
