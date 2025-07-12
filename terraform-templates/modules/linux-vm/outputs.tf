output "vm_id" {
  description = "The VMID of the created VM"
  value       = proxmox_vm_qemu.vm.vmid
}

output "vm_name" {
  description = "The name of the created VM"
  value       = proxmox_vm_qemu.vm.name
}

output "vm_node" {
  description = "The Proxmox node where the VM is running"
  value       = proxmox_vm_qemu.vm.target_node
}

output "vm_status" {
  description = "The status of the VM"
  value       = proxmox_vm_qemu.vm.default_ipv4_address
}

output "vm_ip_address" {
  description = "The IP address of the VM (if available)"
  value       = proxmox_vm_qemu.vm.default_ipv4_address
}

output "vm_mac_address" {
  description = "The MAC address of the VM's primary network interface"
  value       = proxmox_vm_qemu.vm.network[0].macaddr
}

output "vm_ssh_connection" {
  description = "SSH connection information for the VM"
  value = {
    host = proxmox_vm_qemu.vm.default_ipv4_address
    port = 22
    user = var.username
    command = "ssh ${var.username}@${proxmox_vm_qemu.vm.default_ipv4_address}"
  }
}

output "vm_template_used" {
  description = "The template used to create this VM"
  value       = var.template_name
}

output "vm_resource_summary" {
  description = "Summary of VM resources"
  value = {
    cores  = var.cores
    memory = var.memory
    disk   = var.disk_size
    storage = var.storage_pool
  }
} 