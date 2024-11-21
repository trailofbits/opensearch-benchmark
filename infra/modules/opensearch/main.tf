locals {
  cluster_arch_map = {
    vectorsearch = "arm64"
  }
  default_cluster_arch = "x64"
  cluster_arch         = lookup(local.cluster_arch_map, var.workload, local.default_cluster_arch)
}

terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "5.65.0"
      configuration_aliases = [aws.prefix_list_region]
    }
  }
}

data "aws_caller_identity" "current" {}

resource "aws_instance" "target-cluster" {
  ami                    = var.cluster_ami_id
  instance_type          = var.cluster_instance_type
  key_name               = var.ssh_key_name
  vpc_security_group_ids = var.security_groups

  associate_public_ip_address = true

  subnet_id = var.subnet_id

  user_data = templatefile("${path.module}/os-cluster.yaml",
    {
      os_cluster_script      = yamlencode(base64gzip(file("${path.module}/os_cluster.sh"))),
      os_password            = var.password,
      os_version             = var.os_version,
      os_arch                = local.cluster_arch,
      os_snapshot_access_key = var.snapshot_user_aws_access_key_id,
      os_snapshot_secret_key = var.snapshot_user_aws_secret_access_key,
      authorized_ssh_key     = var.ssh_pub_key,
    }
  )
  user_data_replace_on_change = true

  private_dns_name_options {
    hostname_type = "resource-name"
  }

  tags = var.tags
}

resource "aws_instance" "load-generation" {
  ami                    = var.loadgen_ami_id
  instance_type          = var.loadgen_instance_type
  key_name               = var.ssh_key_name
  vpc_security_group_ids = var.security_groups

  # Temporarily assign public IP before EIP so that provisioner can connect to instance
  # NOTE: self.public_ip will be outdated after the aws_eip_association
  associate_public_ip_address = true

  subnet_id = var.subnet_id

  user_data = templatefile("${path.module}/os-load-generation.yaml",
    {
      load_script = yamlencode(base64gzip(templatefile(
        "${path.module}/../../scripts/load_generation.sh",
        {
          workload   = var.workload,
          aws_userid = replace(data.aws_caller_identity.current.arn, "/.+//", "")
        }
      ))),
      os_cluster            = aws_instance.target-cluster.public_dns
      os_password           = var.password,
      distribution_version  = var.distribution_version,
      os_version            = var.os_version,
      workload              = var.workload
      benchmark_environment = var.benchmark_environment
      datastore_host        = var.datastore_host
      datastore_username    = var.datastore_username
      datastore_password    = var.datastore_password
      instance_type         = var.cluster_instance_type
      cluster_instance_id   = aws_instance.target-cluster.id
      ssh_private_key       = base64gzip(var.ssh_priv_key)
    }
  )
  user_data_replace_on_change = true

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
    private_key = var.ssh_priv_key
    host        = self.public_ip
  }

  private_dns_name_options {
    hostname_type = "resource-name"
  }

  provisioner "file" {
    content = templatefile("${path.module}/../../scripts/ingest.sh",
      {
        workload         = var.workload,
        s3_bucket_name   = var.s3_bucket_name,
        snapshot_version = var.snapshot_version,
      }
    )
    destination = "/mnt/ingest.sh"
  }

  provisioner "file" {
    content = templatefile("${path.module}/../../scripts/restore_snapshot.sh",
      {
        workload         = var.workload
        s3_bucket_name   = var.s3_bucket_name,
        snapshot_version = var.snapshot_version,
      }
    )
    destination = "/mnt/restore_snapshot.sh"
  }

  provisioner "file" {
    content = templatefile("${path.module}/../../scripts/benchmark.sh",
      {
        workload       = var.workload
        test_procedure = var.test_procedure,
      }
    )
    destination = "/mnt/benchmark.sh"
  }

  provisioner "file" {
    source      = "${path.module}/../../scripts/utils.sh"
    destination = "/mnt/utils.sh"
  }

  provisioner "file" {
    content = templatefile("${path.module}/../../scripts/segment_timestamps.sh",
      {
        workload = var.workload
      }
    )
    destination = "/mnt/segment_timestamps.sh"
  }

  provisioner "file" {
    content     = var.workload_params
    destination = "/mnt/workload_params.json"
  }

  tags = {
    Name = "load-generation"
  }

  # Ensure the load-generation instance is created after the target-cluster
  # instance so we can connect to it
  depends_on = [aws_instance.target-cluster]
}

resource "aws_ec2_managed_prefix_list_entry" "prefix-list-entry-load-gen" {
  provider       = aws.prefix_list_region
  cidr           = "${aws_instance.load-generation.public_ip}/32"
  description    = terraform.workspace
  prefix_list_id = var.prefix_list_id
}
