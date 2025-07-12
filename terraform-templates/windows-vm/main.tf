# Terraform configuration for Windows VM deployment
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

# Create Windows VM using module
module "windows_vm" {
  source = "./modules/windows-vm"
  
  # Required variables
  vm_name       = var.vm_name
  vm_id         = var.vm_id
  proxmox_node  = var.proxmox_node
  template_name = var.template_name
  
  # VM Configuration
  cores     = var.cores
  sockets   = var.sockets
  memory    = var.memory
  cpu_type  = var.cpu_type
  bios      = var.bios
  numa_enabled = var.numa_enabled
  
  # Disk Configuration
  disk_size     = var.disk_size
  disk_type     = var.disk_type
  storage_pool  = var.storage_pool
  disk_iothread = var.disk_iothread
  disk_ssd      = var.disk_ssd
  disk_discard  = var.disk_discard
  
  # Network Configuration
  network_model    = var.network_model
  network_bridge   = var.network_bridge
  network_tag      = var.network_tag
  network_firewall = var.network_firewall
  network_config   = var.network_config
  ip_address       = var.ip_address
  subnet_mask      = var.subnet_mask
  gateway          = var.gateway
  nameserver       = var.nameserver
  
  # User Configuration
  username  = var.username
  
  # VM Settings
  start_on_boot     = var.start_on_boot
  protection        = var.protection
  tablet            = var.tablet
  boot_order        = var.boot_order
  qemu_agent        = var.qemu_agent
  automatic_reboot  = var.automatic_reboot
  full_clone        = var.full_clone
  tags              = var.tags
  
  # Windows-specific settings
  balloon_memory = var.balloon_memory
} 