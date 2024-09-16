ssh_priv_key                        = "~/.ssh/key"
ssh_pub_key                         = "~/.ssh/key.pub"
aws_region                          = "us-east-1"
aws_subnet_zone                     = "us-east-1a"
target_cluster_type                 = "ElasticSearch"
s3_bucket_name                      = "es-snapshots-osb"
snapshot_user_aws_access_key_id     = "<ACCESS-KEY>"
snapshot_user_aws_secret_access_key = "<SECRET-KEY>"

# Use this for a quick test of the whole process
# workload_params = "corpus_size:1,document_file:documents-60-1k.json.bz2,document_count:1000,document_uncompressed_size_in_bytes:926287,document_compressed_size_in_bytes:54669,number_of_replicas:0,bulk_indexing_clients:1,max_num_segments:10,target_throughput:0"
