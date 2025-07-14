output "vm_id" {
  description = "The VMID of the created container"
  value       = proxmox_lxc.container.vmid
}

output "vm_name" {
  description = "The hostname of the created container"
  value       = proxmox_lxc.container.hostname
}

output "vm_node" {
  description = "The Proxmox node where the container is running"
  value       = proxmox_lxc.container.target_node
}

output "vm_status" {
  description = "The status of the container"
  value       = proxmox_lxc.container.start
}

output "vm_ip_address" {
  description = "The IP address of the container (if available)"
  value       = proxmox_lxc.container.network[0].ip
}

output "vm_mac_address" {
  description = "The MAC address of the container's primary network interface"
  value       = proxmox_lxc.container.network[0].hwaddr
}

output "vm_ssh_connection" {
  description = "SSH connection information for the container"
  value = {
    host = proxmox_lxc.container.network[0].ip
    port = 22
    user = var.username
    command = "ssh ${var.username}@${proxmox_lxc.container.network[0].ip}"
  }
}

output "vm_template_used" {
  description = "The template used to create this container"
  value       = var.template_name
}

output "vm_resource_summary" {
  description = "Summary of container resources"
  value = {
    cores   = var.cores
    memory  = var.memory
    swap    = var.swap
    disk    = var.disk_size
    storage = var.storage_pool
    arch    = var.architecture
  }
}

# Legacy outputs for backward compatibility
output "ct_id" {
  description = "The VMID of the created container (legacy)"
  value       = proxmox_lxc.container.vmid
}

output "ct_name" {
  description = "The hostname of the created container (legacy)"
  value       = proxmox_lxc.container.hostname
}

output "ct_node" {
  description = "The Proxmox node where the container is running (legacy)"
  value       = proxmox_lxc.container.target_node
}

output "ct_status" {
  description = "The status of the container (legacy)"
  value       = proxmox_lxc.container.start
}

output "ct_template_used" {
  description = "The template used to create this container (legacy)"
  value       = var.template_name
}

output "ct_network_info" {
  description = "Network configuration of the container (legacy)"
  value = {
    bridge     = var.network_bridge
    ip_config  = var.network_config
    ip_address = var.ip_address
    gateway    = var.gateway
    vlan_tag   = var.network_tag
  }
}

output "ct_resource_summary" {
  description = "Summary of container resources (legacy)"
  value = {
    cores   = var.cores
    memory  = var.memory
    swap    = var.swap
    disk    = var.disk_size
    storage = var.storage_pool
    arch    = var.architecture
  }
}

output "ct_ip_address" {
  description = "The IP address of the container (if available)"
  value       = proxmox_lxc.container.network[0].ip
}

output "ct_features" {
  description = "Container features configuration (legacy)"
  value = {
    unprivileged = var.unprivileged
    fuse         = var.features_fuse
    keyctl       = var.features_keyctl
    mount        = var.features_mount
    nesting      = var.features_nesting
  }
} 