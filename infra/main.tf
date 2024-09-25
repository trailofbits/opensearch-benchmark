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

resource "aws_key_pair" "ssh_key" {
  key_name   = "${terraform.workspace}-ssh-key"
  public_key = file(var.ssh_pub_key)
}

resource "aws_vpc" "vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_subnet" "subnet" {
  cidr_block        = cidrsubnet(aws_vpc.vpc.cidr_block, 3, 1)
  vpc_id            = aws_vpc.vpc.id
  availability_zone = var.aws_subnet_zone
}

resource "aws_internet_gateway" "gtw" {
  vpc_id = aws_vpc.vpc.id
}

resource "aws_security_group" "allow_osb" {
  name        = "${terraform.workspace}-allow-osb"
  description = "Allow ES/OS/OSB inbound traffic and all outbound traffic"
  vpc_id      = aws_vpc.vpc.id

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "allow_ssh" {
  security_group_id = aws_security_group.allow_osb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 22
  ip_protocol       = "tcp"
  to_port           = 22
}

resource "aws_vpc_security_group_ingress_rule" "allow_es_cluster_traffic_9200" {
  security_group_id = aws_security_group.allow_osb.id
  cidr_ipv4         = "10.0.0.0/16"
  from_port         = 9200
  to_port           = 9200
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "allow_es_cluster_traffic_9300" {
  security_group_id = aws_security_group.allow_osb.id
  cidr_ipv4         = "10.0.0.0/16"
  from_port         = 9300
  to_port           = 9300
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.allow_osb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" # semantically equivalent to all ports
}

resource "aws_route_table" "route-table-test-env" {
  vpc_id = aws_vpc.vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gtw.id
  }
}

resource "aws_route_table_association" "subnet-association" {
  subnet_id      = aws_subnet.subnet.id
  route_table_id = aws_route_table.route-table-test-env.id
}

data "aws_ec2_managed_prefix_list" "prefix-list" {
  provider = aws.prefix_list_region
  id       = var.prefix_list_id
}

data "aws_ami" "ubuntu_ami" {
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

resource "random_password" "cluster-password" {
  length      = 16
  special     = false
  min_lower   = 1
  min_upper   = 0
  min_numeric = 1
}

module "es-cluster" {
  count = var.target_cluster_type == "ElasticSearch" ? 1 : 0

  source                = "./modules/elasticsearch"
  instance_type         = var.instance_type
  ami_id                = data.aws_ami.ubuntu_ami.id
  es_version            = var.es_version
  distribution_version  = var.distribution_version
  ssh_key_name          = aws_key_pair.ssh_key.key_name
  ssh_priv_key          = var.ssh_priv_key
  security_groups       = [aws_security_group.allow_osb.id]
  subnet_id             = aws_subnet.subnet.id
  password              = random_password.cluster-password.result
  prefix_list_id        = data.aws_ec2_managed_prefix_list.prefix-list.id
  benchmark_environment = var.benchmark_environment
  datastore_host        = var.datastore_host
  datastore_username    = var.datastore_username
  datastore_password    = var.datastore_password
  workload              = var.workload

  s3_bucket_name                      = var.s3_bucket_name
  snapshot_user_aws_access_key_id     = var.snapshot_user_aws_access_key_id
  snapshot_user_aws_secret_access_key = var.snapshot_user_aws_secret_access_key
  workload_params                     = var.workload_params

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
  instance_type         = var.instance_type
  ami_id                = data.aws_ami.ubuntu_ami.id
  os_version            = var.os_version
  distribution_version  = var.distribution_version
  ssh_key_name          = aws_key_pair.ssh_key.key_name
  ssh_priv_key          = var.ssh_priv_key
  security_groups       = [aws_security_group.allow_osb.id]
  subnet_id             = aws_subnet.subnet.id
  password              = random_password.cluster-password.result
  prefix_list_id        = data.aws_ec2_managed_prefix_list.prefix-list.id
  benchmark_environment = var.benchmark_environment
  datastore_host        = var.datastore_host
  datastore_username    = var.datastore_username
  datastore_password    = var.datastore_password
  workload              = var.workload

  s3_bucket_name                      = var.s3_bucket_name
  snapshot_user_aws_access_key_id     = var.snapshot_user_aws_access_key_id
  snapshot_user_aws_secret_access_key = var.snapshot_user_aws_secret_access_key
  workload_params                     = var.workload_params

  providers = {
    aws                    = aws
    aws.prefix_list_region = aws.prefix_list_region
  }

  tags = {
    Name = "target-cluster"
  }
}
