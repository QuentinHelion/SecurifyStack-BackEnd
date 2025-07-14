output "vm_ids" {
  description = "The VMIDs of the created containers"
  value       = proxmox_lxc.container[*].vmid
}

output "vm_names" {
  description = "The names of the created containers"
  value       = proxmox_lxc.container[*].hostname
}

output "vm_nodes" {
  description = "The Proxmox nodes where the containers are running"
  value       = proxmox_lxc.container[*].target_node
}

output "vm_ip_addresses" {
  description = "The IP addresses of the containers (if available)"
  value       = [for container in proxmox_lxc.container : container.network[0].ip]
}

output "vm_mac_addresses" {
  description = "The MAC addresses of the containers' primary network interfaces"
  value       = [for container in proxmox_lxc.container : container.network[0].hwaddr]
}

output "vm_ssh_connections" {
  description = "SSH connection details for the containers"
  value = [
    for container in proxmox_lxc.container : {
      host    = split("/", container.network[0].ip)[0]
      port    = 22
      user    = var.username
      command = "ssh ${var.username}@${split("/", container.network[0].ip)[0]}"
    }
  ]
}

output "vm_template_used" {
  description = "The template used to create these containers"
  value       = var.template_name
}

output "vm_resource_summary" {
  description = "Summary of container pack resources"
  value = {
    vm_count = var.vm_count
    cores_per_vm = var.cores
    memory_per_vm = var.memory
    swap_per_vm = var.swap
    disk_per_vm = var.disk_size
    storage = var.storage_pool
    start_vmid = var.start_vmid
    base_name = var.base_name
  }
}

output "vm_pack_details" {
  description = "Detailed information about each container in the pack"
  value = [
    for i, container in proxmox_lxc.container : {
      index = i
      name = container.hostname
      id = container.vmid
      ip = split("/", container.network[0].ip)[0]
      mac = container.network[0].hwaddr
      ssh_connection = {
        host    = split("/", container.network[0].ip)[0]
        port    = 22
        user    = var.username
        command = "ssh ${var.username}@${split("/", container.network[0].ip)[0]}"
      }
    }
  ]
} 