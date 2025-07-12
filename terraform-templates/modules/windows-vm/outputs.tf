output "vm_id" {
  description = "The VMID of the created Windows VM"
  value       = proxmox_vm_qemu.vm.vmid
}

output "vm_name" {
  description = "The name of the created Windows VM"
  value       = proxmox_vm_qemu.vm.name
}

output "vm_node" {
  description = "The Proxmox node where the Windows VM is running"
  value       = proxmox_vm_qemu.vm.target_node
}

output "vm_ip_address" {
  description = "The IP address of the Windows VM (if available)"
  value       = proxmox_vm_qemu.vm.default_ipv4_address
}

output "vm_mac_address" {
  description = "The MAC address of the Windows VM's primary network interface"
  value       = proxmox_vm_qemu.vm.network[0].macaddr
}

output "vm_rdp_connection" {
  description = "RDP connection information for the Windows VM"
  value = {
    host = proxmox_vm_qemu.vm.default_ipv4_address
    port = 3389
    user = var.username
    command = "mstsc /v:${proxmox_vm_qemu.vm.default_ipv4_address}"
  }
}

output "vm_template_used" {
  description = "The template used to create this Windows VM"
  value       = var.template_name
}

output "vm_resource_summary" {
  description = "Summary of Windows VM resources"
  value = {
    cores  = var.cores
    memory = var.memory
    disk   = var.disk_size
    storage = var.storage_pool
    bios   = var.bios
    os_type = "Windows"
  }
}

output "vm_network_config" {
  description = "Network configuration of the Windows VM"
  value = {
    bridge     = var.network_bridge
    model      = var.network_model
    ip_config  = var.network_config
    ip_address = var.ip_address
    gateway    = var.gateway
    vlan_tag   = var.network_tag
  }
} 