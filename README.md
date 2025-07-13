# SecurifyStack-BackEnd

## First-Time Setup: Generating the Master Key

This application uses an encrypted file (`infrastructure/persistence/config.json`) to store configuration settings managed via the UI. To encrypt this file, a `MASTER_KEY` is required. This key **must** be generated once during the initial setup.

1.  **Navigate to the project directory:**
    ```sh
    cd /path/to/SecurifyStack-BackEnd
    ```

2.  **Run the key generation command:**
    ```sh
    python3 main.py --generate-key
    ```
    This command will create a `.env` file in your project root (if it doesn't exist) and add a secure `MASTER_KEY` to it. It will then exit.

**IMPORTANT:** The `.env` file contains the master secret. Treat it with care, do not commit it to version control, and ensure it is present in the application's environment for it to run.

---

## Setup Instructions

1. **Install dependencies**
   
   It is recommended to use a virtual environment:
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   Create a `.env` file in the project root with the following content:
   ```env
   BACKEND_HOST=0.0.0.0
   BACKEND_PORT=5000
   LDAPS_SERVER=localhost
   LDAPS_SERVER_PORT=389
   ```
   - Change `BACKEND_HOST` and `BACKEND_PORT` to your desired IP and port.
   - Change `LDAPS_SERVER` and `LDAPS_SERVER_PORT` to your LDAP/LDAPS server address and port.

   **To use your new LDAPS server at 192.168.1.36, set these in your .env file:**
   ```env
   LDAPS_SERVER=192.168.1.36
   LDAPS_SERVER_PORT=636
   ```

3. **Run the backend**
   ```sh
   python3 main.py
   ```

---

## Setting up a Test LDAPS Server with Docker

You can use Docker to quickly set up a test LDAP/LDAPS server for development:

1. **Run the OpenLDAP Docker container:**
   ```sh
   docker run --name test-ldap -p 389:389 -p 636:636 \
     -e LDAP_ORGANISATION="TestOrg" \
     -e LDAP_DOMAIN="test.local" \
     -e LDAP_ADMIN_PASSWORD="admin" \
     --detach osixia/openldap:1.5.0
   ```
   - This starts an LDAP server on your network with admin password `admin`.

2. **Find the container host's IP address:**
   ```sh
   hostname -I
   # or
   ip a
   ```
   - Use this IP for `LDAPS_SERVER` in your backend `.env` file.

3. **Configure your backend to use LDAPS:**
   In your backend `.env` file, set:
   ```env
   LDAPS_SERVER=<container_host_ip>
   LDAPS_SERVER_PORT=636
   ```
   - Replace `<container_host_ip>` with the actual IP address.

4. **Add a test user to LDAP:**
   - Create a file named `testuser.ldif` with the following content:
     ```ldif
     dn: uid=testuser,dc=test,dc=local
     objectClass: inetOrgPerson
     uid: testuser
     sn: User
     cn: Test User
     userPassword: testpassword
     ```
   - Copy the file into the container (if created on host):
     ```sh
     docker cp testuser.ldif test-ldap:/testuser.ldif
     docker exec -it test-ldap bash
     ldapadd -x -H ldaps://localhost -D "cn=admin,dc=test,dc=local" -w admin -f /testuser.ldif
     ```
   - Or, create the file directly inside the container using `nano` or `vi` and run the `ldapadd` command above.

5. **Restart your backend** (if you changed the `.env`):
   ```sh
   python3 main.py
   ```

You can now test login with the credentials:
- Username: `testuser`
- Password: `testpassword`

---

## Setting up OpenLDAP with LDAPS (Native Installation)

This section describes how to install and configure OpenLDAP with LDAPS (secure LDAP) on a Linux machine, using a self-signed CA. This is useful for local development, integration testing, or as a reference for production hardening.

### 1. Install OpenLDAP and Utilities

```sh
apt update
apt install slapd ldap-utils openssl -y
```

### Note: Example Answers for slapd Prompts

When running `dpkg-reconfigure slapd` or during initial installation, use these answers for a test setup:

- Omit OpenLDAP server configuration? **No**
- DNS domain name: **test.local**
- Organization name: **TEST Inc**
- Administrator password: **(choose a password you will remember)**
- Database backend: **mdb** (or the default)
- Do you want the database to be removed when slapd is purged? **No**
- Move old database? **Yes** (if prompted)
- Allow LDAPv2 protocol? **No**

This will set your base DN to `dc=test,dc=local` and your admin DN to `cn=admin,dc=test,dc=local`.

### 2. Generate a Self-Signed CA and Server Certificates

```sh
mkdir ~/ldap-certs && cd ~/ldap-certs
openssl req -x509 -newkey rsa:4096 -days 3650 -nodes \
  -keyout ca.key -out ca.crt \
  -subj "/CN=MyLDAP-CA"
openssl req -newkey rsa:4096 -nodes \
  -keyout ldap.key -out ldap.csr \
  -subj "/CN=$(hostname -f)"
openssl x509 -req -in ldap.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out ldap.crt -days 3650
```

### 3. Move Certificates and Set Permissions

```sh
cp ldap.crt /etc/ssl/certs/
cp ca.crt /etc/ssl/certs/
cp ldap.key /etc/ssl/certs/
chown openldap:openldap /etc/ssl/certs/ldap.crt /etc/ssl/certs/ldap.key /etc/ssl/certs/ca.crt
chmod 600 /etc/ssl/certs/ldap.key
chmod 644 /etc/ssl/certs/ldap.crt /etc/ssl/certs/ca.crt
```

### 4. Enable LDAPS in slapd

Edit `/etc/default/slapd` and set:
```
SLAPD_SERVICES="ldap:/// ldaps:/// ldapi:///"
```
Then restart slapd:
```sh
systemctl restart slapd
```

### 5. Configure slapd to Use the Certificates

Create a file called `set-cert.ldif`:
```ldif
dn: cn=config
changetype: modify
replace: olcTLSCACertificateFile
olcTLSCACertificateFile: /etc/ssl/certs/ca.crt
-
replace: olcTLSCertificateKeyFile
olcTLSCertificateKeyFile: /etc/ssl/certs/ldap.key
-
replace: olcTLSCertificateFile
olcTLSCertificateFile: /etc/ssl/certs/ldap.crt
-
replace: olcTLSVerifyClient
olcTLSVerifyClient: never
```
Apply it:
```sh
ldapmodify -Y EXTERNAL -H ldapi:/// -f set-cert.ldif
```

### 6. Restart slapd

```sh
systemctl restart slapd
```

### 7. Test LDAPS

```sh
ldapsearch -H ldaps://localhost -x -b "dc=test,dc=local" -D "cn=admin,dc=test,dc=local" -W
```

If you get a certificate trust error, use:
```sh
LDAPTLS_CACERT=/etc/ssl/certs/ca.crt ldapsearch -H ldaps://localhost -x -b "dc=test,dc=local" -D "cn=admin,dc=test,dc=local" -W
```

### 8. (Optional) Make Your CA Trusted System-Wide

```sh
cp /etc/ssl/certs/ca.crt /usr/local/share/ca-certificates/myldap-ca.crt
update-ca-certificates --fresh
```

Then add this line to `/etc/ldap/ldap.conf` to ensure all LDAP clients use the system CA bundle:
```
TLS_CACERT /etc/ssl/certs/ca-certificates.crt
```

### 9. Create a Test User

Create `testuser.ldif`:
```ldif
dn: uid=testuser,dc=test,dc=local
objectClass: inetOrgPerson
sn: User
cn: Test User
uid: testuser
userPassword: testpassword
```
Add the user:
```sh
ldapadd -x -D "cn=admin,dc=test,dc=local" -W -f testuser.ldif
```

### 10. Test LDAPS Login as Test User

```sh
ldapsearch -H ldaps://localhost -x -b "dc=test,dc=local" -D "uid=testuser,dc=test,dc=local" -w testpassword
```

---

### Troubleshooting

- If you get `ldap_modify: Other (e.g., implementation specific) error (80)`, check for typos in your certificate/key file paths and ensure the files exist and are readable by the `openldap` user:
  ```sh
  ls -l /etc/ssl/certs/ldap.crt /etc/ssl/certs/ldap.key /etc/ssl/certs/ca.crt
  chown openldap:openldap /etc/ssl/certs/ldap.crt /etc/ssl/certs/ldap.key /etc/ssl/certs/ca.crt
  chmod 600 /etc/ssl/certs/ldap.key
  chmod 644 /etc/ssl/certs/ldap.crt /etc/ssl/certs/ca.crt
  ```
- If you use `/etc/ssl/private`, ensure `openldap` can access the directory, or move the key to `/etc/ssl/certs/` or `/etc/ldap/`.
- If you get certificate trust errors, use the `LDAPTLS_CACERT` environment variable or update the system trust store as above.
- Always restart slapd after changing certificate settings.
- For more verbose debugging, add `-d 1` to your `ldapsearch` command.

#### Testing File Permissions as openldap

To verify that the `openldap` user can read the certificate and key files, run:

```sh
su -s /bin/bash openldap
cat /etc/ssl/certs/ldap.crt
cat /etc/ssl/certs/ldap.key
cat /etc/ssl/certs/ca.crt
exit
```

- If you see the file contents, permissions are correct.
- If you see "Permission denied", adjust ownership and permissions as described above.

---

This process was tested and confirmed to work with OpenLDAP 2.5+ on Debian/Ubuntu. For production, use a real CA and secure your key material appropriately.

This repository contains the backend part of the SecurifyStack project.

---

## Exporting the CA Certificate for Client Trust

To allow clients (such as your backend) to trust your LDAPS server, you need to provide them with the CA certificate that signed the server's certificate.

### 1. Locate the CA Certificate on the LDAP Server

If you followed the steps above, your CA certificate is at:
```
/etc/ssl/certs/ca.crt
```

### 2. Export/Copy the CA Certificate

Copy the CA certificate from your LDAP server to your backend server (or any client that needs to trust LDAPS). For example, from the LDAP server:

```sh
scp /etc/ssl/certs/ca.crt user@backend-server:/path/to/ca.crt
```

Or, if you are on the backend server and can SSH to the LDAP server:

```sh
scp user@ldap-server:/etc/ssl/certs/ca.crt /path/to/ca.crt
```

### 3. Use the CA Certificate in the Backend

- Place the CA certificate in a secure location on the backend (e.g., `/etc/ssl/certs/ca.crt` or a project-specific path).
- Configure your backend to use this CA certificate for LDAPS connections. For example, set the appropriate environment variable or config option (such as `LDAPTLS_CACERT` or a library-specific setting).


**Set in your .env file :**
```
LDAPTLS_CACERT=/path/to/ca.crt
```

This ensures your backend trusts the LDAPS server's certificate.

---

## Terraform Infrastructure as Code

SecurifyStack includes a comprehensive Terraform infrastructure system for deploying VMs and containers to Proxmox. The system uses a modular architecture with centralized provider configuration and reusable modules.

### Architecture Overview

```
terraform-templates/
├── modules/               # Reusable Terraform modules
│   ├── linux-vm/         # Linux VM module
│   ├── linux-ct/         # Linux Container module
│   └── windows-vm/       # Windows VM module
├── linux-vm/             # Linux VM deployment template
├── linux-ct/             # Linux CT deployment template
├── windows-vm/           # Windows VM deployment template
├── vm-pack/              # VM Pack deployment template
└── README.md             # Detailed Terraform documentation
```

### Key Features

#### 🔒 Security Best Practices
- **Input Validation**: All variables include comprehensive validation rules
- **Sensitive Data**: SSH keys, passwords, and tokens marked as sensitive
- **Resource Limits**: Validation constraints prevent resource abuse
- **Provider Versioning**: Locked provider versions for consistency

#### 🏗️ Modular Design
- **Provider Configuration**: Each template includes its own provider configuration
- **Reusable Modules**: Common VM/CT configurations as modules
- **Template System**: Deployment templates that use modules
- **Individual State**: Each deployment maintains its own Terraform state

#### 🚀 Production Ready
- **Error Handling**: Comprehensive error messages and validation
- **Lifecycle Management**: Proper resource lifecycle rules
- **Performance Optimized**: Resource allocation based on performance tiers
- **Network Flexibility**: Support for both DHCP and static IP configuration

### Prerequisites

1. **Install Terraform**
   ```sh
   # On Ubuntu/Debian
   wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt update && sudo apt install terraform
   
   # On macOS
   brew install terraform
   ```

2. **Configure Proxmox API Token**
   - Create an API token in your Proxmox web interface
   - Format: `user@realm!tokenid=secret`
   - Ensure the token has appropriate permissions for VM/CT management

3. **Set Environment Variables**
   ```env
   PROXMOX_SERVER=your-proxmox-server.com
   PVEAPITOKEN=user@realm!tokenid=secret
   NODE=your-proxmox-node
   ```

### Deployment Process

The backend automatically handles Terraform deployments through the following process:

1. **Template Selection**: Based on machine type and OS version
2. **Module Instantiation**: Templates call appropriate modules
3. **Variable Generation**: Backend generates `terraform.tfvars`
4. **Symlink Creation**: Links to shared modules and provider
5. **Resource Creation**: Terraform deploys to Proxmox
6. **State Management**: Each deployment maintains isolated state

### API Endpoints

#### Deploy Machines
```http
POST /deploy-machines
Content-Type: application/json

{
  "machines": [
    {
      "id": "linux-server-1",
      "name": "web-server",
      "baseType": "linuxServer",
      "advanced": {
        "type": "vm",
        "os_version": "ubuntu-22.04-template",
        "perf": "medium",
        "ip_mode": "static",
        "ip_address": "192.168.1.100"
      }
    }
  ]
}
```

#### List Deployments
```http
GET /list-deployments
```

#### Destroy Machine
```http
DELETE /destroy-machine/{machine_id}
```

### Module Documentation

#### Linux VM Module (`modules/linux-vm/`)
Creates Linux virtual machines with:
- **Cloud-init support** for automated configuration
- **Flexible networking** (DHCP/Static IP)
- **Performance tiers** (low/medium/high)
- **SSH key management**
- **Resource validation**
- **NUMA support**

#### Linux Container Module (`modules/linux-ct/`)
Creates Linux containers with:
- **Unprivileged containers** by default
- **Feature controls** (FUSE, nesting, etc.)
- **Resource limits** and validation
- **Network configuration**
- **SSH access setup**
- **Console management**

#### Windows VM Module (`modules/windows-vm/`)
Creates Windows virtual machines with:
- **UEFI/OVMF support** for modern Windows
- **Memory ballooning**
- **Windows-optimized settings**
- **Network driver selection**
- **Password management**
- **Guest agent support**

### Usage Examples

#### Deploy a Linux VM
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

#### Deploy a Linux Container
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

#### Deploy a Windows VM
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

### Performance Tiers

The deployment service automatically maps performance tiers to resources:

| Tier | CPU Cores | Memory (MB) | Disk (GB) |
|------|-----------|-------------|-----------|
| Low | 1 | 1024 | 20 |
| Medium | 2 | 2048 | 40 |
| High | 4 | 4096 | 80 |

### Troubleshooting

#### Common Issues

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

#### Debug Mode

Enable debug logging by setting:
```hcl
proxmox_debug = true
```

### Security Considerations

#### Sensitive Variables
- API tokens
- SSH private keys
- User passwords
- All marked with `sensitive = true`

#### Validation Rules
- VMID ranges (100-999999)
- IP address format validation
- Resource limit constraints
- Template name validation

#### Network Security
- Optional firewall rules
- VLAN tagging support
- Bridge isolation
- DNS configuration

### Best Practices

#### Development
- Always validate templates before deployment
- Use consistent naming conventions
- Document any custom modifications
- Test with small resource allocations first

#### Production
- Use full clones for production VMs
- Enable protection on critical VMs
- Implement proper backup strategies
- Monitor resource usage

#### Security
- Rotate API tokens regularly
- Use unprivileged containers when possible
- Implement network segmentation
- Regular security updates

### Contributing

When adding new modules or templates:

1. Follow the existing variable naming conventions
2. Include comprehensive validation rules
3. Add proper documentation
4. Test with different configurations
5. Update the Terraform README if needed

### Support

For issues with the Terraform templates:
1. Check the deployment logs in the backend
2. Verify Proxmox connectivity and permissions
3. Validate template availability
4. Review variable values in `terraform.tfvars`

For detailed Terraform documentation, see: `terraform-templates/README.md`
