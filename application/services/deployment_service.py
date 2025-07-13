import os
import subprocess
import json
import shutil
from pathlib import Path
import logging
import re

class DeploymentService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        # Use relative paths from the project directory
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.deployments_base_path = os.path.join(self.base_path, "deployments")
        self.templates_path = os.path.join(self.base_path, "terraform-templates")
        
        # Ensure directories exist
        os.makedirs(self.deployments_base_path, exist_ok=True)
        os.makedirs(self.templates_path, exist_ok=True)
        
        # Create template directories if they don't exist
        template_types = ["linux-vm", "linux-ct", "windows-vm", "vm-pack"]
        for template_type in template_types:
            os.makedirs(f"{self.templates_path}/{template_type}", exist_ok=True)

    def deploy_machines(self, machines):
        """Deploy multiple machines and return results for each"""
        results = []
        
        for machine in machines:
            try:
                result = self.deploy_single_machine(machine)
                results.append({
                    "machine_id": machine["id"],
                    "machine_name": machine["name"],
                    "status": "success" if result["success"] else "error",
                    "message": result["message"],
                    "output": result.get("output", "")
                })
            except Exception as e:
                results.append({
                    "machine_id": machine["id"],
                    "machine_name": machine["name"],
                    "status": "error",
                    "message": f"Deployment failed: {str(e)}",
                    "output": ""
                })
                
        return results

    def deploy_single_machine(self, machine):
        """Deploy a single machine using Terraform"""
        machine_id = machine["id"]
        machine_name = machine["name"]
        base_type = machine["baseType"]
        
        # Create deployment directory for this machine
        deployment_dir = f"{self.deployments_base_path}/{machine_id}"
        os.makedirs(deployment_dir, exist_ok=True)
        
        # Determine template type and copy template files
        template_type = self._get_template_type(machine)
        template_dir = f"{self.templates_path}/{template_type}"
        
        # Copy template files to deployment directory
        self._copy_template_files(template_dir, deployment_dir)
        
        # Generate terraform.tfvars file
        tfvars_content = self._generate_tfvars(machine)
        tfvars_path = f"{deployment_dir}/terraform.tfvars"
        
        with open(tfvars_path, 'w') as f:
            f.write(tfvars_content)
        
        # Save machine configuration for future reference
        config_path = f"{deployment_dir}/machine_config.json"
        with open(config_path, 'w') as f:
            json.dump(machine, f, indent=2)
        
        # Run Terraform
        return self._run_terraform(deployment_dir, machine_name)

    def _get_template_type(self, machine):
        """Determine which Terraform template to use"""
        base_type = machine["baseType"]
        
        if base_type == "linuxServer":
            vm_type = machine.get("advanced", {}).get("type", "vm")
            return "linux-ct" if vm_type == "ct" else "linux-vm"
        elif base_type == "windowsServer" or base_type == "windows10":
            return "windows-vm"
        elif base_type == "vmPack":
            return "vm-pack"
        else:
            raise ValueError(f"Unknown machine type: {base_type}")

    def _copy_template_files(self, template_dir, deployment_dir):
        """Copy Terraform template files to deployment directory"""
        if not os.path.exists(template_dir):
            raise FileNotFoundError(f"Template directory not found: {template_dir}")
        
        # Copy all .tf files from template to deployment directory
        for file in os.listdir(template_dir):
            if file.endswith('.tf'):
                src = f"{template_dir}/{file}"
                dst = f"{deployment_dir}/{file}"
                shutil.copy2(src, dst)
        
        # Create symlink to modules directory for modular architecture
        modules_dir = f"{self.base_path}/terraform-templates/modules"
        
        # Debug information
        logging.info(f"Creating symlinks for deployment: {deployment_dir}")
        logging.info(f"Modules directory: {modules_dir} (exists: {os.path.exists(modules_dir)})")
        
        # Create symlink to modules directory (contains reusable modules)
        modules_link = f"{deployment_dir}/modules"
        if os.path.exists(modules_dir):
            if os.path.exists(modules_link):
                # Remove existing symlink/directory
                if os.path.islink(modules_link):
                    os.unlink(modules_link)
                elif os.path.isdir(modules_link):
                    shutil.rmtree(modules_link)
            
            try:
                # Try to create symlink
                os.symlink(modules_dir, modules_link)
                logging.info(f"Created symlink: {modules_link} -> {modules_dir}")
            except OSError as e:
                # If symlink fails, copy the directory instead
                logging.warning(f"Symlink failed, copying directory: {e}")
                shutil.copytree(modules_dir, modules_link)
                logging.info(f"Copied directory: {modules_dir} -> {modules_link}")
        
        # Verify symlink was created
        if os.path.exists(modules_link):
            logging.info(f"Modules link exists: {modules_link}")
        else:
            logging.error(f"Modules link not created: {modules_link}")

    def _find_next_available_vmid(self):
        """Find the next available VMID starting from 5000"""
        try:
            # Start from 5000 as requested
            MIN_VMID = 5000
            MAX_VMID = 999999
            
            # Get existing VMIDs from Proxmox API
            existing_vmids = set()
            
            try:
                import requests
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                proxmox_server = self.config_manager.get("PROXMOX_SERVER")
                proxmox_token = self.config_manager.get("PVEAPITOKEN")
                proxmox_node = self.config_manager.get("NODE")
                
                if proxmox_server and proxmox_token and proxmox_node:
                    # Parse token
                    token_parts = proxmox_token.split("!")
                    if len(token_parts) == 2:
                        token_id = token_parts[0]
                        token_secret = token_parts[1].split("=")[1]
                        headers = {
                            "Authorization": f"PVEAPIToken={token_id}={token_secret}"
                        }
                        
                        # Get all VMs from all nodes
                        nodes_url = f"https://{proxmox_server}:8006/api2/json/nodes"
                        nodes_response = requests.get(nodes_url, headers=headers, verify=False, timeout=10)
                        
                        if nodes_response.status_code == 200:
                            nodes = nodes_response.json().get("data", [])
                            
                            for node in nodes:
                                node_name = node.get("node")
                                if node_name:
                                    # Get VMs from this node
                                    vms_url = f"https://{proxmox_server}:8006/api2/json/nodes/{node_name}/qemu"
                                    vms_response = requests.get(vms_url, headers=headers, verify=False, timeout=10)
                                    
                                    if vms_response.status_code == 200:
                                        vms = vms_response.json().get("data", [])
                                        for vm in vms:
                                            if "vmid" in vm:
                                                existing_vmids.add(int(vm["vmid"]))
                                    
                                    # Get containers from this node
                                    ct_url = f"https://{proxmox_server}:8006/api2/json/nodes/{node_name}/lxc"
                                    ct_response = requests.get(ct_url, headers=headers, verify=False, timeout=10)
                                    
                                    if ct_response.status_code == 200:
                                        containers = ct_response.json().get("data", [])
                                        for container in containers:
                                            if "vmid" in container:
                                                existing_vmids.add(int(container["vmid"]))
                                    
            except Exception as e:
                logging.warning(f"Could not query Proxmox API for existing VMIDs: {e}")
            
            # Also check local deployment directories for VMIDs
            if os.path.exists(self.deployments_base_path):
                for deployment_dir in os.listdir(self.deployments_base_path):
                    deployment_path = os.path.join(self.deployments_base_path, deployment_dir)
                    if os.path.isdir(deployment_path):
                        # Check terraform.tfvars for vm_id
                        tfvars_path = os.path.join(deployment_path, "terraform.tfvars")
                        if os.path.exists(tfvars_path):
                            try:
                                with open(tfvars_path, 'r') as f:
                                    content = f.read()
                                    import re
                                    match = re.search(r'vm_id\s*=\s*(\d+)', content)
                                    if match:
                                        existing_vmids.add(int(match.group(1)))
                            except Exception as e:
                                logging.warning(f"Could not read terraform.tfvars from {deployment_path}: {e}")
            
            # Find the next available VMID starting from 5000
            for vmid in range(MIN_VMID, MAX_VMID + 1):
                if vmid not in existing_vmids:
                    logging.info(f"Found available VMID: {vmid}")
                    return vmid
            
            # If all VMIDs are taken (unlikely), start from the next available
            if existing_vmids:
                next_vmid = max(existing_vmids) + 1
                if next_vmid <= MAX_VMID:
                    logging.warning(f"All VMIDs in range taken, using next sequential: {next_vmid}")
                    return next_vmid
            
            # Fallback to minimum VMID
            logging.warning(f"No VMIDs available, using minimum: {MIN_VMID}")
            return MIN_VMID
            
        except Exception as e:
            logging.error(f"Error finding next available VMID: {e}")
            return 5000  # Fallback to default

    def _find_vmid_range_for_pack(self, count):
        """Find a range of available VMIDs for VM packs starting from 5000"""
        try:
            # Get existing VMIDs
            existing_vmids = set()
            
            try:
                import requests
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                proxmox_server = self.config_manager.get("PROXMOX_SERVER")
                proxmox_token = self.config_manager.get("PVEAPITOKEN")
                proxmox_node = self.config_manager.get("NODE")
                
                if proxmox_server and proxmox_token and proxmox_node:
                    token_parts = proxmox_token.split("!")
                    if len(token_parts) == 2:
                        token_id = token_parts[0]
                        token_secret = token_parts[1].split("=")[1]
                        headers = {
                            "Authorization": f"PVEAPIToken={token_id}={token_secret}"
                        }
                        
                        # Get all VMs from all nodes
                        nodes_url = f"https://{proxmox_server}:8006/api2/json/nodes"
                        nodes_response = requests.get(nodes_url, headers=headers, verify=False, timeout=10)
                        
                        if nodes_response.status_code == 200:
                            nodes = nodes_response.json().get("data", [])
                            
                            for node in nodes:
                                node_name = node.get("node")
                                if node_name:
                                    # Get VMs and CTs from this node
                                    for vm_type in ["qemu", "lxc"]:
                                        vm_url = f"https://{proxmox_server}:8006/api2/json/nodes/{node_name}/{vm_type}"
                                        vm_response = requests.get(vm_url, headers=headers, verify=False, timeout=10)
                                        
                                        if vm_response.status_code == 200:
                                            vms = vm_response.json().get("data", [])
                                            for vm in vms:
                                                if "vmid" in vm:
                                                    existing_vmids.add(int(vm["vmid"]))
                                    
            except Exception as e:
                logging.warning(f"Could not query Proxmox API for VM pack VMIDs: {e}")
            
            # Check local deployments
            if os.path.exists(self.deployments_base_path):
                for deployment_dir in os.listdir(self.deployments_base_path):
                    deployment_path = os.path.join(self.deployments_base_path, deployment_dir)
                    if os.path.isdir(deployment_path):
                        tfvars_path = os.path.join(deployment_path, "terraform.tfvars")
                        if os.path.exists(tfvars_path):
                            try:
                                with open(tfvars_path, 'r') as f:
                                    content = f.read()
                                    import re
                                    # Check for vm_id and start_vmid
                                    for pattern in [r'vm_id\s*=\s*(\d+)', r'start_vmid\s*=\s*(\d+)']:
                                        matches = re.findall(pattern, content)
                                        for match in matches:
                                            existing_vmids.add(int(match))
                            except Exception as e:
                                logging.warning(f"Could not read terraform.tfvars from {deployment_path}: {e}")
            
            # Find a range of available VMIDs starting from 5000
            start_vmid = 5000
            max_vmid = 999999
            
            for vmid in range(start_vmid, max_vmid - count + 1):
                # Check if the range [vmid, vmid + count - 1] is available
                range_available = True
                for i in range(count):
                    if (vmid + i) in existing_vmids:
                        range_available = False
                        break
                
                if range_available:
                    logging.info(f"Found available VMID range: {vmid} to {vmid + count - 1}")
                    return vmid
            
            # If no range found, use the next available VMID
            next_vmid = self._find_next_available_vmid()
            logging.warning(f"No range available, using single VMID: {next_vmid}")
            return next_vmid
            
        except Exception as e:
            logging.error(f"Error finding VMID range for pack: {e}")
            return 5000

    def _generate_tfvars(self, machine):
        """Generate terraform.tfvars content based on machine configuration"""
        base_type = machine["baseType"]
        advanced = machine.get("advanced", {})
        
        # Find next available VMID
        next_vmid = self._find_next_available_vmid()
        
        # Sanitize VM name for container compatibility (alphanumeric and hyphens only)
        vm_name = machine["name"].replace(" ", "-").replace("_", "-")
        # Remove any non-alphanumeric characters except hyphens
        vm_name = re.sub(r'[^a-zA-Z0-9-]', '', vm_name)
        # Ensure it starts with alphanumeric
        if vm_name and not vm_name[0].isalnum():
            vm_name = "vm-" + vm_name
        # Limit to 64 characters
        vm_name = vm_name[:64]
        
        # Common variables
        tfvars = {
            "vm_name": vm_name,
            "vm_id": advanced.get("vmid", next_vmid),
            "proxmox_server": self.config_manager.get("PROXMOX_SERVER"),
            "proxmox_token": self.config_manager.get("PVEAPITOKEN"),
            "proxmox_node": self.config_manager.get("NODE"),
        }
        
        # Type-specific variables
        if base_type == "linuxServer":
            vm_type = advanced.get("type", "vm")
            os_version = advanced.get("os_version", "")
            
            tfvars.update({
                "template_name": os_version,
                "cores": self._get_cores_from_perf(advanced.get("perf", "medium")),
                "memory": self._get_memory_from_perf(advanced.get("perf", "medium")),
                "disk_size": self._get_disk_from_perf(advanced.get("perf", "medium")),
                "username": advanced.get("username", "user"),
                "ssh_keys": advanced.get("sshKey", ""),  # New variable name
                "ssh_key": advanced.get("sshKey", ""),   # Legacy compatibility
                "network_bridge": "vmbr0",
                "network_tag": 10,
            })
            
            # IP configuration
            if advanced.get("ip_mode") == "static":
                tfvars.update({
                    "ip_address": advanced.get("ip_address", ""),
                    "subnet_mask": advanced.get("subnet_mask", "24"),
                    "gateway": "192.168.1.1",
                    "nameserver": "8.8.8.8",
                })
            else:
                tfvars.update({
                    "network_config": "dhcp",
                    "nameserver": "8.8.8.8",
                })
                
        elif base_type in ["windowsServer", "windows10"]:
            os_version = advanced.get("os_version", "2019")
            template_map = {
                "2016": "windows-server-2016-template",
                "2019": "windows-server-2019-template", 
                "2022": "windows-server-2022-template"
            }
            
            tfvars.update({
                "template_name": template_map.get(os_version, "windows-server-2019-template"),
                "cores": self._get_cores_from_perf(advanced.get("perf", "medium")),
                "memory": self._get_memory_from_perf(advanced.get("perf", "medium")),
                "disk_size": self._get_disk_from_perf(advanced.get("perf", "medium")),
                "network_bridge": "vmbr0",
                "network_tag": 10,
                "nameserver": "8.8.8.8",
            })
            
        elif base_type == "vmPack":
            group = machine.get("group", {})
            vm_count = group.get("count", 1)
            os_version = group.get("os_version", "")
            
            # For VM packs, find a range of available VMIDs
            start_vmid = advanced.get("vmid", self._find_vmid_range_for_pack(vm_count))
            
            tfvars.update({
                "template_name": os_version,
                "vm_count": vm_count,
                "base_name": machine["name"],
                "start_vmid": start_vmid,
                "cores": 2,
                "memory": 2048,
                "disk_size": 20,
                "network_bridge": "vmbr0",
                "network_tag": 10,
                "gateway": "192.168.1.1",
                "nameserver": "8.8.8.8",
                "username": "user",
                "ssh_keys": "",
            })
        
        # Convert to terraform.tfvars format
        tfvars_lines = []
        for key, value in tfvars.items():
            if isinstance(value, str):
                tfvars_lines.append(f'{key} = "{value}"')
            elif isinstance(value, (int, float)):
                tfvars_lines.append(f'{key} = {value}')
            elif isinstance(value, bool):
                tfvars_lines.append(f'{key} = {str(value).lower()}')
            elif isinstance(value, list):
                formatted_list = '[' + ', '.join(f'"{item}"' for item in value) + ']'
                tfvars_lines.append(f'{key} = {formatted_list}')
        
        return '\n'.join(tfvars_lines)

    def _get_cores_from_perf(self, perf):
        """Get CPU cores based on performance tier"""
        perf_map = {"low": 1, "medium": 2, "high": 4}
        return perf_map.get(perf, 2)

    def _get_memory_from_perf(self, perf):
        """Get memory in MB based on performance tier"""
        perf_map = {"low": 1024, "medium": 2048, "high": 4096}
        return perf_map.get(perf, 2048)

    def _get_disk_from_perf(self, perf):
        """Get disk size in GB based on performance tier"""
        perf_map = {"low": 20, "medium": 40, "high": 80}
        return perf_map.get(perf, 40)

    def _run_terraform(self, deployment_dir, machine_name):
        """Run Terraform commands in the deployment directory"""
        try:
            # Change to deployment directory
            original_cwd = os.getcwd()
            os.chdir(deployment_dir)
            
            # Run terraform init
            init_result = subprocess.run(
                ["terraform", "init"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if init_result.returncode != 0:
                return {
                    "success": False,
                    "message": f"❌ Terraform init failed for {machine_name}",
                    "output": self._clean_terraform_output(init_result.stderr)
                }
            
            # Run terraform plan
            plan_result = subprocess.run(
                ["terraform", "plan"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if plan_result.returncode != 0:
                return {
                    "success": False,
                    "message": f"❌ Terraform plan failed for {machine_name}",
                    "output": self._clean_terraform_output(plan_result.stderr)
                }
            
            # Run terraform apply
            apply_result = subprocess.run(
                ["terraform", "apply", "-auto-approve"],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if apply_result.returncode != 0:
                return {
                    "success": False,
                    "message": f"❌ Terraform apply failed for {machine_name}",
                    "output": self._clean_terraform_output(apply_result.stderr)
                }
            
            # Extract and format deployment summary
            cleaned_output = self._clean_terraform_output(apply_result.stdout)
            summary = self._extract_deployment_summary(cleaned_output, machine_name)
            formatted_message = self._format_success_message(summary)
            
            return {
                "success": True,
                "message": formatted_message,
                "output": cleaned_output,
                "summary": summary
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": f"⏰ Terraform deployment timed out for {machine_name}",
                "output": "Operation timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"💥 Terraform deployment error for {machine_name}: {str(e)}",
                "output": str(e)
            }
        finally:
            # Always return to original directory
            os.chdir(original_cwd)

    def list_deployments(self):
        """List all current deployments"""
        deployments = []
        if os.path.exists(self.deployments_base_path):
            for item in os.listdir(self.deployments_base_path):
                deployment_path = f"{self.deployments_base_path}/{item}"
                if os.path.isdir(deployment_path):
                    config_file = f"{deployment_path}/machine_config.json"
                    if os.path.exists(config_file):
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                        deployments.append({
                            "machine_id": item,
                            "config": config,
                            "deployment_path": deployment_path
                        })
        return deployments

    def destroy_machine(self, machine_id):
        """Destroy a deployed machine using terraform destroy"""
        deployment_dir = f"{self.deployments_base_path}/{machine_id}"
        
        if not os.path.exists(deployment_dir):
            return {
                "success": False,
                "message": f"Deployment not found for machine {machine_id}"
            }
        
        try:
            original_cwd = os.getcwd()
            os.chdir(deployment_dir)
            
            # Run terraform destroy
            destroy_result = subprocess.run(
                ["terraform", "destroy", "-auto-approve"],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if destroy_result.returncode != 0:
                return {
                    "success": False,
                    "message": f"❌ Terraform destroy failed for {machine_id}",
                    "output": self._clean_terraform_output(destroy_result.stderr)
                }
            
            # Remove deployment directory
            shutil.rmtree(deployment_dir)
            
            return {
                "success": True,
                "message": f"🗑️  Successfully destroyed {machine_id}",
                "output": self._clean_terraform_output(destroy_result.stdout)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error destroying {machine_id}: {str(e)}",
                "output": str(e)
            }
        finally:
            os.chdir(original_cwd) 

    def _clean_terraform_output(self, output):
        """Clean up Terraform output by removing ANSI color codes and improving readability"""
        if not output:
            return output
        
        # Remove ANSI color codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', output)
        
        # Remove extra whitespace and normalize line endings
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned

    def _extract_deployment_summary(self, output, machine_name):
        """Extract useful deployment information from Terraform output"""
        try:
            # Parse the output to extract key information
            lines = output.split('\n')
            summary = {
                "machine_name": machine_name,
                "status": "Successfully deployed",
                "resources_created": 0,
                "vm_ids": [],
                "vm_names": [],
                "vm_ips": [],
                "vm_macs": [],
                "ssh_connections": []
            }
            
            # Look for resource creation information
            for line in lines:
                if "Resources:" in line:
                    # Extract number of resources created
                    match = re.search(r'(\d+) added', line)
                    if match:
                        summary["resources_created"] = int(match.group(1))
                
                # Look for outputs section
                if "Outputs:" in line:
                    # Parse outputs to extract useful information
                    in_outputs = True
                    current_output = ""
                    for output_line in lines[lines.index(line):]:
                        if output_line.strip() == "":
                            break
                        if "=" in output_line and not output_line.startswith(" "):
                            current_output = output_line.split("=")[0].strip()
                        elif current_output and "[" in output_line and "]" in output_line:
                            # Extract array values
                            values = re.findall(r'"([^"]*)"', output_line)
                            if current_output == "vm_ids":
                                summary["vm_ids"] = [int(v) for v in values if v.isdigit()]
                            elif current_output == "vm_names":
                                summary["vm_names"] = values
                            elif current_output == "vm_ip_addresses":
                                summary["vm_ips"] = values
                            elif current_output == "vm_mac_addresses":
                                summary["vm_macs"] = values
                            elif current_output == "vm_ssh_connections":
                                # Parse SSH connection objects
                                ssh_info = []
                                for i, name in enumerate(summary["vm_names"]):
                                    if i < len(values):
                                        ssh_info.append({
                                            "name": name,
                                            "command": f"ssh user@{values[i]}" if values[i] != "dhcp" else "ssh user@<IP>"
                                        })
                                summary["ssh_connections"] = ssh_info
            
            return summary
            
        except Exception as e:
            # Fallback to basic success message
            return {
                "machine_name": machine_name,
                "status": "Successfully deployed",
                "resources_created": 0,
                "vm_ids": [],
                "vm_names": [],
                "vm_ips": [],
                "vm_macs": [],
                "ssh_connections": []
            }

    def _format_success_message(self, summary):
        """Format deployment summary into a clean success message"""
        if not summary:
            return "Deployment completed successfully"
        
        message = f"✅ Successfully created machines:\n"
        
        # Create a list of machine names and VMIDs
        machines = []
        for i, name in enumerate(summary['vm_names']):
            vm_id = summary['vm_ids'][i] if i < len(summary['vm_ids']) else "N/A"
            machines.append(f"   {name} (ID: {vm_id})")
        
        message += "\n".join(machines)
        
        return message.strip() 