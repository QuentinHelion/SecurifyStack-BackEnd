# Required Variables
variable "vm_name" {
  description = "Name of the container (hostname)"
  type        = string
  validation {
    condition     = can(regex("^[a-zA-Z0-9-]+$", var.vm_name)) && length(var.vm_name) <= 64
    error_message = "Container name must contain only alphanumeric characters and hyphens, and be max 64 characters."
  }
}

variable "vm_id" {
  description = "VMID for the container (100-999999)"
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
  description = "Container template file name"
  type        = string
  validation {
    condition     = length(var.template_name) > 0
    error_message = "Template name cannot be empty."
  }
}

# User Configuration
variable "username" {
  description = "Username for the container"
  type        = string
  default     = "root"
}

variable "password" {
  description = "Password for the container"
  type        = string
  default     = "rootroot"
  sensitive   = true
}

# Container Configuration
variable "cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 1
  validation {
    condition     = var.cores >= 1 && var.cores <= 128
    error_message = "CPU cores must be between 1 and 128."
  }
}

variable "memory" {
  description = "Memory in MB"
  type        = number
  default     = 512
  validation {
    condition     = var.memory >= 16 && var.memory <= 524288
    error_message = "Memory must be between 16MB and 512GB."
  }
}

variable "swap" {
  description = "Swap in MB"
  type        = number
  default     = 512
  validation {
    condition     = var.swap >= 0 && var.swap <= 524288
    error_message = "Swap must be between 0MB and 512GB."
  }
}

variable "architecture" {
  description = "Container architecture"
  type        = string
  default     = "amd64"
  validation {
    condition     = contains(["amd64", "i386", "arm64", "armhf"], var.architecture)
    error_message = "Architecture must be one of: amd64, i386, arm64, armhf."
  }
}

variable "os_type" {
  description = "Operating system type"
  type        = string
  default     = "unmanaged"
  validation {
    condition     = contains(["unmanaged", "debian", "ubuntu", "centos", "fedora", "opensuse", "archlinux", "alpine", "gentoo"], var.os_type)
    error_message = "OS type must be one of: unmanaged, debian, ubuntu, centos, fedora, opensuse, archlinux, alpine, gentoo."
  }
}

# Storage Configuration
variable "disk_size" {
  description = "Root filesystem size in GB"
  type        = number
  default     = 8
  validation {
    condition     = var.disk_size >= 1 && var.disk_size <= 16384
    error_message = "Disk size must be between 1GB and 16TB."
  }
}

variable "storage_pool" {
  description = "Storage pool name"
  type        = string
  default     = "local-lvm"
}

# Network Configuration
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

# SSH Configuration
variable "ssh_keys" {
  description = "SSH public keys (one per line)"
  type        = string
  default     = ""
  sensitive   = true
}

# Container Settings
variable "unprivileged" {
  description = "Create unprivileged container"
  type        = bool
  default     = true
}

variable "start_on_creation" {
  description = "Start container after creation"
  type        = bool
  default     = true
}

variable "start_on_boot" {
  description = "Start container on boot"
  type        = bool
  default     = true
}

variable "protection" {
  description = "Protection flag"
  type        = bool
  default     = false
}

# Console Settings
variable "console_enabled" {
  description = "Enable console"
  type        = bool
  default     = true
}

variable "tty_count" {
  description = "Number of TTYs"
  type        = number
  default     = 2
  validation {
    condition     = var.tty_count >= 0 && var.tty_count <= 6
    error_message = "TTY count must be between 0 and 6."
  }
}

variable "console_mode" {
  description = "Console mode"
  type        = string
  default     = "tty"
  validation {
    condition     = contains(["tty", "console"], var.console_mode)
    error_message = "Console mode must be either 'tty' or 'console'."
  }
}

# Container Features
variable "features_fuse" {
  description = "Enable FUSE"
  type        = bool
  default     = false
}

variable "features_keyctl" {
  description = "Enable keyctl"
  type        = bool
  default     = false
}

variable "features_mount" {
  description = "Enable mount"
  type        = bool
  default     = false
}

variable "features_nesting" {
  description = "Enable nesting"
  type        = bool
  default     = false
}

# Tags
variable "tags" {
  description = "Tags for the container"
  type        = string
  default     = ""
} 