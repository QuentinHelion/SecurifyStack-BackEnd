# Terraform configuration for VM Pack deployment
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "~> 2.9.14"
    }
  }
}

provider "proxmox" {
  pm_api_url          = "https://${var.proxmox_server}:8006/api2/json"
  pm_api_token_id     = split("=", var.proxmox_token)[0]
  pm_api_token_secret = split("=", var.proxmox_token)[1]
  pm_tls_insecure     = var.proxmox_tls_insecure
}

# Create multiple Linux containers using a loop
resource "proxmox_lxc" "container" {
  count = var.vm_count
  
  # Container Identity
  hostname     = replace("${var.base_name}-${count.index + 1}", " ", "-")
  vmid         = var.start_vmid + count.index
  target_node  = var.proxmox_node
  ostemplate   = "local:vztmpl/${var.template_name}"
  
  # Container Configuration
  cores  = var.cores
  memory = var.memory
  swap   = var.swap
  
  # Root filesystem
  rootfs {
    storage = var.storage_pool
    size    = "${var.disk_size}G"
  }
  
  # Network Configuration
  network {
    name     = "eth0"
    bridge   = var.network_bridge
    tag      = var.network_tag != 0 ? var.network_tag : null
    ip       = "dhcp"
    firewall = var.network_firewall
  }
  
  # SSH Configuration
  ssh_public_keys = var.ssh_keys != "" ? var.ssh_keys : null
  
  # User Configuration
  password = var.password != "" ? var.password : null
  
  # DNS Configuration
  nameserver = var.nameserver
  
  # Container Settings
  onboot = var.start_on_boot
  
  # Tags
  tags = var.tags
  
  lifecycle {
    ignore_changes = [
      # Ignore changes to these attributes to prevent unnecessary recreation
      ssh_public_keys,
    ]
  }
} 