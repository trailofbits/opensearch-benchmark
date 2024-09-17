resource "aws_instance" "target-cluster" {
  ami             = var.ami_id
  instance_type   = var.instance_type
  key_name        = var.ssh_key_name
  security_groups = var.security_groups

  associate_public_ip_address = true

  subnet_id = var.subnet_id

  user_data = templatefile("${path.module}/es-cluster.yaml",
    {
      es_cluster_script = yamlencode(filebase64("${path.module}/es_cluster.sh")),
      es_password       = var.password,

      es_snapshot_access_key = var.snapshot_user_aws_access_key_id,
      es_snapshot_secret_key = var.snapshot_user_aws_secret_access_key,
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

  associate_public_ip_address = true

  subnet_id = var.subnet_id

  user_data = templatefile("${path.module}/es-load-generation.yaml",
    {
      es_load_script  = yamlencode(filebase64("${path.module}/es_load_generation.sh")),
      es_cluster      = aws_instance.target-cluster.public_dns
      es_password     = var.password,
      es_index_8_15_0 = yamlencode(filebase64("${path.module}/es_indexes/es_index_8.15.0.json")),

      ingest_script = yamlencode(
        base64encode(templatefile("${path.module}/ingest.sh",
          {
            s3_bucket_name  = var.s3_bucket_name,
            workload_params = var.workload_params,
          }
        ))
      ),
      restore_snapshot_script = yamlencode(
        base64encode(templatefile("${path.module}/restore_snapshot.sh",
          {
            s3_bucket_name = var.s3_bucket_name,
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
