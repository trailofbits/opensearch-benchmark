terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.65.0"
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

locals {
  benchmark_subnet_cidr_block = cidrsubnet(aws_vpc.vpc.cidr_block, 3, 1)
  datastore_cidr_blocks = [
    cidrsubnet(aws_vpc.vpc.cidr_block, 3, 2),
    cidrsubnet(aws_vpc.vpc.cidr_block, 3, 3),
    cidrsubnet(aws_vpc.vpc.cidr_block, 3, 4)
  ]
  datastore_subnet_map = zipmap(var.aws_subnet_zones, local.datastore_cidr_blocks)
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
  cidr_block        = local.benchmark_subnet_cidr_block
  vpc_id            = aws_vpc.vpc.id
  availability_zone = var.aws_subnet_zones[0]
}

resource "aws_subnet" "datastore_subnets" {
  for_each          = local.datastore_subnet_map
  cidr_block        = each.value
  vpc_id            = aws_vpc.vpc.id
  availability_zone = each.key
}

resource "aws_internet_gateway" "gtw" {
  vpc_id = aws_vpc.vpc.id
}

resource "aws_security_group" "allow_osb" {
  name        = "${terraform.workspace}-allow-osb"
  description = "Allow ES/OS/OSB inbound traffic and all outbound traffic"
  vpc_id      = aws_vpc.vpc.id
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

resource "aws_vpc_security_group_ingress_rule" "allow_https_traffic" {
  security_group_id = aws_security_group.allow_osb.id
  cidr_ipv4         = "10.0.0.0/16"
  from_port         = 443
  to_port           = 443
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

resource "aws_route_table_association" "datastore-subnet-associations" {
  for_each       = aws_subnet.datastore_subnets
  subnet_id      = each.value.id
  route_table_id = aws_route_table.route-table-test-env.id
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

resource "aws_instance" "target-cluster" {
  ami             = data.aws_ami.ubuntu_ami.id
  instance_type   = "c5d.2xlarge"
  key_name        = aws_key_pair.ssh_key.key_name
  security_groups = [aws_security_group.allow_osb.id]

  associate_public_ip_address = true

  subnet_id = aws_subnet.subnet.id

  user_data = templatefile("${path.module}/scripts/init.sh", {
    hostname = "target-cluster"
  })

  private_dns_name_options {
    hostname_type = "resource-name"
  }

  tags = {
    Name = "target-cluster"
  }
}

resource "aws_instance" "load-generation" {
  ami             = data.aws_ami.ubuntu_ami.id
  instance_type   = "c5d.2xlarge"
  key_name        = aws_key_pair.ssh_key.key_name
  security_groups = [aws_security_group.allow_osb.id]

  associate_public_ip_address = true

  subnet_id = aws_subnet.subnet.id

  user_data = templatefile("${path.module}/scripts/init.sh", {
    hostname = "load-generation"
  })

  private_dns_name_options {
    hostname_type = "resource-name"
  }

  tags = {
    Name = "load-generation"
  }
}

output "target-cluster-ip" {
  value = aws_instance.target-cluster.public_dns
}

output "load-generation-ip" {
  value = aws_instance.load-generation.public_dns
}
