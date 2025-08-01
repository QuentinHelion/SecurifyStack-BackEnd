# Windows VM Module
terraform {
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "~> 2.9.14"
    }
  }
}

resource "proxmox_vm_qemu" "vm" {
  name        = var.vm_name
  vmid        = var.vm_id
  target_node = var.proxmox_node
  clone       = var.template_name
  full_clone  = var.full_clone
  
  # VM Configuration
  cores   = var.cores
  sockets = var.sockets
  memory  = var.memory
  cpu     = var.cpu_type
  bios    = var.bios
  numa    = var.numa_enabled
  
  # Disk Configuration
  disk {
    type    = var.disk_type
    storage = var.storage_pool
    size    = "${var.disk_size}G"
    iothread = var.disk_iothread
    ssd     = var.disk_ssd
    discard = var.disk_discard
  }
  
  # Network Configuration
  network {
    model    = var.network_model
    bridge   = var.network_bridge
    tag      = var.network_tag != 0 ? var.network_tag : null
    firewall = var.network_firewall
  }
  
  # IP Configuration (if static)
  ipconfig0 = var.network_config == "static" ? "ip=${var.ip_address}/${var.subnet_mask},gw=${var.gateway}" : null
  
  # User Configuration
  ciuser = var.username
  cipassword = var.password != "" ? var.password : null
  
  # VM Settings
  onboot        = var.start_on_boot
  protection    = var.protection
  tablet        = var.tablet
  boot          = var.boot_order
  agent         = var.qemu_agent
  automatic_reboot = var.automatic_reboot
  
  # Windows-specific settings
  balloon = var.balloon_memory
  
  # Tags for organization
  tags = var.tags != "" ? var.tags : null
  
  lifecycle {
    ignore_changes = [
      # Ignore changes to these attributes to prevent unnecessary recreation
      balloon,
    ]
  }
} 