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
  description = "Number of VMs to create"
  type        = number
  default     = 1
  validation {
    condition     = var.vm_count >= 1 && var.vm_count <= 10
    error_message = "VM count must be between 1 and 10."
  }
}

variable "start_vmid" {
  description = "Starting VMID for the VM pack"
  type        = number
  default     = 5000
  validation {
    condition     = var.start_vmid >= 100 && var.start_vmid <= 999999
    error_message = "Start VMID must be between 100 and 999999."
  }
}

variable "template_name" {
  description = "Template to clone from"
  type        = string
}

# VM Configuration Variables
variable "cores" {
  description = "Number of CPU cores per VM"
  type        = number
  default     = 2
}

variable "memory" {
  description = "Memory in MB per VM"
  type        = number
  default     = 2048
}

# Disk Configuration
variable "disk_size" {
  description = "Disk size in GB per VM"
  type        = number
  default     = 20
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

variable "gateway" {
  description = "Gateway IP address"
  type        = string
  default     = "192.168.1.1"
}

variable "nameserver" {
  description = "DNS nameserver"
  type        = string
  default     = "8.8.8.8"
}

# User Configuration
variable "username" {
  description = "Username for the VMs"
  type        = string
  default     = "user"
}

variable "ssh_keys" {
  description = "SSH public keys"
  type        = string
  default     = ""
  sensitive   = true
}

variable "os_type" {
  description = "Operating system type"
  type        = string
  default     = "auto"  # Auto-detect based on template
} 