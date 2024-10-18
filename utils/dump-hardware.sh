#!/bin/bash
# Dump hardware information in a tarfile
# Usage (where current directory is infra/ ):
# scp ../utils/dump-hardware.sh ubuntu@$(terraform output -raw target-cluster-ip):/home/ubuntu/
# ssh ubuntu@$(terraform output -raw target-cluster-ip) "bash dump-hardware.sh"
# scp "ubuntu@$(terraform output -raw target-cluster-ip):/home/ubuntu/hardware_info_*.tar.gz" .

instance_id="$(curl -m 5 -s http://169.254.169.254/latest/meta-data/instance-id)"
# Create a directory for output
output_dir="hardware_info_$(hostname)_$instance_id"
mkdir -p "$output_dir"

# Save raw output
save_raw_output() {
    commands_file="$output_dir/commands.txt"
    echo "Saving raw output..."
    echo "# Command outputs recorded in each file" >> $commands_file

    uname -a > "$output_dir/uname_output.txt"
    echo "uname_output.txt: uname -a" >> $commands_file

    lsblk -o "NAME,MAJ:MIN,RM,SIZE,RO,TYPE,MOUNTPOINTS,TRAN,ROTA,SCHED,MODEL,SERIAL" > "$output_dir/lsblk_output.txt"
    echo "lsblk_output.txt: lsblk -o \"NAME,MAJ:MIN,RM,SIZE,RO,TYPE,MOUNTPOINTS,TRAN,ROTA,SCHED,MODEL,SERIAL\"" >> $commands_file

    sudo dmidecode > "$output_dir/dmidecode_all_output.txt"
    echo "dmidecode_all_output.txt: sudo dmidecode" >> $commands_file

    sudo dmidecode -t memory > "$output_dir/dmidecode_memory_output.txt"
    echo "dmidecode_memory_output.txt: sudo dmidecode -t memory" >> $commands_file

    lscpu > "$output_dir/lscpu_output.txt"
    echo "lscpu_output.txt: lscpu" >> $commands_file

    sudo lshw > "$output_dir/lshw_output.txt"
    echo "lshw_output.txt: lshw" >> $commands_file

    lspci > "$output_dir/lspci_output.txt"
    echo "lspci_output.txt: lspci" >> $commands_file

    lspci -vv > "$output_dir/lspci_verbose_output.txt"
    echo "lspci_verbose_output.txt: lspci -vv" >> $commands_file

    echo "Raw output saved in $output_dir"
}

# Main script
save_raw_output

tar czf "$output_dir.tar.gz" "$output_dir"
echo "Created tarfile: $output_dir.tar.gz"
