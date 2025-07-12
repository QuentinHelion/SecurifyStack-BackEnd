output "ct_id" {
  description = "The VMID of the created container"
  value       = module.linux_ct.ct_id
}

output "ct_name" {
  description = "The hostname of the created container"
  value       = module.linux_ct.ct_name
}

output "ct_node" {
  description = "The Proxmox node where the container is running"
  value       = module.linux_ct.ct_node
}

output "ct_status" {
  description = "The status of the container"
  value       = module.linux_ct.ct_status
}

output "ct_template_used" {
  description = "The template used to create this container"
  value       = module.linux_ct.ct_template_used
}

output "ct_network_info" {
  description = "Network configuration of the container"
  value       = module.linux_ct.ct_network_info
}

output "ct_resource_summary" {
  description = "Summary of container resources"
  value       = module.linux_ct.ct_resource_summary
}

output "ct_features" {
  description = "Container features configuration"
  value       = module.linux_ct.ct_features
} 