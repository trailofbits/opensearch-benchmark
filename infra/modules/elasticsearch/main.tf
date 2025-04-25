locals {
  cluster_arch_map = {
    vectorsearch = "aarch64"
  }
  default_cluster_arch = "x86_64"
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

locals {
  # start at 4 because first 4 addresses are reserved for AWS
  load_generation_private_ip = cidrhost(var.subnet_cidr_block, 4)
  cluster_node_private_ips = [
    cidrhost(var.subnet_cidr_block, 5),
    cidrhost(var.subnet_cidr_block, 6),
    cidrhost(var.subnet_cidr_block, 7)
  ]
  main_cluster_node_private_ip        = local.cluster_node_private_ips[0]
  nodes_type                          = var.workload == "vectorsearch" ? "multi" : "single"
  additional_nodes_idx                = var.workload == "vectorsearch" ? 1 : 3
  additional_cluster_node_private_ips = slice(local.cluster_node_private_ips, local.additional_nodes_idx, 3)
}

resource "tls_private_key" "cert-key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "tls_self_signed_cert" "cert" {
  private_key_pem = tls_private_key.cert-key.private_key_pem

  ip_addresses = local.cluster_node_private_ips
  dns_names    = concat([for ip in local.cluster_node_private_ips : format("node-%s", ip)], ["main-node"])

  subject {
    common_name  = "target-cluster"
    country      = "US"
    organization = "Target Cluster Org"
  }

  validity_period_hours = 720

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
    "cert_signing",
    "client_auth",
    "key_agreement",
    "timestamping",
  ]

}

resource "aws_instance" "target-cluster-additional-nodes" {
  for_each               = toset(local.additional_cluster_node_private_ips)
  ami                    = var.cluster_ami_id
  instance_type          = var.cluster_instance_type
  key_name               = var.ssh_key_name
  vpc_security_group_ids = var.security_groups

  associate_public_ip_address = true

  subnet_id  = var.subnet_id
  private_ip = each.key

  user_data = templatefile("${path.module}/es-cluster.yaml",
    {
      es_cluster_script = yamlencode(base64gzip(file("${path.module}/es_cluster.sh"))),
      es_password       = var.password,
      es_version        = var.es_version,
      es_arch           = local.cluster_arch,

      es_snapshot_access_key = var.snapshot_user_aws_access_key_id,
      es_snapshot_secret_key = var.snapshot_user_aws_secret_access_key,
      authorized_ssh_key     = yamlencode(base64gzip(var.ssh_pub_key)),
      jvm_options            = yamlencode(base64gzip(file("${path.module}/jvm.options"))),
      cluster_ips            = join(",", local.cluster_node_private_ips),
      node_name              = format("node-%s", each.key),
      crt                    = yamlencode(base64gzip(tls_self_signed_cert.cert.cert_pem)),
      crt_key                = yamlencode(base64gzip(tls_private_key.cert-key.private_key_pem)),
      nodes_type             = local.nodes_type,
    }
  )
  user_data_replace_on_change = true

  private_dns_name_options {
    hostname_type = "resource-name"
  }

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

  tags = var.tags
}

resource "aws_instance" "target-cluster-main-node" {
  ami                    = var.cluster_ami_id
  instance_type          = var.cluster_instance_type
  key_name               = var.ssh_key_name
  vpc_security_group_ids = var.security_groups

  associate_public_ip_address = true

  subnet_id = var.subnet_id

  private_ip = local.main_cluster_node_private_ip

  user_data = templatefile("${path.module}/es-cluster.yaml",
    {
      es_cluster_script = yamlencode(base64gzip(file("${path.module}/es_cluster.sh"))),
      es_password       = var.password,
      es_version        = var.es_version,
      es_arch           = local.cluster_arch,

      es_snapshot_access_key = var.snapshot_user_aws_access_key_id,
      es_snapshot_secret_key = var.snapshot_user_aws_secret_access_key,
      authorized_ssh_key     = yamlencode(base64gzip(var.ssh_pub_key)),
      jvm_options            = yamlencode(base64gzip(file("${path.module}/jvm.options"))),
      cluster_ips            = join(",", local.cluster_node_private_ips),
      node_name              = "main-node",
      crt                    = yamlencode(base64gzip(tls_self_signed_cert.cert.cert_pem)),
      crt_key                = yamlencode(base64gzip(tls_private_key.cert-key.private_key_pem)),
      nodes_type             = local.nodes_type,
    }
  )
  user_data_replace_on_change = true

  private_dns_name_options {
    hostname_type = "resource-name"
  }

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

  private_ip = local.load_generation_private_ip

  user_data = templatefile("${path.module}/es-load-generation.yaml",
    {
      load_script = yamlencode(base64gzip(templatefile(
        "${path.module}/../../scripts/load_generation.sh",
        {
          workload    = var.workload,
          aws_userid  = replace(data.aws_caller_identity.current.arn, "/.+//", ""),
          osb_version = var.osb_version
        }
      ))),
      utils_script            = yamlencode(base64gzip(file("${path.module}/../../scripts/utils.sh"))),
      es_cluster              = aws_instance.target-cluster-main-node.public_dns
      es_password             = var.password,
      distribution_version    = var.distribution_version,
      es_version              = var.es_version,
      workload                = var.workload
      big5_es_index_8         = yamlencode(base64gzip(file("${path.module}/es_indexes/big5/es_index_8.json"))),
      vectorsearch_es_index_8 = yamlencode(base64gzip(file("${path.module}/es_indexes/vectorsearch/es_index_8.json"))),
      big5_es_index_9         = yamlencode(base64gzip(file("${path.module}/es_indexes/big5/es_index_9.json"))),
      vectorsearch_es_index_9 = yamlencode(base64gzip(file("${path.module}/es_indexes/vectorsearch/es_index_9.json"))),
      osb_knn_patch           = yamlencode(base64gzip(file("${path.module}/es_files/osb-1.11.0-knn.patch"))),
      vectorsearch_task_patch = yamlencode(base64gzip(file("${path.module}/../common_files/vectorsearch-task.patch"))),
      benchmark_environment   = var.benchmark_environment
      datastore_host          = var.datastore_host
      datastore_username      = var.datastore_username
      datastore_password      = var.datastore_password
      instance_type           = var.cluster_instance_type
      cluster_instance_id     = aws_instance.target-cluster-main-node.id
      fix_files_script = yamlencode(base64gzip(templatefile("${path.module}/fix_files.sh",
        {
          workload = var.workload,
        }
      ))),
      ssh_private_key = base64gzip(var.ssh_priv_key)
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

  private_dns_name_options {
    hostname_type = "resource-name"
  }

  tags = {
    Name = "load-generation"
  }

  # Ensure the load-generation instance is created after the target-cluster
  # instance so we can connect to it
  depends_on = [aws_instance.target-cluster-main-node]
}

resource "aws_ec2_managed_prefix_list_entry" "prefix-list-entry-load-gen" {
  count          = length(var.prefix_list_id) > 0 ? 1 : 0
  provider       = aws.prefix_list_region
  cidr           = "${aws_instance.load-generation.public_ip}/32"
  description    = terraform.workspace
  prefix_list_id = var.prefix_list_id
}
