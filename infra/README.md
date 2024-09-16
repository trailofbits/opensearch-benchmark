# OpenSearch benchmarking infrastructure

## Steps
- Install `terraform` and `awscli`.
- In the AWS Console, go to "Security Credentials" and create a new "Access Key"
- Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- Create an Elastic IP in the console. This will be for the load generator so that it remains the same across deployments.
    - For metric data store access: Add the Elastic IP you created to the shared prefix list (id: `pl-06f77c0b59dbf70fe`).
    - Set `load_gen_ip` to the Elastic IP address in `terraform.tfvars`.
- `terraform workspace new <unique-name>` (e.g. `terraform workspace new rschirone`)
- `terraform init`
- `terraform apply -var ssh_pub_key=~/.ssh/id_rsa.pub` (or change the variable in `terraform.tfvars` and just run `terraform apply`)
- connect to the VM with `ssh ubuntu@<ip>`

## Connecting to the Metric Datastore
OpenSearch Benchmark can be configured to use a remote OpenSearch instance as a metric data store. These instructions are specific to the shared data store.

- Connect to the load generation instance and update `~/.benchmark/benchmark.ini`
```
[results_publishing]
datastore.type = opensearch
datastore.host = insert_hostname_here
datastore.port = 443
datastore.secure = True
datastore.ssl.verification_mode = none
datastore.user = insert_user_here
datastore.password = insert_password_here
datastore.number_of_replicas = 1
datastore.number_of_shards = 3
```
