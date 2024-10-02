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
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.ssh_key_name
  vpc_security_group_ids = var.security_groups

  associate_public_ip_address = true

  subnet_id = var.subnet_id

  user_data = templatefile("${path.module}/es-cluster.yaml",
    {
      es_cluster_script = yamlencode(base64gzip(file("${path.module}/es_cluster.sh"))),
      es_password       = var.password,
      es_version        = var.es_version

      es_snapshot_access_key = var.snapshot_user_aws_access_key_id,
      es_snapshot_secret_key = var.snapshot_user_aws_secret_access_key,
    }
  )
  user_data_replace_on_change = true

  private_dns_name_options {
    hostname_type = "resource-name"
  }

  tags = var.tags
}

resource "aws_instance" "load-generation" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.ssh_key_name
  vpc_security_group_ids = var.security_groups

  # Temporarily assign public IP before EIP so that provisioner can connect to instance
  # NOTE: self.public_ip will be outdated after the aws_eip_association
  associate_public_ip_address = true

  subnet_id = var.subnet_id

  user_data = templatefile("${path.module}/es-load-generation.yaml",
    {
      load_script = yamlencode(base64gzip(templatefile(
        "${path.module}/../../scripts/load_generation.sh",
        {
          workload = var.workload,
          aws_userid   = replace(data.aws_caller_identity.current.arn, "/.+//", "")
        }
      ))),
      es_cluster            = aws_instance.target-cluster.public_dns
      es_password           = var.password,
      distribution_version  = var.distribution_version,
      es_version            = var.es_version,
      workload              = var.workload
      big5_es_index_8_15    = yamlencode(base64gzip(file("${path.module}/es_indexes/big5/es_index_8.15.json"))),
      benchmark_environment = var.benchmark_environment
      datastore_host        = var.datastore_host
      datastore_username    = var.datastore_username
      datastore_password    = var.datastore_password
      instance_type         = var.instance_type

      ingest_script = yamlencode(
        base64gzip(templatefile("${path.module}/../../scripts/ingest.sh",
          {
            workload        = var.workload
            s3_bucket_name  = var.s3_bucket_name,
            workload_params = var.workload_params,
          }
        ))
      ),
      restore_snapshot_script = yamlencode(
        base64gzip(templatefile("${path.module}/../../scripts/restore_snapshot.sh",
          {
            workload        = var.workload
            s3_bucket_name  = var.s3_bucket_name,
            workload_params = var.workload_params,
          }
        ))
      ),
      benchmark_script = yamlencode(
        base64gzip(templatefile("${path.module}/../../scripts/benchmark.sh",
          {
            workload        = var.workload
            workload_params = var.workload_params,
          }
        ))
      ),
      fix_index_script = yamlencode(base64gzip(templatefile("${path.module}/fix_index.sh",
        {
          workload = var.workload,
        }
      ))),
      utils_script = yamlencode(
        base64gzip(file("${path.module}/../../scripts/utils.sh"))
      ),
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

resource "aws_ec2_managed_prefix_list_entry" "prefix-list-entry-load-gen" {
  provider       = aws.prefix_list_region
  cidr           = "${aws_instance.load-generation.public_ip}/32"
  description    = terraform.workspace
  prefix_list_id = var.prefix_list_id
}
