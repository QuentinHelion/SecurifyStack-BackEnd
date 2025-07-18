"""
Main app file, all api route are declared there
"""

import sys
import os
from cryptography.fernet import Fernet
from dotenv import set_key
import logging

# --- Argument Parsing must happen BEFORE Flask app initialization ---
if '--generate-key' in sys.argv:
    try:
        env_file = '.env'
        if not os.path.exists(env_file):
            open(env_file, 'a').close()
        
        new_key = Fernet.generate_key()
        set_key(env_file, 'MASTER_KEY', new_key.decode())
        print(f"Successfully generated and saved a new MASTER_KEY to the {env_file} file.")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred while generating the key: {e}")
        sys.exit(1)


from flask import Flask, request, jsonify, abort, send_file
from flask_cors import CORS
import requests
import tempfile
import shutil
from application.interfaces.controllers.crtl_json import JsonCrtl
from application.interfaces.controllers.ldaps_controller import LdapsController
from application.interfaces.presenters.ldaps_presenter import LdapsPresenter
from infrastructure.data.args import Args
from infrastructure.data.config_manager import ConfigManager
from infrastructure.data.token import generate_token
from infrastructure.data.sftp_utils import connect_sftp, is_directory
from infrastructure.data.terraform_utils import execute_terraform
from application.services.terraform_service import TerraformService
from application.services.deployment_service import DeploymentService
from application.services.deployment_tracking_service import DeploymentTrackingService
from application.services.health_check_service import HealthCheckService


args_checker = Args()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://securify-stack.homelab"]}})

config_manager = ConfigManager()
terraform_service = TerraformService(config_manager)
deployment_service = DeploymentService(config_manager)
tracking_service = DeploymentTrackingService(config_manager)
health_check_service = HealthCheckService(config_manager)

SFTP_BASE_PATH = os.getenv("SFTP_BASE_PATH", ".")
LOCAL_APP_DIR = os.getenv("LOCAL_APP_DIR", "./downloaded_apps")
USERS_TOKENS = []
EXCLUDED_ROUTES = ["/login", "/test-proxmox", "/test-ldaps", "/save-config", "/get-config"]


@app.before_request
def before_request():
    """
    Before request, check if token is given and if it is valid
    """
    if request.method == 'OPTIONS':
        return

    if request.path not in EXCLUDED_ROUTES:
        token = None
        
        # 1. First, try to get the token from the Authorization header (best practice)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # 2. If not in header, fall back to checking URL parameters (for legacy calls)
        if not token:
            token = request.args.get('token')
        
        # 3. Validate the token
        if not token or token not in USERS_TOKENS:
            abort(
                code=401,
                description=jsonify({
                    "status": "401",
                    "message": "Unauthorized: Token is missing or invalid"
                })
            )


@app.route('/login', methods=['GET'])
def login():
    """
    :return: auth token
    """
    ldap_server = config_manager.get("LDAPS_SERVER")
    ldap_port = int(config_manager.get("LDAPS_SERVER_PORT"))
    ldap_cert_info = config_manager.get("LDAPS_CERT", "infrastructure/persistence/certificats/ssrootca.cer")
    ldap_base_dn = config_manager.get("LDAPS_BASE_DN")
    ldap_user_ou = config_manager.get("LDAPS_USER_OU", "")

    cert_path = None
    is_temp_cert = False
    try:
        if ldap_cert_info and os.path.exists(ldap_cert_info):
            cert_path = ldap_cert_info
        elif ldap_cert_info:
            is_temp_cert = True
            cert_path = "login_temp_cert.cer"
            with open(cert_path, "w") as cert_file:
                cert_file.write(ldap_cert_info)

        # Build the correct DN for binding
        user = request.args["cn"]
        dn = f"uid={user}"
        if ldap_user_ou:
            dn += f",ou={ldap_user_ou}"
        if ldap_base_dn:
            dn += f",{ldap_base_dn}"

        ldaps_controller = LdapsController(
            server_address=ldap_server,
            path_to_cert_file=cert_path,
            port=ldap_port
        )

        result = ldaps_controller.connect(
            bind_dn=dn,
            password=request.args["password"]
        )

        if not result:
            print("User | Error | User not found")
            return jsonify({
                "status": "400",
                "message": "User not found"
            }), 400

        token = generate_token(16)
        USERS_TOKENS.append(token)
        return jsonify({
            "status": "200",
            "message": token
        }), 200

    finally:
        if is_temp_cert and cert_path and os.path.exists(cert_path):
            os.remove(cert_path)


@app.route('/disconnect', methods=['GET'])
def disconnect():
    """
    delete user token from USERS_TOKEN array
    """
    token = request.args["token"]
    USERS_TOKENS.remove(token)
    return jsonify({
        "status": "200",
        "message": "Successfully disconnected"
    }), 200


@app.route('/checklist/get', methods=['GET'])
def checklist_get():
    """
    :return: ping result
    """

    json_crtl = JsonCrtl("infrastructure/persistence/checklist.json")
    response = json_crtl.read()

    return response, 200


@app.route('/checklist/update', methods=['PUT'])
def checklist_update():
    """
    This route permit to update checklist
    Take as arg checklist file
    :return: bool depend on success of checklist updating
    """

    for x in request.files:
        print(x)

    if 'checklist' not in request.files:
        print("Checklist Update | Error | Missing args")
        return jsonify({
            "status": "400",
            "message": "Missing args"
        }), 400

    file = request.files["checklist"]

    if not args_checker.args_file(file):
        print("Checklist Update | Error | Missing args")
        return jsonify({
            "status": "400",
            "message": "Missing args"
        }), 400

    print("Checklist Update | Info | File ok, starting...")

    file_content = file.read()
    print(file_content)

    json_crtl = JsonCrtl("infrastructure/persistence/checklist.json")

    response = jsonify(json_crtl.update(file_content))

    return response, 200


def test_proxmox_connection(server, node, token):
    """
    Tests the connection to the Proxmox server and a specific node.
    """
    if not server or not node or not token:
        return False, "Proxmox server, node, and token are required."
    try:
        headers = {'Authorization': f'PVEAPIToken={token}'}
        response = requests.get(f'https://{server}:8006/api2/json/nodes/{node}/status', headers=headers, verify=False, timeout=5)
        response.raise_for_status()
        return True, "Proxmox connection successful."
    except requests.exceptions.RequestException as e:
        return False, f"Proxmox connection failed: {str(e)}"


def test_ldaps_connection(server, port, base_dn, cert_info=None):
    """
    Tests the connection to the LDAPS server with an anonymous bind.
    """
    if not server or not port or not base_dn or not cert_info:
        return False, "LDAPS server, port, base DN, and certificate are required."

    cert_path = None
    is_temp_cert = False
    if cert_info and os.path.exists(cert_info):
        cert_path = cert_info
    elif cert_info:
        is_temp_cert = True
        cert_path = "temp_cert.cer"
        try:
            with open(cert_path, "w") as cert_file:
                cert_file.write(cert_info)
        except IOError as e:
            return False, f"Failed to write temporary certificate: {e}"

    try:
        presenter = LdapsPresenter(server_address=server, port=int(port), path_to_cert_file=cert_path)
        presenter.set_server()
        is_ok, message = presenter.test_connection_and_search(base_dn)
        return is_ok, message
    except Exception as e:
        return False, f"LDAPS connection failed: {str(e)}"
    finally:
        # Clean up the temporary certificate file if it was created
        if is_temp_cert and cert_path and os.path.exists(cert_path):
            os.remove(cert_path)


@app.route('/test-proxmox', methods=['POST'])
def test_proxmox():
    """
    Tests the connection to a Proxmox server.
    """
    data = request.json
    proxmox_server = data.get('proxmoxServer')
    proxmox_node = data.get('proxmoxNode')
    proxmox_token = data.get('proxmoxToken')

    is_ok, message = test_proxmox_connection(proxmox_server, proxmox_node, proxmox_token)

    if is_ok:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 400


@app.route('/test-ldaps', methods=['POST'])
def test_ldaps():
    """
    Tests the connection to an LDAPS server.
    """
    data = request.json
    ldaps_server = data.get('ldapsServer')
    ldaps_port = data.get('ldapsPort')
    ldaps_base_dn = data.get('ldapsBaseDN')
    ldaps_cert = data.get('ldapsCert') # This can be the cert data or a path

    is_ok, message = test_ldaps_connection(ldaps_server, ldaps_port, ldaps_base_dn, ldaps_cert)

    if is_ok:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 400


@app.route('/stats/proxmox', methods=['GET'])
def stats_proxmox():
    """
    :return: ping result
    """

    json_crtl = JsonCrtl("infrastructure/persistence/stats.json")
    response = json_crtl.read()

    return response, 200


@app.route('/fetch-proxmox-data', methods=['GET'])
def fetch_proxmox_data():
    try:
        # Use the service layer, which contains the correct Proxmox API logic
        terraform_service = TerraformService(config_manager)
        templates = terraform_service.get_templates()
        bridges = terraform_service.get_bridges()
        return jsonify({"templates": templates, "bridges": bridges})
    except Exception as e:
        # Log the actual error for easier debugging in the future
        logging.error(f"Error fetching Proxmox data: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while fetching Proxmox data."}), 500


@app.route('/get-config', methods=['GET'])
def get_config():
    """Returns the current configuration, decrypting secrets."""
    config_keys = [
        "PROXMOX_SERVER", "NODE", "PVEAPITOKEN",
        "LDAPS_SERVER", "LDAPS_PORT", "LDAPS_CERT",
        "LDAPS_BASE_DN", "LDAPS_USER_OU"
    ]
    
    current_config = {key: config_manager.get(key) for key in config_keys}
    return jsonify(current_config)


@app.route('/save-config', methods=['POST'])
def save_config():
    """
    Saves the configuration from the control panel.
    """
    data = request.json
    
    config_to_save = {
        'PROXMOX_SERVER': data.get('proxmoxServer'),
        'NODE': data.get('proxmoxNode'),
        'PVEAPITOKEN': data.get('proxmoxToken'),
        'LDAPS_SERVER': data.get('ldapsServer'),
        'LDAPS_PORT': data.get('ldapsPort'),
        'LDAPS_CERT': data.get('ldapsCert'),
        'LDAPS_BASE_DN': data.get('ldapsBaseDN'),
        'LDAPS_USER_OU': data.get('ldapsUserOU')
    }

    if config_manager.save_config(config_to_save):
        return jsonify({"status": "success", "message": "Configuration saved successfully."}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to save configuration."}), 500


@app.route('/run-terraform', methods=['POST'])
def run_terraform():
    if 'case' not in request.json:
        return jsonify({'error': 'Case must be provided'}), 400

    case = request.json['case']
    terraform_script_path = case
    try:
        state_file_name = TerraformService.generate_state_file_name(
            case, request.json)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # Common required fields
    common_required_fields = ['clone']
    optional_fields = ['cores', 'sockets', 'memory', 'disk_size',
                       'network_model', 'nameserver', 'network_config_type']

    tfvars = {}
    errors = []

    # Collect common required fields
    for field in common_required_fields:
        if field in request.json:
            tfvars[field] = request.json[field]
        else:
            errors.append(f'{field} is required')

    # Case-specific fields
    if case == 'Deploy-1':
        case_specific_required_fields = [
            'vm_name', 'vm_id', 'ip', 'gw', 'network_bridge', 'network_tag']
    elif case == 'Deploy-any-count':
        case_specific_required_fields = [
            'base_name', 'vm_count', 'start_vmid', 'start_ip', 'gw', 'network_bridge', 'network_tag']
    elif case == 'Deploy-any-names':
        case_specific_required_fields = [
            'hostnames', 'start_vmid', 'start_ip', 'gw', 'network_bridge', 'network_tag']

    # Collect case-specific required fields
    for field in case_specific_required_fields:
        if field in request.json:
            tfvars[field] = request.json[field]
        else:
            errors.append(f'{field} is required')

    # Collect optional fields
    for field in optional_fields:
        if field in request.json:
            tfvars[field] = request.json[field]
        elif field == 'network_config_type':
            tfvars[field] = 'dhcp'

    if errors:
        return jsonify({'error': 'Missing required fields', 'details': errors}), 400

    try:
        print(tfvars)
        # Write the terraform.tfvars file
        TerraformService.write_tfvars_file(terraform_script_path, tfvars)
        print("Data written in terraform.tfvars")
        # Run Terraform command
        output, error = TerraformService.handle_terraform_command(
            terraform_script_path, state_file_name)

        if error:
            return jsonify({'output': output, 'error': error}), 500

        return jsonify({'output': output, 'error': None}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/apps', methods=['GET'])
def list_apps():
    sftp = connect_sftp()
    sftp.chdir(SFTP_BASE_PATH)
    app_folders = []

    for item in sftp.listdir():
        if item.startswith('.') or item == '.git':
            continue
        if not is_directory(sftp, item):
            continue
        try:
            sftp.chdir(item)
            files = sftp.listdir()
            if 'description.txt' in files:
                with sftp.open('description.txt') as f:
                    description = f.read().decode()
                app_folders.append({
                    'name': item,
                    'description': description.strip(),
                    'logo_url': f'/apps/{item}/logo'
                })
            sftp.chdir('..')
        except IOError:
            continue
    sftp.close()
    return jsonify(app_folders)

@app.route('/apps/<app_name>/logo', methods=['GET'])
def get_logo(app_name):
    sftp = connect_sftp()
    try:
        sftp.chdir(f"{SFTP_BASE_PATH}/{app_name}")
        local_path = os.path.join(tempfile.gettempdir(), f"logo.png")
        sftp.get('logo.png', local_path)
        return send_file(local_path, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 404
    finally:
        sftp.close()

@app.route('/install/<app_name>', methods=['POST', 'GET'])
def install_app(app_name):
    sftp = connect_sftp()

    local_path = os.path.join(LOCAL_APP_DIR, app_name)

    if os.path.exists(local_path):
        shutil.rmtree(local_path)

    os.makedirs(local_path, exist_ok=True)

    try:
        sftp.chdir(f"{SFTP_BASE_PATH}/{app_name}")
        for file in sftp.listdir():
            sftp.get(file, os.path.join(local_path, file))

        success, output_or_error = execute_terraform(local_path)
        if not success:
            return jsonify({'error': 'Terraform error', 'details': output_or_error}), 500

        return jsonify({'status': 'success', 'output': output_or_error})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        sftp.close()



@app.route('/validate-config', methods=['POST'])
def validate_config():
    data = request.json
    errors = []
    vmid_set = set()
    ip_set = set()
    roles_windows_server = ['ADDS', 'DNS', 'DHCP', 'IIS']
    roles_linux_server = ['Web Server', 'Database', 'File Server']
    os_versions_windows_server = ['2016', '2019', '2022']
    os_versions_linux_server = [
        'debian-12.4.0-amd64-netinst.iso',
        'debian-12.5.0-amd64-netinst.iso', 
        'noble-server-cloudimg-amd64.img',
        'ubuntu-24.04-desktop-amd64.iso',
        'debian-12-standard_12.2-1_amd64.tar.zst',
        'ubuntu-20.04-standard_20.04-1_amd64.tar.gz',
        'ubuntu-24.04-standard_24.04-2_amd64.tar.zst'
    ]
    machines = data.get('machines', [])
    if not machines:
        errors.append('No machines defined.')
    for idx, m in enumerate(machines):
        base_type = m.get('baseType') or (m.get('id', '').split('-')[0])
        name = m.get('name') or m.get('id')
        adv = m.get('advanced', {})
        # VMID
        vmid = adv.get('vmid') or (100 + idx)
        if not isinstance(vmid, int) or vmid <= 0 or vmid >= 10000:
            errors.append(f'{name}: Invalid or missing VMID.')
        if vmid in vmid_set:
            errors.append(f'{name}: Duplicate VMID ({vmid}).')
        vmid_set.add(vmid)
        # Name
        if not name or not isinstance(name, str) or not name.strip():
            errors.append(f'{name}: Name is required.')
        # IP (only require for static mode)
        if base_type != 'vmPack':
            ip_mode = adv.get('ip_mode', 'dhcp')
            if ip_mode == 'static':
                ip = adv.get('ip_address')
                if not ip or not isinstance(ip, str) or not is_valid_ip(ip):
                    errors.append(f'{name}: Invalid or missing IP address.')
                if ip in ip_set:
                    errors.append(f'{name}: Duplicate IP ({ip}).')
                ip_set.add(ip)
        # OS Version
        if base_type == 'windowsServer' and adv.get('os_version') not in os_versions_windows_server:
            errors.append(f'{name}: Invalid or missing Windows Server OS version.')
        if base_type == 'linuxServer' and adv.get('os_version') not in os_versions_linux_server:
            errors.append(f'{name}: Invalid or missing Linux Server OS version.')
        # Roles
        roles = m.get('roles', [])
        if base_type == 'windowsServer' and not all(r in roles_windows_server for r in roles):
            errors.append(f'{name}: Invalid roles selected.')
        if base_type == 'linuxServer' and not all(r in roles_linux_server for r in roles):
            errors.append(f'{name}: Invalid roles selected.')
        # VM Pack count
        if base_type == 'vmPack':
            count = m.get('group', {}).get('count')
            if not isinstance(count, int) or count < 1 or count > 10:
                errors.append(f'{name}: VM Pack count must be 1-10.')
        # VLANs
        vlans = m.get('vlans', [])
        if vlans:
            if not isinstance(vlans, list):
                errors.append(f'{name}: VLANs must be a list.')
            else:
                seen_vlans = set()
                for v in vlans:
                    if not v or (not isinstance(v, (str, int))):
                        errors.append(f'{name}: VLANs must be non-empty strings or numbers.')
                    if v in seen_vlans:
                        errors.append(f'{name}: Duplicate VLAN ({v}).')
                    seen_vlans.add(v)
    if errors:
        return jsonify({'valid': False, 'errors': errors}), 200
    return jsonify({'valid': True}), 200


def is_valid_ip(ip):
    import re
    return re.match(r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip) is not None


@app.route('/deploy-machines', methods=['POST'])
def deploy_machines():
    """Deploy machines from Conceptify using individual Terraform deployments"""
    try:
        data = request.json
        machines = data.get('machines', [])
        
        if not machines:
            return jsonify({'error': 'No machines provided for deployment'}), 400
        
        # Deploy all machines using the deployment service
        results = deployment_service.deploy_machines(machines)
        
        # Check if any deployments failed
        failed_deployments = [r for r in results if r['status'] == 'error']
        successful_deployments = [r for r in results if r['status'] == 'success']
        
        response = {
            'total_machines': len(machines),
            'successful': len(successful_deployments),
            'failed': len(failed_deployments),
            'results': results
        }
        
        if failed_deployments:
            response['message'] = f"{len(successful_deployments)} machines deployed successfully, {len(failed_deployments)} failed"
            return jsonify(response), 207  # Multi-status
        else:
            response['message'] = f"All {len(machines)} machines deployed successfully"
            return jsonify(response), 200
            
    except Exception as e:
        logging.error(f"Error in deploy_machines: {e}", exc_info=True)
        return jsonify({'error': f'Deployment service error: {str(e)}'}), 500


@app.route('/list-deployments', methods=['GET'])
def list_deployments():
    """List all current deployments"""
    try:
        deployments = deployment_service.list_deployments()
        return jsonify({'deployments': deployments}), 200
    except Exception as e:
        logging.error(f"Error listing deployments: {e}", exc_info=True)
        return jsonify({'error': f'Failed to list deployments: {str(e)}'}), 500


@app.route('/destroy-machine/<machine_id>', methods=['DELETE'])
def destroy_machine(machine_id):
    """Destroy a specific machine deployment"""
    try:
        result = deployment_service.destroy_machine(machine_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logging.error(f"Error destroying machine {machine_id}: {e}", exc_info=True)
        return jsonify({'error': f'Failed to destroy machine: {str(e)}'}), 500


@app.route('/deployed-machines', methods=['GET'])
def get_deployed_machines():
    """Get all deployed machines for Conceptify display"""
    try:
        machines = tracking_service.get_deployed_machines()
        return jsonify({'machines': machines}), 200
    except Exception as e:
        logging.error(f"Error getting deployed machines: {e}", exc_info=True)
        return jsonify({'error': f'Failed to get deployed machines: {str(e)}'}), 500


@app.route('/machine-health/<machine_id>', methods=['GET'])
def get_machine_health(machine_id):
    """Get health status of a specific machine"""
    try:
        machine = tracking_service.get_machine_by_id(machine_id)
        if not machine:
            return jsonify({'error': 'Machine not found'}), 404
        
        # Extract VM ID from machine config
        vm_id = None
        try:
            config = machine.get('config', {})
            # Try to get VM ID from various sources
            if 'vm_id' in config:
                vm_id = config['vm_id']
            elif 'id' in config:
                # If no vm_id, try to extract from deployment
                deployment_path = f"deployments/{machine_id}/terraform.tfvars"
                if os.path.exists(deployment_path):
                    with open(deployment_path, 'r') as f:
                        content = f.read()
                        import re
                        vm_id_match = re.search(r'vm_id\s*=\s*(\d+)', content)
                        if vm_id_match:
                            vm_id = int(vm_id_match.group(1))
        except:
            pass
        
        if vm_id:
            health_info = health_check_service.comprehensive_health_check(machine_id, vm_id)
            if health_info:
                # Update tracking with latest health info
                tracking_service.update_machine_status(
                    machine_id, 
                    health_info["status"], 
                    health_info["ip_address"]
                )
                return jsonify(health_info), 200
        
        return jsonify({'error': 'Unable to perform health check'}), 500
        
    except Exception as e:
        logging.error(f"Error getting machine health {machine_id}: {e}", exc_info=True)
        return jsonify({'error': f'Failed to get machine health: {str(e)}'}), 500


@app.route('/update-machine/<machine_id>', methods=['PUT'])
def update_machine(machine_id):
    """Update a deployed machine's configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update machine configuration
        result = deployment_service.update_machine(machine_id, data)
        
        if result.get('success'):
            return jsonify({'message': 'Machine updated successfully'}), 200
        else:
            return jsonify({'error': result.get('error', 'Failed to update machine')}), 500
    except Exception as e:
        logging.error(f"Error updating machine {machine_id}: {e}", exc_info=True)
        return jsonify({'error': f'Failed to update machine: {str(e)}'}), 500


@app.route('/boot-all-machines', methods=['POST'])
def boot_all_machines():
    """Boot all deployed machines via Proxmox API"""
    try:
        logging.info("=== Starting boot all machines operation ===")
        
        # Get all deployed machines
        machines = tracking_service.get_deployed_machines()
        logging.info(f"Found {len(machines)} machines in deployed_machines.json")
        
        if not machines:
            logging.warning("No deployed machines found in tracking file")
            return jsonify({'message': 'No deployed machines found'}), 200
        
        results = []
        success_count = 0
        
        for i, machine in enumerate(machines, 1):
            machine_id = machine.get('id')
            machine_name = machine.get('name', 'Unknown')
            
            logging.info(f"[{i}/{len(machines)}] Processing machine: {machine_name} (ID: {machine_id})")
            
            # Extract VM ID from machine config - try multiple sources
            vm_id = None
            config = machine.get('config', {})
            
            # Check multiple possible locations for VM ID
            if 'vm_id' in config:
                vm_id = config['vm_id']
                logging.info(f"  Found VM ID in config.vm_id: {vm_id}")
            elif 'vmid' in config:
                vm_id = config['vmid']
                logging.info(f"  Found VM ID in config.vmid: {vm_id}")
            elif 'id' in config:
                vm_id = config['id']
                logging.info(f"  Found VM ID in config.id: {vm_id}")
            else:
                # Try to extract from deployment result
                deployment_result = machine.get('deployment_result', {})
                output = deployment_result.get('output', '')
                
                # Try to extract VM ID from terraform output
                import re
                vm_id_match = re.search(r'vm_id\s*=\s*(\d+)', output)
                if vm_id_match:
                    vm_id = int(vm_id_match.group(1))
                    logging.info(f"  Extracted VM ID from deployment output: {vm_id}")
                else:
                    logging.warning(f"  No VM ID found for machine {machine_name}")
            
            if vm_id:
                try:
                    # Check if the container is already running
                    from proxmoxer import ProxmoxAPI
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    proxmox_server = deployment_service.config_manager.get("PROXMOX_SERVER")
                    proxmox_token = deployment_service.config_manager.get("PVEAPITOKEN")
                    proxmox_node = deployment_service.config_manager.get("NODE")
                    user_realm, token_rest = proxmox_token.split("!", 1)
                    token_name, token_value = token_rest.split("=", 1)
                    proxmox = ProxmoxAPI(
                        proxmox_server,
                        user=user_realm,
                        token_name=token_name,
                        token_value=token_value,
                        verify_ssl=False
                    )
                    ct = proxmox.nodes(proxmox_node).lxc(int(vm_id))
                    status = ct.status.current.get()
                    if status.get('status') == 'running':
                        logging.info(f"  ℹ️  {machine_name} (VM ID: {vm_id}) is already running.")
                        results.append({
                            'machine_id': machine_id,
                            'machine_name': machine_name,
                            'vm_id': vm_id,
                            'status': 'already_running',
                            'message': f'{machine_name} is already running.'
                        })
                        continue

                    logging.info(f"  Attempting to boot VM/Container with ID: {vm_id}")
                    
                    # Use the deployment service's boot method
                    boot_success = deployment_service._start_vm_via_proxmox_api(vm_id)
                    
                    if boot_success:
                        # Fetch eth0 IP using proxmoxer with comprehensive logging
                        try:
                            from proxmoxer import ProxmoxAPI
                            import urllib3
                            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                            proxmox_server = deployment_service.config_manager.get("PROXMOX_SERVER")
                            proxmox_token = deployment_service.config_manager.get("PVEAPITOKEN")
                            proxmox_node = deployment_service.config_manager.get("NODE")
                            user_realm, token_rest = proxmox_token.split("!", 1)
                            token_name, token_value = token_rest.split("=", 1)
                            proxmox = ProxmoxAPI(
                                proxmox_server,
                                user=user_realm,
                                token_name=token_name,
                                token_value=token_value,
                                verify_ssl=False
                            )
                            
                            # Wait a moment for container to fully start
                            import time
                            time.sleep(3)
                            
                            # Try multiple methods to get the IP
                            eth0_ip = None
                            
                            # Method 1: Try /interfaces endpoint
                            try:
                                logging.info(f"  Attempting to fetch interfaces for VM {vm_id}...")
                                interfaces = proxmox.nodes(proxmox_node).lxc(int(vm_id)).interfaces.get()
                                logging.info(f"  Raw interfaces response: {interfaces}")
                                
                                for iface in interfaces:
                                    logging.info(f"    Interface: {iface}")
                                    if iface.get('name') == 'eth0':
                                        inet = iface.get('inet')
                                        inet6 = iface.get('inet6')
                                        logging.info(f"      eth0 inet: {inet}, inet6: {inet6}")
                                        if inet and '.' in str(inet) and not str(inet).startswith('127.'):
                                            eth0_ip = str(inet).split('/')[0]
                                            logging.info(f"      Found valid IP from inet: {eth0_ip}")
                                            break
                            except Exception as e:
                                logging.error(f"  Error with /interfaces endpoint: {e}")
                            
                            # Method 2: Try /status/current endpoint
                            if not eth0_ip:
                                try:
                                    logging.info(f"  Trying /status/current for VM {vm_id}...")
                                    status = proxmox.nodes(proxmox_node).lxc(int(vm_id)).status.current.get()
                                    logging.info(f"  Status response: {status}")
                                    # Look for any IP-like data in status
                                    for key, value in status.items():
                                        if 'ip' in key.lower() and isinstance(value, str) and '.' in value:
                                            if not value.startswith('127.') and value != 'dhcp':
                                                eth0_ip = value.split('/')[0]
                                                logging.info(f"      Found IP in status.{key}: {eth0_ip}")
                                                break
                                except Exception as e:
                                    logging.error(f"  Error with /status/current endpoint: {e}")
                            
                            # Method 3: Try /config endpoint
                            if not eth0_ip:
                                try:
                                    logging.info(f"  Trying /config for VM {vm_id}...")
                                    config = proxmox.nodes(proxmox_node).lxc(int(vm_id)).config.get()
                                    logging.info(f"  Config response: {config}")
                                    # Look for network config with actual IP
                                    for key, value in config.items():
                                        if key.startswith('net') and isinstance(value, str):
                                            logging.info(f"      Network config {key}: {value}")
                                            if 'ip=' in value and 'dhcp' not in value.lower():
                                                import re
                                                ip_match = re.search(r'ip=([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', value)
                                                if ip_match:
                                                    eth0_ip = ip_match.group(1)
                                                    logging.info(f"      Found IP in config.{key}: {eth0_ip}")
                                                    break
                                except Exception as e:
                                    logging.error(f"  Error with /config endpoint: {e}")
                            
                            # Method 4: Use health check service as fallback
                            if not eth0_ip:
                                logging.info(f"  Trying health check service for VM {vm_id}...")
                                health_info = health_check_service.get_machine_ip_from_proxmox(machine_id, vm_id)
                                if health_info and health_info.get('ip_address'):
                                    potential_ip = health_info['ip_address']
                                    if potential_ip and '.' in potential_ip and not potential_ip.startswith('127.') and potential_ip.lower() not in ('dhcp', 'static', 'unknown'):
                                        eth0_ip = potential_ip
                                        logging.info(f"      Found IP via health check: {eth0_ip}")
                            
                            # If no real IP found, use config type as fallback
                            if not eth0_ip or eth0_ip.lower() in ('dhcp', 'static', 'unknown'):
                                adv = config.get('advanced', {})
                                fallback_value = adv.get('ip_mode', 'Unknown')
                                logging.info(f"  No real IP found, using fallback: {fallback_value}")
                                eth0_ip = fallback_value
                            
                            # Update the machine status
                            tracking_service.update_machine_status(machine_id, 'running', eth0_ip)
                            logging.info(f"  ✅ Updated {machine_name} (ID: {machine_id}) with IP/type: {eth0_ip}")
                            
                        except Exception as e:
                            logging.error(f"  ❌ Error fetching IP for {machine_name} (ID: {machine_id}): {e}")
                            # Still update with fallback
                            adv = config.get('advanced', {})
                            fallback_value = adv.get('ip_mode', 'Unknown')
                            tracking_service.update_machine_status(machine_id, 'running', fallback_value)
                            logging.info(f"  Updated {machine_name} with fallback: {fallback_value}")
                        success_count += 1
                        logging.info(f"  ✅ Successfully started {machine_name} (VM ID: {vm_id})")
                        results.append({
                            'machine_id': machine_id,
                            'machine_name': machine_name,
                            'vm_id': vm_id,
                            'status': 'success',
                            'message': f'Successfully started {machine_name}'
                        })
                    else:
                        logging.error(f"  ❌ Failed to start {machine_name} (VM ID: {vm_id})")
                        results.append({
                            'machine_id': machine_id,
                            'machine_name': machine_name,
                            'vm_id': vm_id,
                            'status': 'failed',
                            'message': f'Failed to start {machine_name}'
                        })
                except Exception as e:
                    logging.error(f"  ❌ Error starting {machine_name} (VM ID: {vm_id}): {str(e)}")
                    results.append({
                        'machine_id': machine_id,
                        'machine_name': machine_name,
                        'vm_id': vm_id,
                        'status': 'error',
                        'message': f'Error starting {machine_name}: {str(e)}'
                    })
            else:
                logging.warning(f"  ⚠️  Skipping {machine_name} - No VM ID found")
                results.append({
                    'machine_id': machine_id,
                    'machine_name': machine_name,
                    'vm_id': None,
                    'status': 'skipped',
                    'message': f'No VM ID found for {machine_name}'
                })
        
        num_running = sum(1 for r in results if r['status'] in ('success', 'already_running'))
        final_message = f'Boot operation completed. {num_running}/{len(machines)} machines are running (started or already running).'
        logging.info(f"=== Boot operation completed: {num_running}/{len(machines)} running ===")
        
        return jsonify({
            'message': final_message,
            'total_machines': len(machines),
            'success_count': num_running,
            'results': results
        }), 200
        
    except Exception as e:
        logging.error(f"Error booting all machines: {e}", exc_info=True)
        return jsonify({'error': f'Failed to boot machines: {str(e)}'}), 500


@app.route('/check-deployed-machines', methods=['GET'])
def check_deployed_machines():
    """Check if deployed machines exist for enabling/disabling boot button"""
    try:
        machines = tracking_service.get_deployed_machines()
        has_machines = len(machines) > 0
        
        return jsonify({
            'has_machines': has_machines,
            'machine_count': len(machines)
        }), 200
        
    except Exception as e:
        logging.error(f"Error checking deployed machines: {e}", exc_info=True)
        return jsonify({
            'has_machines': False,
            'machine_count': 0,
            'error': str(e)
        }), 200  # Return 200 so frontend can handle gracefully


@app.route('/refresh-ips', methods=['POST'])
def refresh_ips():
    """Simple endpoint to refresh IPs for all deployed machines"""
    try:
        machines = tracking_service.get_deployed_machines()
        if not machines:
            return jsonify({'message': 'No deployed machines found'}), 200
        
        updated_count = 0
        results = []
        
        # Get Proxmox config
        proxmox_server = config_manager.get("PROXMOX_SERVER")
        proxmox_token = config_manager.get("PVEAPITOKEN")
        proxmox_node = config_manager.get("NODE")
        
        if not all([proxmox_server, proxmox_token, proxmox_node]):
            return jsonify({'error': 'Missing Proxmox configuration'}), 500
        
        # Parse token for proxmoxer
        try:
            user_realm, token_rest = proxmox_token.split("!", 1)
            token_name, token_value = token_rest.split("=", 1)
        except Exception as e:
            return jsonify({'error': f'Invalid Proxmox token format: {e}'}), 500
        
        # Initialize proxmoxer
        try:
            from proxmoxer import ProxmoxAPI
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            proxmox = ProxmoxAPI(
                proxmox_server,
                user=user_realm,
                token_name=token_name,
                token_value=token_value,
                verify_ssl=False
            )
        except Exception as e:
            return jsonify({'error': f'Failed to connect to Proxmox: {e}'}), 500
        
        for machine in machines:
            machine_id = machine.get('id')
            machine_name = machine.get('name', 'Unknown')
            vm_id = machine_id  # Use machine ID as VM ID
            
            logging.info(f"Processing machine: {machine_name} (ID: {machine_id}, VM ID: {vm_id})")
            
            try:
                real_ip = None
                
                # Always use LXC container logic for IP fetching
                try:
                    # Method 1: Try interfaces endpoint
                    logging.info(f"Trying interfaces endpoint for VM {vm_id}")
                    interfaces = proxmox.nodes(proxmox_node).lxc(int(vm_id)).interfaces.get()
                    logging.info(f"Interfaces response for {vm_id}: {interfaces}")
                    
                    for iface in interfaces:
                        if iface.get('name') == 'eth0':
                            inet = iface.get('inet')
                            logging.info(f"Found eth0 interface for {vm_id}: {inet}")
                            if inet and '.' in str(inet) and not str(inet).startswith('127.'):
                                real_ip = str(inet).split('/')[0]
                                logging.info(f"Extracted IP for {vm_id}: {real_ip}")
                                break
                except Exception as e:
                    logging.warning(f"LXC interfaces call failed for {vm_id}: {e}")
                
                # Method 2: Try config endpoint if interfaces didn't work
                if not real_ip:
                    try:
                        logging.info(f"Trying config endpoint for VM {vm_id}")
                        config = proxmox.nodes(proxmox_node).lxc(int(vm_id)).config.get()
                        logging.info(f"Config response for {vm_id}: {config}")
                        
                        for key, value in config.items():
                            if key.startswith('net') and 'ip=' in str(value) and 'dhcp' not in str(value).lower():
                                import re
                                ip_match = re.search(r'ip=([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', str(value))
                                if ip_match:
                                    real_ip = ip_match.group(1)
                                    logging.info(f"Extracted IP from config for {vm_id}: {real_ip}")
                                    break
                    except Exception as e:
                        logging.warning(f"LXC config call failed for {vm_id}: {e}")
                
                # Update machine status
                if real_ip:
                    logging.info(f"Updating machine {machine_id} with IP: {real_ip}")
                    tracking_service.update_machine_status(machine_id, 'running', real_ip)
                    updated_count += 1
                    results.append(f"{machine_name}: {real_ip}")
                else:
                    current_ip = machine.get('ip_address', 'dhcp')
                    logging.warning(f"No IP found for {machine_id}, keeping current: {current_ip}")
                    results.append(f"{machine_name}: {current_ip} (no IP found)")
                    
            except Exception as e:
                logging.error(f"Error processing machine {machine_id}: {e}")
                results.append(f"{machine_name}: error - {str(e)}")
        
        return jsonify({
            'message': f'Refreshed IPs for {updated_count}/{len(machines)} machines',
            'results': results,
            'total_machines': len(machines),
            'updated_count': updated_count
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to refresh IPs: {str(e)}'}), 500


@app.route('/ping', methods=['GET'])
def ping_machine():
    machine_id = request.args.get('machine_id')
    if not machine_id:
        return jsonify({'success': False, 'error': 'Missing machine_id'}), 400
    tracking_service = get_tracking_service()
    machine = tracking_service.get_machine_by_id(machine_id)
    if not machine or not machine.get('ip_address'):
        return jsonify({'success': False, 'error': 'Machine or IP not found'}), 404
    config_manager = get_config_manager()
    health_check_service = HealthCheckService(config_manager)
    ip = machine['ip_address']
    reachable = health_check_service.ping_machine(ip)
    return jsonify({'success': True, 'ip_address': ip, 'reachable': reachable})


if __name__ == '__main__':
    host = config_manager.get('BACKEND_HOST', '0.0.0.0')
    port = int(config_manager.get('BACKEND_PORT', 5000))
    app.run(host=host, debug=True, port=port)
