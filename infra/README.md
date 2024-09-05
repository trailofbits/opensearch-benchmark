# OpenSearch benchmarking infrastructure

## Steps
- Install `terraform` and `awscli`.
- In the AWS Console, go to "Security Credentials" and create a new "Access Key"
- Set the environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- `terraform workspace new <unique-name>` (e.g. `terraform workspace new rschirone`)
- `terraform init`
- `terraform apply -var ssh_pub_key=~/.ssh/id_rsa.pub` (or change the variable in `terraform.tfvars` and just run `terraform apply`)
- connect to the VM with `ssh ubuntu@<ip>`
