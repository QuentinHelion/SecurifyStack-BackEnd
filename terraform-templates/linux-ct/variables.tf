# Proxmox Provider Variables (passed to shared module)
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

# Container Configuration Variables
variable "vm_name" {
  description = "Name of the container"
  type        = string
}

variable "vm_id" {
  description = "VMID for the container"
  type        = number
}

variable "template_name" {
  description = "Container template to use"
  type        = string
}

variable "username" {
  description = "Username for the container"
  type        = string
  default     = "root"
}

variable "password" {
  description = "Password for the user"
  type        = string
  default     = "rootroot"
  sensitive   = true
}

variable "cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 1
}

variable "memory" {
  description = "Memory in MB"
  type        = number
  default     = 512
}

variable "swap" {
  description = "Swap in MB"
  type        = number
  default     = 512
}

variable "architecture" {
  description = "Container architecture"
  type        = string
  default     = "amd64"
}

variable "os_type" {
  description = "Operating system type"
  type        = string
  default     = "unmanaged"
}

# Storage Configuration
variable "disk_size" {
  description = "Root filesystem size in GB"
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
}

variable "ip_address" {
  description = "Static IP address (required if network_config is static)"
  type        = string
  default     = ""
}

variable "subnet_mask" {
  description = "Subnet mask in CIDR notation"
  type        = string
  default     = "24"
}

variable "gateway" {
  description = "Gateway IP address"
  type        = string
  default     = ""
}

variable "mac_address" {
  description = "MAC address for the container"
  type        = string
  default     = ""
}

variable "nameserver" {
  description = "DNS nameserver"
  type        = string
  default     = "8.8.8.8"
}

variable "search_domain" {
  description = "DNS search domain"
  type        = string
  default     = ""
}

# SSH Configuration
variable "ssh_keys" {
  description = "SSH public keys"
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

variable "startup_order" {
  description = "Startup order"
  type        = string
  default     = ""
}

variable "protection" {
  description = "Protection flag"
  type        = bool
  default     = false
}

variable "restore" {
  description = "Restore from backup"
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
}

variable "console_mode" {
  description = "Console mode"
  type        = string
  default     = "tty"
}

# Container Features
variable "features_nesting" {
  description = "Enable nested virtualization"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags for the container"
  type        = string
  default     = ""
}

# Legacy variables for backward compatibility
variable "ssh_key" {
  description = "SSH public key (legacy - use ssh_keys instead)"
  type        = string
  default     = ""
  sensitive   = true
} 