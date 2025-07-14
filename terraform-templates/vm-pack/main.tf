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

# Determine if template is for container or VM based on template name
locals {
  is_container_template = can(regex(".*\\.(tar\\.zst|tar\\.gz|tar\\.xz)$", var.template_name))
  
  # Detect OS type based on template name
  detected_os_type = var.os_type == "auto" ? (
    can(regex(".*debian.*", lower(var.template_name)) ? "debian" : (
      can(regex(".*ubuntu.*", lower(var.template_name)) ? "ubuntu" : "unmanaged"
    ))
  ) : var.os_type
}

# Create multiple containers using a loop (for container templates)
module "vm_pack_container" {
  source = "./modules/linux-ct"
  count  = local.is_container_template ? var.vm_count : 0
  
  # Required variables
  vm_name       = replace("${var.base_name}-${count.index + 1}", " ", "-")
  vm_id         = var.start_vmid + count.index
  proxmox_node  = var.proxmox_node
  template_name = var.template_name
  
  # User Configuration
  username = var.username
  ssh_keys = var.ssh_keys
  
  # Common Configuration
  cores  = var.cores
  memory = var.memory
  
  # Container-specific variables
  swap         = 512
  architecture = "amd64"
  os_type      = local.detected_os_type
  
  # Disk Configuration
  disk_size    = var.disk_size
  storage_pool = "local-lvm"
  
  # Network Configuration
  network_bridge   = var.network_bridge
  network_tag      = var.network_tag
  network_firewall = false
  network_config   = "dhcp"
  ip_address       = ""
  subnet_mask      = "24"
  gateway          = var.gateway
  nameserver       = var.nameserver
  
  # Container-specific settings
  unprivileged     = true
  start_on_creation = true
  start_on_boot    = false
  protection       = false
  console_enabled  = true
  tty_count        = 2
  console_mode     = "tty"
  features_nesting = true
  
  tags = ""
}

# Create multiple VMs using a loop (for VM templates)
module "vm_pack_vm" {
  source = "./modules/linux-vm"
  count  = local.is_container_template ? 0 : var.vm_count
  
  # Required variables
  vm_name       = replace("${var.base_name}-${count.index + 1}", " ", "-")
  vm_id         = var.start_vmid + count.index
  proxmox_node  = var.proxmox_node
  template_name = var.template_name
  
  # User Configuration
  username = var.username
  ssh_keys = var.ssh_keys
  
  # Common Configuration
  cores  = var.cores
  memory = var.memory
  
  # VM-specific variables
  sockets      = 1
  cpu_type     = "host"
  bios         = "seabios"
  numa_enabled = false
  os_type      = local.detected_os_type
  
  # Disk Configuration
  disk_size     = var.disk_size
  storage_pool  = "local-lvm"
  disk_type     = "scsi"
  disk_iothread = false
  disk_ssd      = false
  disk_discard  = false
  
  # Network Configuration
  network_bridge   = var.network_bridge
  network_tag      = var.network_tag
  network_firewall = false
  network_config   = "dhcp"
  ip_address       = ""
  subnet_mask      = "24"
  gateway          = var.gateway
  nameserver       = var.nameserver
  network_model    = "virtio"
  search_domain    = ""
  
  # VM-specific settings
  start_on_boot     = false
  tablet            = true
  boot_order        = "cdn"
  qemu_agent        = 1
  automatic_reboot  = false
  full_clone        = true
  tags              = ""
} 