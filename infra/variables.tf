variable "ssh_priv_key" {
  description = "Path to the SSH Private Key"
  type        = string
  default     = "~/.ssh/id_rsa"
}

variable "ssh_pub_key" {
  description = "Path to the SSH Public Key"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "aws_region" {
  description = "AWS region used for the deployment"
  type        = string
}

variable "aws_subnet_zone" {
  description = "AWS subnet availability zone, tied to the aws_region used"
  type        = string
}

variable "target_cluster_type" {
  description = "Type of cluster to deploy (ES, OS, etc.)"
  type        = string
  validation {
    condition     = contains(["ElasticSearch", "OpenSearch"], var.target_cluster_type)
    error_message = "Valid values for var: target_cluster_type are (ElasticSearch, OpenSearch)."
  }
  default = "OpenSearch"
}

variable "instance_type" {
  description = "Instance type to use for the cluster"
  type        = string
  default     = "c5d.2xlarge"
}

variable "es_version" {
  description = "Version of ElasticSearch to deploy"
  type        = string
  default     = "8.15.0"
}

variable "os_version" {
  description = "Version of OpenSearch to deploy"
  type        = string
  default     = "2.16.0"
}
