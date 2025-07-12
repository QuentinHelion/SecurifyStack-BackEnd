# SecurifyStack Terraform Templates

This directory contains the modular Terraform infrastructure for deploying VMs and containers to Proxmox through the SecurifyStack platform.

## Architecture Overview

The Terraform templates follow a modular architecture with the following structure:

```
terraform-templates/
├── shared/                 # Shared provider configuration
│   ├── provider.tf        # Centralized Proxmox provider
│   └── variables.tf       # Provider-specific variables
├── modules/               # Reusable Terraform modules
│   ├── linux-vm/         # Linux VM module
│   ├── linux-ct/         # Linux Container module
│   └── windows-vm/       # Windows VM module
├── linux-vm/             # Linux VM deployment template
├── linux-ct/             # Linux CT deployment template
└── deployments/          # Individual deployment instances
    └── {machine-id}/     # Per-machine deployment directory
```

## Key Features

### 🔒 Security Best Practices
- **Input Validation**: All variables include comprehensive validation rules
- **Sensitive Data**: SSH keys, passwords, and tokens marked as sensitive
- **Resource Limits**: Validation constraints prevent resource abuse
- **Provider Versioning**: Locked provider versions for consistency

### 🏗️ Modular Design
- **Centralized Provider**: Single provider configuration shared across all deployments
- **Reusable Modules**: Common VM/CT configurations as modules
- **Template System**: Deployment templates that use modules
- **Individual State**: Each deployment maintains its own Terraform state

### 🚀 Production Ready
- **Error Handling**: Comprehensive error messages and validation
- **Lifecycle Management**: Proper resource lifecycle rules
- **Performance Optimized**: Resource allocation based on performance tiers
- **Network Flexibility**: Support for both DHCP and static IP configuration

## Module Documentation

### Shared Provider (`shared/`)

Centralized Proxmox provider configuration with:
- Version constraints (`>= 1.0`)
- Provider version pinning (`~> 2.9.14`)
- Configurable connection parameters
- Security best practices

### Linux VM Module (`modules/linux-vm/`)

Creates Linux virtual machines with:
- **Cloud-init support** for automated configuration
- **Flexible networking** (DHCP/Static IP)
- **Performance tiers** (low/medium/high)
- **SSH key management**
- **Resource validation**
- **NUMA support**

### Linux Container Module (`modules/linux-ct/`)

Creates Linux containers with:
- **Unprivileged containers** by default
- **Feature controls** (FUSE, nesting, etc.)
- **Resource limits** and validation
- **Network configuration**
- **SSH access setup**
- **Console management**

### Windows VM Module (`modules/windows-vm/`)

Creates Windows virtual machines with:
- **UEFI/OVMF support** for modern Windows
- **Memory ballooning**
- **Windows-optimized settings**
- **Network driver selection**
- **Password management**
- **Guest agent support**

## Usage Examples

### Deploy a Linux VM

```hcl
module "web_server" {
  source = "../modules/linux-vm"
  
  # Required
  vm_name       = "web-server-01"
  vm_id         = 101
  proxmox_node  = "pve-node1"
  template_name = "ubuntu-22.04-template"
  
  # Resources
  cores   = 4
  memory  = 8192
  disk_size = 40
  
  # Network
  network_config = "static"
  ip_address     = "192.168.1.100"
  subnet_mask    = "24"
  gateway        = "192.168.1.1"
  
  # User
  username = "admin"
  ssh_keys = file("~/.ssh/id_rsa.pub")
}
```

### Deploy a Linux Container

```hcl
module "database_ct" {
  source = "../modules/linux-ct"
  
  # Required
  vm_name       = "database-ct-01"
  vm_id         = 201
  proxmox_node  = "pve-node1"
  template_name = "debian-12-standard_12.2-1_amd64.tar.zst"
  
  # Resources
  cores  = 2
  memory = 4096
  swap   = 1024
  disk_size = 20
  
  # Features
  features_nesting = true
  unprivileged     = true
}
```

### Deploy a Windows VM

```hcl
module "windows_server" {
  source = "../modules/windows-vm"
  
  # Required
  vm_name       = "win-server-01"
  vm_id         = 301
  proxmox_node  = "pve-node1"
  template_name = "windows-server-2022-template"
  
  # Resources
  cores   = 4
  memory  = 8192
  disk_size = 80
  
  # Windows-specific
  bios     = "ovmf"
  username = "Administrator"
  password = var.admin_password
}
```

## Variable Reference

### Common Variables (All Modules)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `vm_name` | string | - | Name of the VM/Container |
| `vm_id` | number | - | VMID (100-999999) |
| `proxmox_node` | string | - | Proxmox node name |
| `template_name` | string | - | Template to clone from |

### Resource Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `cores` | number | 2 | CPU cores (1-128) |
| `memory` | number | 2048 | Memory in MB |
| `disk_size` | number | 20 | Disk size in GB |
| `storage_pool` | string | "local-lvm" | Storage pool |

### Network Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `network_config` | string | "dhcp" | "dhcp" or "static" |
| `network_bridge` | string | "vmbr0" | Network bridge |
| `network_tag` | number | 0 | VLAN tag (0=none) |
| `ip_address` | string | "" | Static IP address |
| `subnet_mask` | string | "24" | CIDR subnet mask |
| `gateway` | string | "" | Gateway IP |

## Performance Tiers

The deployment service automatically maps performance tiers to resources:

| Tier | CPU Cores | Memory (MB) | Disk (GB) |
|------|-----------|-------------|-----------|
| Low | 1 | 1024 | 20 |
| Medium | 2 | 2048 | 40 |
| High | 4 | 4096 | 80 |

## Deployment Process

1. **Template Selection**: Based on machine type and OS version
2. **Module Instantiation**: Templates call appropriate modules
3. **Variable Generation**: Backend generates `terraform.tfvars`
4. **Resource Creation**: Terraform deploys to Proxmox
5. **State Management**: Each deployment maintains isolated state

## File Structure per Deployment

Each deployed machine gets its own directory:

```
deployments/{machine-id}/
├── main.tf              # Template calling modules
├── variables.tf         # Variable definitions
├── outputs.tf           # Output definitions
├── terraform.tfvars     # Generated variable values
├── terraform.tfstate    # Terraform state
├── machine_config.json  # Original machine config
├── shared/              # Symlink to shared provider
└── modules/             # Symlink to modules
```

## Security Considerations

### Sensitive Variables
- API tokens
- SSH private keys
- User passwords
- All marked with `sensitive = true`

### Validation Rules
- VMID ranges (100-999999)
- IP address format validation
- Resource limit constraints
- Template name validation

### Network Security
- Optional firewall rules
- VLAN tagging support
- Bridge isolation
- DNS configuration

## Troubleshooting

### Common Issues

1. **Module Not Found**
   ```bash
   # Ensure symlinks exist
   ls -la deployments/{machine-id}/modules
   ls -la deployments/{machine-id}/shared
   ```

2. **Provider Initialization**
   ```bash
   # Re-initialize if needed
   cd deployments/{machine-id}
   terraform init -upgrade
   ```

3. **State Lock Issues**
   ```bash
   # Force unlock if needed (use carefully)
   terraform force-unlock {lock-id}
   ```

### Debug Mode

Enable debug logging by setting:
```hcl
proxmox_debug = true
```

## Best Practices

### Development
- Always validate templates before deployment
- Use consistent naming conventions
- Document any custom modifications
- Test with small resource allocations first

### Production
- Use full clones for production VMs
- Enable protection on critical VMs
- Implement proper backup strategies
- Monitor resource usage

### Security
- Rotate API tokens regularly
- Use unprivileged containers when possible
- Implement network segmentation
- Regular security updates

## Contributing

When adding new modules or templates:

1. Follow the existing variable naming conventions
2. Include comprehensive validation rules
3. Add proper documentation
4. Test with different configurations
5. Update this README if needed

## Support

For issues with the Terraform templates:
1. Check the deployment logs in the backend
2. Verify Proxmox connectivity and permissions
3. Validate template availability
4. Review variable values in `terraform.tfvars` 