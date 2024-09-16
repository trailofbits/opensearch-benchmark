variable "instance_type" {
  description = "Instance type to use for the cluster"
  type        = string
  default     = "c5d.2xlarge"
}

variable "ami_id" {
  description = "AMI ID to use for the cluster"
  type        = string
}

variable "os_version" {
  description = "Version of OpenSearch to deploy"
  type        = string
  default     = "2.16.0"
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
  description = "List of security groups to apply to the OS instance"
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
  description = "Password for the OS cluster"
  type        = string
}

variable "load_gen_ip" {
  description = "IP of Load generation Elastic IP"
  type        = string
}

variable "workload_params" {
  description = "Workload parameters to pass to the ingest and benchmark scripts"
  type        = string
  default     = ""
}
