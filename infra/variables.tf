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

variable "s3_bucket_name" {
  description = "S3 bucket name for the snapshot"
  type        = string
}

variable "snapshot_user_aws_access_key_id" {
  description = "value of the AWS_ACCESS_KEY_ID for the snapshot user"
  type        = string
  sensitive   = true
}

variable "snapshot_user_aws_secret_access_key" {
  description = "value of the AWS_SECRET_ACCESS_KEY for the snapshot user"
  type        = string
  sensitive   = true
}

variable "workload_params" {
  description = "Workload parameters for the cluster"
  type        = string
  default     = "number_of_replicas:0,bulk_indexing_clients:1,max_num_segments:10,target_throughput:0"
}
