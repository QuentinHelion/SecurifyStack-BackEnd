# This module provides the shared Proxmox provider configuration
# It should be called by other modules to ensure consistent provider configuration

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
  pm_api_token_id     = split("!", var.proxmox_token)[0]
  pm_api_token_secret = split("=", split("!", var.proxmox_token)[1])[1]
  pm_tls_insecure     = var.proxmox_tls_insecure
  pm_parallel         = var.proxmox_parallel
  pm_timeout          = var.proxmox_timeout
  pm_debug            = var.proxmox_debug
}

# No resources are created in this module
# It only provides the provider configuration for other modules 