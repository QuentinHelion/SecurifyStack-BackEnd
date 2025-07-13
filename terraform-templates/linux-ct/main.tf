# Terraform configuration for Linux Container deployment
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

# Create Linux Container using module
module "linux_ct" {
  source = "./modules/linux-ct"
  
  # Required variables
  vm_name       = var.vm_name
  vm_id         = var.vm_id
  proxmox_node  = var.proxmox_node
  template_name = var.template_name
  
  # User Configuration
  username = var.username
  
  # Container Configuration
  cores        = var.cores
  memory       = var.memory
  swap         = var.swap
  architecture = var.architecture
  os_type      = var.os_type
  
  # Storage Configuration
  disk_size    = var.disk_size
  storage_pool = var.storage_pool
  
  # Network Configuration
  network_bridge   = var.network_bridge
  network_tag      = var.network_tag
  network_firewall = var.network_firewall
  network_config   = var.network_config
  ip_address       = var.ip_address
  subnet_mask      = var.subnet_mask
  gateway          = var.gateway
  nameserver       = var.nameserver
  
  # SSH Configuration
  ssh_keys = var.ssh_keys
  
  # Container Settings
  unprivileged      = var.unprivileged
  start_on_creation = var.start_on_creation
  start_on_boot     = var.start_on_boot
  protection        = var.protection
  
  # Console Settings
  console_enabled = var.console_enabled
  tty_count       = var.tty_count
  console_mode    = var.console_mode
  
  # Container Features
  features_nesting = var.features_nesting
  
  # Tags
  tags = var.tags
} 