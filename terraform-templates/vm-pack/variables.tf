# Proxmox Provider Variables
variable "proxmox_server" {
  description = "Proxmox server hostname or IP address"
  type        = string
}

variable "proxmox_token" {
  description = "Proxmox API token in format user@realm!tokenid=secret"
  type        = string
  sensitive   = true
}

variable "proxmox_node" {
  description = "Proxmox node name"
  type        = string
}

variable "proxmox_tls_insecure" {
  description = "Disable TLS verification for Proxmox API"
  type        = bool
  default     = true
}

# VM Pack Configuration Variables
variable "base_name" {
  description = "Base name for the VM pack"
  type        = string
}

variable "vm_count" {
  description = "Number of containers to create"
  type        = number
  default     = 1
  validation {
    condition     = var.vm_count >= 1 && var.vm_count <= 10
    error_message = "Container count must be between 1 and 10."
  }
}

variable "start_vmid" {
  description = "Starting VMID for the container pack"
  type        = number
  default     = 5000
  validation {
    condition     = var.start_vmid >= 100 && var.start_vmid <= 999999
    error_message = "Start VMID must be between 100 and 999999."
  }
}

variable "template_name" {
  description = "Container template to use"
  type        = string
}

# Container Configuration Variables
variable "cores" {
  description = "Number of CPU cores per container"
  type        = number
  default     = 1
}

variable "memory" {
  description = "Memory in MB per container"
  type        = number
  default     = 512
}

variable "swap" {
  description = "Swap in MB per container"
  type        = number
  default     = 512
}

# Storage Configuration
variable "disk_size" {
  description = "Root filesystem size in GB per container"
  type        = number
  default     = 8
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
}

variable "network_firewall" {
  description = "Enable firewall on network interface"
  type        = bool
  default     = false
}

variable "nameserver" {
  description = "DNS nameserver"
  type        = string
  default     = "8.8.8.8"
}

# User Configuration
variable "username" {
  description = "Username for the containers"
  type        = string
  default     = "root"
}

variable "password" {
  description = "Password for the containers"
  type        = string
  default     = "rootroot"
  sensitive   = true
}

variable "ssh_keys" {
  description = "SSH public keys"
  type        = string
  default     = ""
  sensitive   = true
}

# Container Settings
variable "start_on_boot" {
  description = "Start container on boot"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags for the containers"
  type        = string
  default     = ""
} 