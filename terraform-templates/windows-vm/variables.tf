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

# VM Configuration Variables
variable "vm_name" {
  description = "Name of the VM"
  type        = string
}

variable "vm_id" {
  description = "VMID for the VM"
  type        = number
}

variable "template_name" {
  description = "Template to clone from"
  type        = string
}

variable "cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 2
}

variable "sockets" {
  description = "Number of CPU sockets"
  type        = number
  default     = 1
}

variable "memory" {
  description = "Memory in MB"
  type        = number
  default     = 2048
}

variable "cpu_type" {
  description = "CPU type"
  type        = string
  default     = "host"
}

variable "bios" {
  description = "BIOS type (seabios or ovmf)"
  type        = string
  default     = "ovmf"
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
  default     = 20
}

variable "disk_type" {
  description = "Disk type (scsi, ide, sata, virtio)"
  type        = string
  default     = "scsi"
}

variable "storage_pool" {
  description = "Storage pool name"
  type        = string
  default     = "local-lvm"
}

variable "disk_iothread" {
  description = "Enable iothread for disk"
  type        = bool
  default     = true
}

variable "disk_ssd" {
  description = "Mark disk as SSD"
  type        = bool
  default     = false
}

variable "disk_discard" {
  description = "Enable discard for disk"
  type        = string
  default     = "on"
}

# Network Configuration
variable "network_model" {
  description = "Network interface model"
  type        = string
  default     = "virtio"
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

# User Configuration
variable "username" {
  description = "Username for the VM"
  type        = string
  default     = "Administrator"
}

variable "password" {
  description = "Password for the user"
  type        = string
  default     = ""
  sensitive   = true
}

# VM Settings
variable "start_on_boot" {
  description = "Start VM on boot"
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

variable "tablet" {
  description = "Enable tablet device"
  type        = bool
  default     = true
}

variable "boot_order" {
  description = "Boot order"
  type        = string
  default     = "c"
}

variable "qemu_agent" {
  description = "Enable QEMU guest agent"
  type        = number
  default     = 1
}

variable "automatic_reboot" {
  description = "Automatically reboot after configuration changes"
  type        = bool
  default     = true
}

variable "full_clone" {
  description = "Create a full clone instead of linked clone"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags for the VM"
  type        = string
  default     = ""
}

# Windows-specific settings
variable "balloon_memory" {
  description = "Enable memory ballooning for Windows VMs"
  type        = bool
  default     = true
} 