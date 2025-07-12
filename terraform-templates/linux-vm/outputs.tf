output "vm_id" {
  description = "The VMID of the created VM"
  value       = module.linux_vm.vm_id
}

output "vm_name" {
  description = "The name of the created VM"
  value       = module.linux_vm.vm_name
}

output "vm_node" {
  description = "The Proxmox node where the VM is running"
  value       = module.linux_vm.vm_node
}

output "vm_ip_address" {
  description = "The IP address of the VM (if available)"
  value       = module.linux_vm.vm_ip_address
}

output "vm_mac_address" {
  description = "The MAC address of the VM's primary network interface"
  value       = module.linux_vm.vm_mac_address
}

output "vm_ssh_host" {
  description = "SSH connection string for the VM"
  value       = module.linux_vm.vm_ssh_host
}

output "vm_ssh_port" {
  description = "SSH port for the VM"
  value       = module.linux_vm.vm_ssh_port
}

output "vm_template_used" {
  description = "The template used to create this VM"
  value       = module.linux_vm.vm_template_used
}

output "vm_resource_summary" {
  description = "Summary of VM resources"
  value       = module.linux_vm.vm_resource_summary
} 