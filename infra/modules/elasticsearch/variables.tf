variable "instance_type" {
  description = "Instance type to use for the cluster"
  type        = string
  default     = "c5d.2xlarge"
}

variable "ami_id" {
  description = "AMI ID to use for the cluster"
  type        = string
}

variable "es_version" {
  description = "Version of ElasticSearch to deploy"
  type        = string
  default     = "8.15.0"
}

variable "ssh_key_name" {
  description = "Name of the SSH key to use for the cluster"
  type        = string
}

variable "ssh_priv_key" {
  description = "Path to the SSH Private Key"
  type        = string
}

variable "security_groups" {
  description = "List of security groups to apply to the ES instance"
  type        = list(string)
}

variable "subnet_id" {
  description = "Subnet ID"
  type        = string
}

variable "tags" {
  description = "List of Tags to apply to resources"
  type        = any
}

variable "password" {
  description = "Password for the ES cluster"
  type        = string
}
