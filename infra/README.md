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
