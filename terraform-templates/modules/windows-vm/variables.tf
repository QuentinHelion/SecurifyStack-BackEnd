# Required Variables
variable "vm_name" {
  description = "Name of the Windows VM"
  type        = string
  validation {
    condition     = can(regex("^[a-zA-Z0-9-]+$", var.vm_name)) && length(var.vm_name) <= 64
    error_message = "VM name must contain only alphanumeric characters and hyphens, and be max 64 characters."
  }
}

variable "vm_id" {
  description = "VMID for the Windows VM (100-999999)"
  type        = number
  validation {
    condition     = var.vm_id >= 100 && var.vm_id <= 999999
    error_message = "VMID must be between 100 and 999999."
  }
}

variable "proxmox_node" {
  description = "Proxmox node name"
  type        = string
}

variable "template_name" {
  description = "Windows VM template name"
  type        = string
  validation {
    condition     = length(var.template_name) > 0
    error_message = "Template name cannot be empty."
  }
}

# User Configuration
variable "username" {
  description = "Username for the Windows VM"
  type        = string
  default     = "Administrator"
}

variable "password" {
  description = "Password for the Windows VM"
  type        = string
  default     = "rootroot"
  sensitive   = true
}

# VM Configuration
variable "cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 2
  validation {
    condition     = var.cores >= 1 && var.cores <= 128
    error_message = "CPU cores must be between 1 and 128."
  }
}

variable "sockets" {
  description = "Number of CPU sockets"
  type        = number
  default     = 1
  validation {
    condition     = var.sockets >= 1 && var.sockets <= 16
    error_message = "CPU sockets must be between 1 and 16."
  }
}

variable "memory" {
  description = "Memory in MB"
  type        = number
  default     = 2048
  validation {
    condition     = var.memory >= 512 && var.memory <= 524288
    error_message = "Memory must be between 512MB and 512GB."
  }
}

variable "cpu_type" {
  description = "CPU type"
  type        = string
  default     = "host"
  validation {
    condition     = contains(["host", "kvm64", "kvm32", "qemu64", "qemu32", "pentium3", "n270", "athlon", "phenom", "coreduo", "core2duo", "qemu64", "kvm64", "kvm32", "pentium2", "pentium3", "486", "coreduo", "n270", "athlon", "phenom", "core2duo", "pentium", "pentium2", "pentium3", "486", "coreduo", "n270", "athlon", "phenom", "core2duo"], var.cpu_type)
    error_message = "CPU type must be a valid Proxmox CPU type."
  }
}

variable "bios" {
  description = "BIOS type"
  type        = string
  default     = "seabios"
  validation {
    condition     = contains(["seabios", "ovmf"], var.bios)
    error_message = "BIOS must be either 'seabios' or 'ovmf'."
  }
}

variable "numa_enabled" {
  description = "Enable NUMA"
  type        = bool
  default     = false
}

# Disk Configuration
variable "disk_size" {
  description = "Disk size in GB"
  type        = number
  default     = 40
  validation {
    condition     = var.disk_size >= 1 && var.disk_size <= 16384
    error_message = "Disk size must be between 1GB and 16TB."
  }
}

variable "disk_type" {
  description = "Disk type"
  type        = string
  default     = "scsi"
  validation {
    condition     = contains(["ide", "sata", "scsi", "virtio"], var.disk_type)
    error_message = "Disk type must be one of: ide, sata, scsi, virtio."
  }
}

variable "storage_pool" {
  description = "Storage pool name"
  type        = string
  default     = "local-lvm"
}

variable "disk_iothread" {
  description = "Enable disk I/O thread"
  type        = bool
  default     = false
}

variable "disk_ssd" {
  description = "Mark disk as SSD"
  type        = bool
  default     = false
}

variable "disk_discard" {
  description = "Enable discard"
  type        = bool
  default     = false
}

# Network Configuration
variable "network_model" {
  description = "Network model"
  type        = string
  default     = "virtio"
  validation {
    condition     = contains(["e1000", "e1000-82540em", "e1000-82544gc", "e1000-82545em", "i82551", "i82557b", "i82559er", "ne2k_isa", "ne2k_pci", "pcnet", "rtl8139", "virtio", "vmxnet3"], var.network_model)
    error_message = "Network model must be a valid Proxmox network model."
  }
}

variable "network_bridge" {
  description = "Network bridge"
  type        = string
  default     = "vmbr0"
}

variable "network_tag" {
  description = "VLAN tag (0 for no tag)"
  type        = number
  default     = 0
  validation {
    condition     = var.network_tag >= 0 && var.network_tag <= 4094
    error_message = "VLAN tag must be between 0 and 4094."
  }
}

variable "network_firewall" {
  description = "Enable firewall on network interface"
  type        = bool
  default     = false
}

variable "network_config" {
  description = "Network configuration type (dhcp or static)"
  type        = string
  default     = "dhcp"
  validation {
    condition     = contains(["dhcp", "static"], var.network_config)
    error_message = "Network config must be either 'dhcp' or 'static'."
  }
}

variable "ip_address" {
  description = "Static IP address (required if network_config is static)"
  type        = string
  default     = ""
  validation {
    condition = var.ip_address == "" || can(cidrhost("${var.ip_address}/32", 0))
    error_message = "IP address must be a valid IPv4 address."
  }
}

variable "subnet_mask" {
  description = "Subnet mask in CIDR notation"
  type        = string
  default     = "24"
  validation {
    condition     = can(regex("^([0-9]|[1-2][0-9]|3[0-2])$", var.subnet_mask))
    error_message = "Subnet mask must be a valid CIDR notation (0-32)."
  }
}

variable "gateway" {
  description = "Gateway IP address"
  type        = string
  default     = ""
  validation {
    condition = var.gateway == "" || can(cidrhost("${var.gateway}/32", 0))
    error_message = "Gateway must be a valid IPv4 address."
  }
}

variable "nameserver" {
  description = "DNS nameserver"
  type        = string
  default     = "8.8.8.8"
  validation {
    condition = can(cidrhost("${var.nameserver}/32", 0))
    error_message = "Nameserver must be a valid IPv4 address."
  }
}

variable "search_domain" {
  description = "DNS search domain"
  type        = string
  default     = ""
}

# VM Settings
variable "start_on_boot" {
  description = "Start VM on boot"
  type        = bool
  default     = true
}

variable "protection" {
  description = "Protection flag"
  type        = bool
  default     = false
}

variable "tablet" {
  description = "Enable tablet pointer"
  type        = bool
  default     = false
}

variable "boot_order" {
  description = "Boot order"
  type        = string
  default     = "order=scsi0;net0"
}

variable "qemu_agent" {
  description = "QEMU agent"
  type        = number
  default     = 0
  validation {
    condition     = var.qemu_agent >= 0 && var.qemu_agent <= 1
    error_message = "QEMU agent must be 0 or 1."
  }
}

variable "automatic_reboot" {
  description = "Automatic reboot"
  type        = bool
  default     = false
}

variable "full_clone" {
  description = "Full clone"
  type        = bool
  default     = true
}

# Windows-specific settings
variable "balloon_memory" {
  description = "Balloon memory"
  type        = number
  default     = 0
  validation {
    condition     = var.balloon_memory >= 0 && var.balloon_memory <= 524288
    error_message = "Balloon memory must be between 0MB and 512GB."
  }
}

# Tags
variable "tags" {
  description = "Tags for the Windows VM"
  type        = string
  default     = ""
} 