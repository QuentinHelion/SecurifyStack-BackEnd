import os
import json
import logging
from datetime import datetime
from pathlib import Path

class DeploymentTrackingService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.tracking_file = os.path.join(self.base_path, "deployed_machines.json")
        
        # Ensure the tracking file exists
        self._initialize_tracking_file()
    
    def _initialize_tracking_file(self):
        """Initialize the tracking file if it doesn't exist"""
        if not os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'w') as f:
                json.dump({"machines": []}, f, indent=2)
    
    def _load_deployed_machines(self):
        """Load deployed machines from the tracking file"""
        try:
            with open(self.tracking_file, 'r') as f:
                data = json.load(f)
                return data.get("machines", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading deployed machines: {e}")
            return []
    
    def _save_deployed_machines(self, machines):
        """Save deployed machines to the tracking file"""
        try:
            with open(self.tracking_file, 'w') as f:
                json.dump({"machines": machines}, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving deployed machines: {e}")
    
    def add_deployed_machine(self, machine_config, deployment_result):
        """Add a successfully deployed machine to tracking"""
        try:
            machines = self._load_deployed_machines()
            
            # Check if this is a vm-pack deployment
            if machine_config.get("baseType") == "vmPack":
                self._add_vmpack_machines(machines, machine_config, deployment_result)
            else:
                self._add_single_machine(machines, machine_config, deployment_result)
            
            self._save_deployed_machines(machines)
            
        except Exception as e:
            logging.error(f"Error adding deployed machine to tracking: {e}")
    
    def _add_vmpack_machines(self, machines, machine_config, deployment_result):
        """Add multiple machines from a vm-pack deployment"""
        try:
            output = deployment_result.get("output", "")
            
            # Parse terraform output to extract arrays
            import re
            
            # Extract VM IDs
            vm_ids_match = re.search(r'vm_ids\s*=\s*\[([\d,\s]+)\]', output)
            vm_ids = []
            if vm_ids_match:
                vm_ids = [int(x.strip()) for x in vm_ids_match.group(1).split(',') if x.strip()]
            
            # Extract VM names
            vm_names_match = re.search(r'vm_names\s*=\s*\[(.*?)\]', output, re.DOTALL)
            vm_names = []
            if vm_names_match:
                names_str = vm_names_match.group(1)
                vm_names = [name.strip().strip('"') for name in names_str.split(',') if name.strip()]
            
            # Extract IP addresses
            vm_ips_match = re.search(r'vm_ip_addresses\s*=\s*\[(.*?)\]', output, re.DOTALL)
            vm_ips = []
            if vm_ips_match:
                ips_str = vm_ips_match.group(1)
                vm_ips = [ip.strip().strip('"') for ip in ips_str.split(',') if ip.strip()]
            
            # Extract MAC addresses
            vm_macs_match = re.search(r'vm_mac_addresses\s*=\s*\[(.*?)\]', output, re.DOTALL)
            vm_macs = []
            if vm_macs_match:
                macs_str = vm_macs_match.group(1)
                vm_macs = [mac.strip().strip('"') for mac in macs_str.split(',') if mac.strip()]
            
            # Create entries for each container
            for i in range(len(vm_ids)):
                if i < len(vm_ids):
                    vmid = vm_ids[i]
                    name = vm_names[i] if i < len(vm_names) else f"{machine_config['name']}-{i+1}"
                    ip = vm_ips[i] if i < len(vm_ips) else "dhcp"
                    mac = vm_macs[i] if i < len(vm_macs) else ""
                    
                    # Create individual machine config
                    individual_config = machine_config.copy()
                    individual_config["id"] = str(vmid)
                    individual_config["name"] = name
                    individual_config["vm_id"] = vmid
                    
                    deployed_machine = {
                        "id": str(vmid),
                        "name": name,
                        "base_type": machine_config["baseType"],
                        "deployment_time": datetime.now().isoformat(),
                        "ip_address": ip,
                        "mac_address": mac,
                        "status": "deployed",
                        "terraform_state_path": f"deployments/{machine_config['id']}/terraform.tfstate",
                        "config": individual_config,
                        "deployment_result": deployment_result,
                        "pack_id": machine_config["id"]  # Reference to original pack
                    }
                    
                    # Remove existing machine with same ID if it exists
                    machines[:] = [m for m in machines if m["id"] != str(vmid)]
                    
                    # Add the new machine
                    machines.append(deployed_machine)
                    logging.info(f"Added container to tracking: {name} (ID: {vmid})")
            
        except Exception as e:
            logging.error(f"Error adding vm-pack machines to tracking: {e}")
    
    def _add_single_machine(self, machines, machine_config, deployment_result):
        """Add a single machine to tracking (original logic)"""
        try:
            # Extract IP address from deployment result
            ip_address = self._extract_ip_from_result(deployment_result)

            # Extract VMID from deployment result (ct_id, vm_id, or vmid)
            output = deployment_result.get("output", "")
            import re
            vmid = None
            patterns = [
                r'ct_id\s*=\s*(\d+)',
                r'vm_id\s*=\s*(\d+)',
                r'vmid\s*=\s*(\d+)',
                r'container_id\s*=\s*(\d+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, output)
                if match:
                    vmid = int(match.group(1))
                    break

            # Use VMID as the id if found, otherwise fallback to old id
            id_to_use = str(vmid) if vmid else machine_config["id"]
            # Update config as well
            updated_config = machine_config.copy()
            updated_config["id"] = id_to_use
            if vmid:
                updated_config["vm_id"] = vmid

            deployed_machine = {
                "id": id_to_use,
                "name": machine_config["name"],
                "base_type": machine_config["baseType"],
                "deployment_time": datetime.now().isoformat(),
                "ip_address": ip_address,
                "status": "deployed",
                "terraform_state_path": f"deployments/{id_to_use}/terraform.tfstate",
                "config": updated_config,
                "deployment_result": deployment_result
            }
            
            # Remove existing machine with same ID if it exists
            machines[:] = [m for m in machines if m["id"] != id_to_use]
            
            # Add the new machine
            machines.append(deployed_machine)
            logging.info(f"Added deployed machine to tracking: {machine_config['name']} (ID: {id_to_use})")
            
        except Exception as e:
            logging.error(f"Error adding single machine to tracking: {e}")
    
    def _extract_ip_from_result(self, deployment_result):
        """Extract IP address from deployment result"""
        try:
            output = deployment_result.get("output", "")
            
            # Try to extract IP from various output formats
            if "vm_ip_address" in output:
                import re
                ip_match = re.search(r'vm_ip_address\s*=\s*"([^"]+)"', output)
                if ip_match:
                    ip_addr = ip_match.group(1)
                    # Handle CIDR notation (e.g., "192.168.1.100/24")
                    if '/' in ip_addr:
                        ip_addr = ip_addr.split('/')[0]
                    return ip_addr
            
            if "ct_ip_address" in output:
                import re
                ip_match = re.search(r'ct_ip_address\s*=\s*"([^"]+)"', output)
                if ip_match:
                    ip_addr = ip_match.group(1)
                    # Handle CIDR notation (e.g., "192.168.1.100/24")
                    if '/' in ip_addr:
                        ip_addr = ip_addr.split('/')[0]
                    return ip_addr
            
            # Look for IP addresses in the output
            import re
            ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            ip_matches = re.findall(ip_pattern, output)
            if ip_matches:
                # Return the first valid IP that's not localhost
                for ip in ip_matches:
                    if not ip.startswith("127.") and not ip.startswith("0."):
                        return ip
            
            return "Unknown"
        except Exception as e:
            logging.error(f"Error extracting IP from deployment result: {e}")
            return "Unknown"
    
    def get_deployed_machines(self):
        """Get all deployed machines"""
        return self._load_deployed_machines()
    
    def get_machine_by_id(self, machine_id):
        """Get a specific deployed machine by ID"""
        machines = self._load_deployed_machines()
        for machine in machines:
            if machine["id"] == machine_id:
                return machine
        return None
    
    def update_machine_status(self, machine_id, status, ip_address=None):
        """Update the status of a deployed machine"""
        try:
            machines = self._load_deployed_machines()
            
            for machine in machines:
                if machine["id"] == machine_id:
                    machine["status"] = status
                    machine["last_updated"] = datetime.now().isoformat()
                    if ip_address:
                        machine["ip_address"] = ip_address
                    break
            
            self._save_deployed_machines(machines)
            logging.info(f"Updated machine status: {machine_id} -> {status}")
            
        except Exception as e:
            logging.error(f"Error updating machine status: {e}")
    
    def remove_machine(self, machine_id):
        """Remove a machine from tracking (when destroyed)"""
        try:
            machines = self._load_deployed_machines()
            machines = [m for m in machines if m["id"] != machine_id]
            self._save_deployed_machines(machines)
            logging.info(f"Removed machine from tracking: {machine_id}")
            
        except Exception as e:
            logging.error(f"Error removing machine from tracking: {e}")
    
    def get_terraform_state_path(self, machine_id):
        """Get the terraform state path for a machine"""
        machine = self.get_machine_by_id(machine_id)
        if machine:
            return machine.get("terraform_state_path")
        return None
    
    def machine_exists(self, machine_id):
        """Check if a machine exists in tracking"""
        return self.get_machine_by_id(machine_id) is not None 