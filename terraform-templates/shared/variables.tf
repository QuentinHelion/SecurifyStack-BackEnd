# Proxmox Provider Configuration Variables
variable "proxmox_server" {
  description = "Proxmox server hostname or IP address"
  type        = string
  validation {
    condition     = can(regex("^[a-zA-Z0-9.-]+$", var.proxmox_server))
    error_message = "Proxmox server must be a valid hostname or IP address."
  }
}

variable "proxmox_token" {
  description = "Proxmox API token in format user@realm!tokenid=secret"
  type        = string
  sensitive   = true
  validation {
    condition     = can(regex("^[^!]+![^=]+=.+$", var.proxmox_token))
    error_message = "Proxmox token must be in format user@realm!tokenid=secret."
  }
}

variable "proxmox_node" {
  description = "Proxmox node name where resources will be created"
  type        = string
  validation {
    condition     = length(var.proxmox_node) > 0
    error_message = "Proxmox node name cannot be empty."
  }
}

variable "proxmox_tls_insecure" {
  description = "Disable TLS verification for Proxmox API (not recommended for production)"
  type        = bool
  default     = true
}

variable "proxmox_parallel" {
  description = "Number of parallel API calls to Proxmox"
  type        = number
  default     = 4
  validation {
    condition     = var.proxmox_parallel >= 1 && var.proxmox_parallel <= 10
    error_message = "Proxmox parallel must be between 1 and 10."
  }
}

variable "proxmox_timeout" {
  description = "Timeout for Proxmox API calls in seconds"
  type        = number
  default     = 300
  validation {
    condition     = var.proxmox_timeout >= 30 && var.proxmox_timeout <= 3600
    error_message = "Proxmox timeout must be between 30 and 3600 seconds."
  }
}

variable "proxmox_debug" {
  description = "Enable debug logging for Proxmox provider"
  type        = bool
  default     = false
} 