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
            machines = [m for m in machines if m["id"] != id_to_use]
            
            # Add the new machine
            machines.append(deployed_machine)
            
            self._save_deployed_machines(machines)
            logging.info(f"Added deployed machine to tracking: {machine_config['name']} (ID: {id_to_use})")
            
        except Exception as e:
            logging.error(f"Error adding deployed machine to tracking: {e}")
    
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