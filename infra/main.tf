terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.65.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "3.6.2"
    }

    external = {
      source  = "hashicorp/external"
      version = "2.3.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Workspace = terraform.workspace
      Service   = "OSB"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  alias  = "prefix_list_region"

  default_tags {
    tags = {
      Workspace = terraform.workspace
      Service   = "OSB"
    }
  }
}

resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Save private key to a local file
resource "local_file" "private_key" {
  content         = tls_private_key.ssh_key.private_key_pem
  filename        = "${path.module}/private_key-${terraform.workspace}.pem"
  file_permission = "0600"
}

resource "aws_key_pair" "ssh_key" {
  key_name   = "${terraform.workspace}-ssh-key"
  public_key = tls_private_key.ssh_key.public_key_openssh
}

data "aws_vpc" "vpc" {
  id = var.vpc_id
}

data "aws_subnet" "subnet" {
  id = var.vpc_subnet_id
}

data "aws_internet_gateway" "gtw" {
  internet_gateway_id = var.vpc_gateway_id
}

data "aws_route_table" "route-table-test-env" {
  route_table_id = var.vpc_route_table_id
}

resource "aws_route_table_association" "subnet-association" {
  subnet_id      = data.aws_subnet.subnet.id
  route_table_id = data.aws_route_table.route-table-test-env.route_table_id
}

data "aws_ec2_managed_prefix_list" "prefix-list" {
  provider = aws.prefix_list_region
  id       = var.prefix_list_id
}

data "aws_ami" "ubuntu_ami_amd64" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"]
}

data "aws_ami" "ubuntu_ami_arm64" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"]
}

resource "random_password" "cluster-password" {
  length      = 16
  special     = false
  min_lower   = 1
  min_upper   = 0
  min_numeric = 1
}

data "external" "latest_snapshot_version" {
  program = ["python3", "${path.module}/get_latest_snapshot_version.py"]
  query = {
    s3_bucket_name        = var.s3_bucket_name
    aws_access_key_id     = var.snapshot_user_aws_access_key_id
    aws_secret_access_key = var.snapshot_user_aws_secret_access_key
    cluster_type          = var.target_cluster_type == "ElasticSearch" ? "ES" : "OS"
    cluster_version       = var.target_cluster_type == "ElasticSearch" ? var.es_version : var.os_version
    workload              = var.workload
    snapshot_version      = var.snapshot_version
  }
}

locals {
  # set instance types based on the workload
  # TODO set r*.4xlarge if vectorsearch with 10 million docs
  workload_cluster_instance_map = {
    vectorsearch = "r6gd.4xlarge"
  }
  workload_loadgen_instance_map = {
    vectorsearch = "c5d.4xlarge"
  }
  default_cluster_instance = "c5d.2xlarge"
  default_loadgen_instance = "c5d.2xlarge"
  cluster_instance_type    = lookup(local.workload_cluster_instance_map, var.workload, local.default_cluster_instance)
  loadgen_instance_type    = lookup(local.workload_loadgen_instance_map, var.workload, local.default_loadgen_instance)

  workload_cluster_ami_map = {
    vectorsearch = data.aws_ami.ubuntu_ami_arm64.id
  }
  workload_loadgen_ami_map = {
  }
  default_cluster_ami = data.aws_ami.ubuntu_ami_amd64.id
  default_loadgen_ami = data.aws_ami.ubuntu_ami_amd64.id
  cluster_ami_id      = lookup(local.workload_cluster_ami_map, var.workload, local.default_cluster_ami)
  loadgen_ami_id      = lookup(local.workload_loadgen_ami_map, var.workload, local.default_loadgen_ami)
}

module "es-cluster" {
  count = var.target_cluster_type == "ElasticSearch" ? 1 : 0

  source                = "./modules/elasticsearch"
  cluster_instance_type = local.cluster_instance_type
  loadgen_instance_type = local.loadgen_instance_type
  cluster_ami_id        = local.cluster_ami_id
  loadgen_ami_id        = local.loadgen_ami_id
  es_version            = var.es_version
  distribution_version  = var.distribution_version
  ssh_key_name          = aws_key_pair.ssh_key.key_name
  ssh_priv_key          = tls_private_key.ssh_key.private_key_openssh
  ssh_pub_key           = tls_private_key.ssh_key.public_key_openssh
  security_groups       = [var.security_group_id]
  subnet_id             = data.aws_subnet.subnet.id
  password              = random_password.cluster-password.result
  prefix_list_id        = data.aws_ec2_managed_prefix_list.prefix-list.id
  benchmark_environment = var.benchmark_environment
  datastore_host        = var.datastore_host
  datastore_username    = var.datastore_username
  datastore_password    = var.datastore_password
  workload              = var.workload
  osb_version           = var.osb_version

  s3_bucket_name                      = var.s3_bucket_name
  snapshot_version                    = data.external.latest_snapshot_version.result.latest_version
  snapshot_user_aws_access_key_id     = var.snapshot_user_aws_access_key_id
  snapshot_user_aws_secret_access_key = var.snapshot_user_aws_secret_access_key
  workload_params                     = var.workload_params
  test_procedure                      = var.test_procedure

  providers = {
    aws                    = aws
    aws.prefix_list_region = aws.prefix_list_region
  }

  tags = {
    Name = "target-cluster"
  }
}

module "os-cluster" {
  count = var.target_cluster_type == "OpenSearch" ? 1 : 0

  source                = "./modules/opensearch"
  cluster_instance_type = local.cluster_instance_type
  loadgen_instance_type = local.loadgen_instance_type
  cluster_ami_id        = local.cluster_ami_id
  loadgen_ami_id        = local.loadgen_ami_id
  os_version            = var.os_version
  distribution_version  = var.distribution_version
  ssh_key_name          = aws_key_pair.ssh_key.key_name
  ssh_priv_key          = tls_private_key.ssh_key.private_key_openssh
  ssh_pub_key           = tls_private_key.ssh_key.public_key_openssh
  security_groups       = [var.security_group_id]
  subnet_id             = data.aws_subnet.subnet.id
  password              = random_password.cluster-password.result
  prefix_list_id        = data.aws_ec2_managed_prefix_list.prefix-list.id
  benchmark_environment = var.benchmark_environment
  datastore_host        = var.datastore_host
  datastore_username    = var.datastore_username
  datastore_password    = var.datastore_password
  workload              = var.workload
  osb_version           = var.osb_version

  s3_bucket_name                      = var.s3_bucket_name
  snapshot_version                    = data.external.latest_snapshot_version.result.latest_version
  snapshot_user_aws_access_key_id     = var.snapshot_user_aws_access_key_id
  snapshot_user_aws_secret_access_key = var.snapshot_user_aws_secret_access_key
  workload_params                     = var.workload_params
  test_procedure                      = var.test_procedure

  providers = {
    aws                    = aws
    aws.prefix_list_region = aws.prefix_list_region
  }

  tags = {
    Name = "target-cluster"
  }
}
