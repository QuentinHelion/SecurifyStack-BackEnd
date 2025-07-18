# Linux Container Module
terraform {
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "~> 2.9.14"
    }
  }
}

resource "proxmox_lxc" "container" {
  hostname     = var.vm_name
  vmid         = var.vm_id
  target_node  = var.proxmox_node
  ostemplate   = "local:vztmpl/${var.template_name}"
  
  # Container Configuration
  cores       = var.cores
  memory      = var.memory
  swap        = var.swap
  
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
    ip       = var.network_config == "dhcp" ? "dhcp" : "${var.ip_address}/${var.subnet_mask}"
    gw       = var.network_config == "dhcp" ? null : var.gateway
    firewall = var.network_firewall
  }
  
  # SSH Configuration
  ssh_public_keys = var.ssh_keys != "" ? var.ssh_keys : null
  
  # User Configuration
  password = var.password != "" ? var.password : null
  
  # DNS Configuration
  nameserver   = var.nameserver


  lifecycle {
    ignore_changes = [
      # Ignore changes to these attributes to prevent unnecessary recreation
      ssh_public_keys,
    ]
  }
} 