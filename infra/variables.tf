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

variable "load_gen_ip" {
  description = "IP address of an existing Elastic IP for the load gen instance."
  type        = string
  validation {
    condition = (
      can(cidrnetmask("${var.load_gen_ip}/32"))
    )
    error_message = "The load_gen_ip value must be a valid IPv4 address."
  }
}
