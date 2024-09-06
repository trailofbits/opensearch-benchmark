terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.65.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"

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
  availability_zone = "us-east-1a"
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
