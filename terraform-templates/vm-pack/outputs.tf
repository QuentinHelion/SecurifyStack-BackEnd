output "vm_ids" {
  description = "The VMIDs of the created VMs/Containers"
  value       = concat(module.vm_pack_container[*].vm_id, module.vm_pack_vm[*].vm_id)
}

output "vm_names" {
  description = "The names of the created VMs/Containers"
  value       = concat(module.vm_pack_container[*].vm_name, module.vm_pack_vm[*].vm_name)
}

output "vm_nodes" {
  description = "The Proxmox nodes where the VMs/Containers are running"
  value       = concat(module.vm_pack_container[*].vm_node, module.vm_pack_vm[*].vm_node)
}

output "vm_ip_addresses" {
  description = "The IP addresses of the VMs/Containers (if available)"
  value       = concat(module.vm_pack_container[*].vm_ip_address, module.vm_pack_vm[*].vm_ip_address)
}

output "vm_mac_addresses" {
  description = "The MAC addresses of the VMs/Containers' primary network interfaces"
  value       = concat(module.vm_pack_container[*].vm_mac_address, module.vm_pack_vm[*].vm_mac_address)
}

output "vm_ssh_connections" {
  description = "SSH connection information for the VMs/Containers"
  value       = concat(module.vm_pack_container[*].vm_ssh_connection, module.vm_pack_vm[*].vm_ssh_connection)
}

output "vm_template_used" {
  description = "The template used to create these VMs"
  value       = var.template_name
}

output "vm_resource_summary" {
  description = "Summary of VM pack resources"
  value = {
    vm_count = var.vm_count
    cores_per_vm = var.cores
    memory_per_vm = var.memory
    disk_per_vm = var.disk_size
    storage = "local-lvm"
    start_vmid = var.start_vmid
    base_name = var.base_name
  }
}

output "vm_pack_details" {
  description = "Detailed information about each VM/Container in the pack"
  value = concat(
    [
      for i, vm in module.vm_pack_container : {
        index = i
        name = vm.vm_name
        id = vm.vm_id
        ip = vm.vm_ip_address
        mac = vm.vm_mac_address
        ssh_connection = vm.vm_ssh_connection
      }
    ],
    [
      for i, vm in module.vm_pack_vm : {
        index = i
        name = vm.vm_name
        id = vm.vm_id
        ip = vm.vm_ip_address
        mac = vm.vm_mac_address
        ssh_connection = vm.vm_ssh_connection
      }
    ]
  )
} 