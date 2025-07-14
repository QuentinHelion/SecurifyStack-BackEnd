import os
import subprocess
import json
import logging
import requests
import urllib3
from datetime import datetime

# Disable SSL warnings for Proxmox API calls
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class HealthCheckService:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    def get_machine_ip_from_proxmox(self, machine_id, vm_id):
        """Get machine IP address from Proxmox API"""
        try:
            proxmox_server = self.config_manager.get("PROXMOX_SERVER")
            proxmox_token = self.config_manager.get("PVEAPITOKEN")
            proxmox_node = self.config_manager.get("NODE")
            
            if not all([proxmox_server, proxmox_token, proxmox_node]):
                logging.error("Missing Proxmox configuration")
                return None
            
            # Parse token
            token_parts = proxmox_token.split("!")
            if len(token_parts) != 2:
                logging.error("Invalid Proxmox token format")
                return None
            
            token_id = token_parts[0]
            token_secret = token_parts[1].split("=")[1]
            
            headers = {
                "Authorization": f"PVEAPIToken={token_id}={token_secret}"
            }
            
            # Try to get VM info first
            vm_url = f"https://{proxmox_server}:8006/api2/json/nodes/{proxmox_node}/qemu/{vm_id}/status/current"
            vm_response = requests.get(vm_url, headers=headers, verify=False, timeout=10)
            
            if vm_response.status_code == 200:
                vm_data = vm_response.json().get("data", {})
                
                # Try to get agent info for IP
                agent_url = f"https://{proxmox_server}:8006/api2/json/nodes/{proxmox_node}/qemu/{vm_id}/agent/network-get-interfaces"
                agent_response = requests.get(agent_url, headers=headers, verify=False, timeout=10)
                
                if agent_response.status_code == 200:
                    agent_data = agent_response.json().get("data", {})
                    ip_address = self._extract_ip_from_agent_data(agent_data)
                    if ip_address:
                        return {
                            "ip_address": ip_address,
                            "status": vm_data.get("status", "unknown"),
                            "source": "proxmox_agent"
                        }
            
            # Try container if VM didn't work
            ct_url = f"https://{proxmox_server}:8006/api2/json/nodes/{proxmox_node}/lxc/{vm_id}/status/current"
            ct_response = requests.get(ct_url, headers=headers, verify=False, timeout=10)
            
            if ct_response.status_code == 200:
                ct_data = ct_response.json().get("data", {})
                
                # Get container config for network info
                config_url = f"https://{proxmox_server}:8006/api2/json/nodes/{proxmox_node}/lxc/{vm_id}/config"
                config_response = requests.get(config_url, headers=headers, verify=False, timeout=10)
                
                ip_address = None
                if config_response.status_code == 200:
                    config_data = config_response.json().get("data", {})
                    ip_address = self._extract_ip_from_ct_config(config_data)
                # Fallback: Try /interfaces endpoint if config did not yield a valid IP
                if not ip_address or ip_address.lower() in ("dhcp", "static"):
                    interfaces_url = f"https://{proxmox_server}:8006/api2/json/nodes/{proxmox_node}/lxc/{vm_id}/interfaces"
                    interfaces_response = requests.get(interfaces_url, headers=headers, verify=False, timeout=10)
                    if interfaces_response.status_code == 200:
                        interfaces_data = interfaces_response.json().get("data", {})
                        ip_address = self._extract_ip_from_lxc_interfaces(interfaces_data)
                if ip_address:
                    return {
                        "ip_address": ip_address,
                        "status": ct_data.get("status", "unknown"),
                        "source": "proxmox_config_or_interfaces"
                    }
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting machine IP from Proxmox: {e}")
            return None
    
    def _extract_ip_from_agent_data(self, agent_data):
        """Extract IP address from QEMU agent network data"""
        try:
            if "result" in agent_data:
                interfaces = agent_data["result"]
                for interface in interfaces:
                    if interface.get("name") != "lo":  # Skip loopback
                        ip_addresses = interface.get("ip-addresses", [])
                        for ip_info in ip_addresses:
                            ip = ip_info.get("ip-address")
                            if ip and not ip.startswith("127.") and ":" not in ip:  # IPv4, not localhost
                                return ip
            return None
        except Exception as e:
            logging.error(f"Error extracting IP from agent data: {e}")
            return None
    
    def _extract_ip_from_ct_config(self, config_data):
        """Extract IP address from container configuration"""
        try:
            # Look for network configuration
            for key, value in config_data.items():
                if key.startswith("net"):
                    # Parse network configuration
                    if "ip=" in value:
                        import re
                        ip_match = re.search(r'ip=([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', value)
                        if ip_match:
                            return ip_match.group(1)
            return None
        except Exception as e:
            logging.error(f"Error extracting IP from container config: {e}")
            return None
    
    def _extract_ip_from_lxc_interfaces(self, interfaces_data):
        """Extract IP address from LXC /interfaces endpoint data"""
        try:
            logging.info(f"Extracting IP from LXC interfaces data: {interfaces_data}")
            
            # Handle different response formats
            if isinstance(interfaces_data, dict):
                # Sometimes the response is wrapped in a dict
                if 'data' in interfaces_data:
                    interfaces_data = interfaces_data['data']
                elif 'result' in interfaces_data:
                    interfaces_data = interfaces_data['result']
            
            if not isinstance(interfaces_data, list):
                logging.warning(f"Expected list for interfaces, got: {type(interfaces_data)}")
                return None
            
            # Look for eth0 or first non-loopback interface
            for iface in interfaces_data:
                logging.info(f"Processing interface: {iface}")
                iface_name = iface.get("name", "")
                
                if iface_name == "eth0" or (iface_name != "lo" and iface_name.startswith("eth")):
                    # Try different IP field names
                    for ip_field in ["inet", "ip-address", "ip_address", "ipv4"]:
                        if ip_field in iface:
                            ip_value = iface[ip_field]
                            logging.info(f"Found {ip_field} in {iface_name}: {ip_value}")
                            
                            if isinstance(ip_value, str) and ip_value:
                                # Handle CIDR notation
                                ip = ip_value.split('/')[0]
                                if self._is_valid_ip_simple(ip):
                                    logging.info(f"Valid IP found: {ip}")
                                    return ip
                    
                    # Try ip-addresses array
                    if "ip-addresses" in iface:
                        ip_addresses = iface["ip-addresses"]
                        logging.info(f"Found ip-addresses array in {iface_name}: {ip_addresses}")
                        
                        for ip_info in ip_addresses:
                            if isinstance(ip_info, dict):
                                ip = ip_info.get("ip-address") or ip_info.get("address")
                            else:
                                ip = str(ip_info)
                            
                            if ip and self._is_valid_ip_simple(ip.split('/')[0]):
                                logging.info(f"Valid IP found in array: {ip}")
                                return ip.split('/')[0]
            
            logging.warning("No valid IP found in any interface")
            return None
            
        except Exception as e:
            logging.error(f"Error extracting IP from LXC interfaces: {e}")
            return None
    
    def _is_valid_ip_simple(self, ip_string):
        """Simple IP validation"""
        try:
            if not ip_string or not isinstance(ip_string, str):
                return False
            
            # Basic format check
            parts = ip_string.split('.')
            if len(parts) != 4:
                return False
            
            # Check each part is a valid number 0-255
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            
            # Exclude localhost and invalid ranges
            if ip_string.startswith("127.") or ip_string.startswith("0.") or ip_string == "0.0.0.0":
                return False
            
            return True
        except:
            return False
    
    def get_machine_ip_from_terraform(self, machine_id):
        """Get machine IP address from Terraform state"""
        try:
            deployment_dir = os.path.join(self.base_path, "deployments", machine_id)
            state_file = os.path.join(deployment_dir, "terraform.tfstate")
            
            if not os.path.exists(state_file):
                logging.warning(f"Terraform state file not found for machine {machine_id}")
                return None
            
            # Read terraform state
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            
            # Extract IP from state
            ip_address = self._extract_ip_from_terraform_state(state_data)
            
            if ip_address:
                return {
                    "ip_address": ip_address,
                    "status": "running",
                    "source": "terraform_state"
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting machine IP from Terraform: {e}")
            return None
    
    def _extract_ip_from_terraform_state(self, state_data):
        """Extract IP address from Terraform state"""
        try:
            resources = state_data.get("resources", [])
            
            for resource in resources:
                if resource.get("type") in ["proxmox_vm_qemu", "proxmox_lxc"]:
                    instances = resource.get("instances", [])
                    for instance in instances:
                        attributes = instance.get("attributes", {})
                        
                        # Try different IP fields
                        for ip_field in ["default_ipv4_address", "ipconfig0", "network"]:
                            if ip_field in attributes:
                                ip_value = attributes[ip_field]
                                if isinstance(ip_value, str) and self._is_valid_ip(ip_value):
                                    return ip_value
                                elif isinstance(ip_value, dict):
                                    # Handle nested IP configuration
                                    for key, value in ip_value.items():
                                        if "ip" in key.lower() and self._is_valid_ip(str(value)):
                                            return str(value)
            
            return None
            
        except Exception as e:
            logging.error(f"Error extracting IP from Terraform state: {e}")
            return None
    
    def _is_valid_ip(self, ip_string):
        """Check if string is a valid IP address"""
        try:
            import ipaddress
            ipaddress.ip_address(ip_string.split('/')[0])  # Handle CIDR notation
            return not ip_string.startswith("127.") and not ip_string.startswith("0.")
        except:
            return False
    
    def ping_machine(self, ip_address):
        """Ping a machine to check if it's reachable"""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "3", ip_address],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logging.error(f"Error pinging machine {ip_address}: {e}")
            return False
    
    def ssh_check(self, ip_address, username="debian", port=22):
        """Check if SSH is available on the machine"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((ip_address, port))
            sock.close()
            return result == 0
        except Exception as e:
            logging.error(f"Error checking SSH on {ip_address}: {e}")
            return False
    
    def comprehensive_health_check(self, machine_id, vm_id):
        """Perform a comprehensive health check on a machine"""
        try:
            health_info = {
                "machine_id": machine_id,
                "vm_id": vm_id,
                "timestamp": datetime.now().isoformat(),
                "ip_address": None,
                "status": "unknown",
                "ping_success": False,
                "ssh_available": False,
                "source": "unknown"
            }
            
            # Try to get IP from Proxmox first
            proxmox_info = self.get_machine_ip_from_proxmox(machine_id, vm_id)
            if proxmox_info:
                health_info.update(proxmox_info)
            else:
                # Fallback to Terraform state
                terraform_info = self.get_machine_ip_from_terraform(machine_id)
                if terraform_info:
                    health_info.update(terraform_info)
            
            # If we have an IP, perform connectivity checks
            if health_info["ip_address"]:
                health_info["ping_success"] = self.ping_machine(health_info["ip_address"])
                health_info["ssh_available"] = self.ssh_check(health_info["ip_address"])
            
            return health_info
            
        except Exception as e:
            logging.error(f"Error performing comprehensive health check: {e}")
            return None 