variable "ssh_pub_key" {
  description = "Path to the SSH Public Key"
  type        = string
}

variable "aws_region" {
  description = "AWS region used for the deployment"
  type        = string
}

variable "aws_subnet_zone" {
  description = "AWS subnet availability zone, tied to the aws_region used"
  type        = string
}
