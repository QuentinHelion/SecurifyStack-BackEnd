"""
Main app file, all api route are declared there
"""

from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import os
import subprocess
import requests
from application.interfaces.controllers.crtl_json import JsonCrtl
from application.interfaces.controllers.ldaps_controller import LdapsController
from application.interfaces.presenters.ldaps_presenter import LdapsPresenter
from infrastructure.data.args import Args
from infrastructure.data.config_manager import ConfigManager
from infrastructure.data.token import generate_token
from application.services.terraform_service import TerraformService

args_checker = Args()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

config_manager = ConfigManager()

USERS_TOKENS = []
EXCLUDED_ROUTES = ["/login", "/test-proxmox", "/test-ldaps", "/save-config"]


@app.before_request
def before_request():
    """
    Before request, check if token is give and if it is valid
    """
    if request.path not in EXCLUDED_ROUTES:
        if "token" in request.args:
            if request.args["token"] not in USERS_TOKENS:
                abort(
                    code=401,
                    description=jsonify({
                        "status": "401",
                        "message": "Unautorized"
                    })
                )
        else:
            abort(
                code=401,
                description=jsonify({
                    "status": "401",
                    "message": "Unautorized"
                })
            )


@app.route('/login', methods=['GET'])
def login():
    """
    :return: auth token
    """
    # Fetch all LDAP config from config manager
    ldap_server = config_manager.get("LDAPS_SERVER")
    ldap_port = int(config_manager.get("LDAPS_SERVER_PORT"))
    ldap_cert = config_manager.get("LDAPS_CERT", "infrastructure/persistence/certificats/ssrootca.cer")
    ldap_base_dn = config_manager.get("LDAPS_BASE_DN")  # e.g. 'dc=test,dc=local'
    ldap_user_ou = config_manager.get("LDAPS_USER_OU", "")  # e.g. 'Users' or ''

    # Build the correct DN for binding
    user = request.args["cn"]
    dn = f"uid={user}"
    if ldap_user_ou:
        dn += f",ou={ldap_user_ou}"
    if ldap_base_dn:
        dn += f",{ldap_base_dn}"

    ldaps_controller = LdapsController(
        server_address=ldap_server,
        path_to_cert_file=ldap_cert,
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
    if cert_info:
        # Check if cert_info is a valid path on the server
        if os.path.exists(cert_info):
            cert_path = cert_info
        else:
            # If not a path, assume it's content and write to a temp file
            try:
                with open("temp_cert.cer", "w") as cert_file:
                    cert_file.write(cert_info)
                cert_path = "temp_cert.cer"
                is_temp_cert = True
            except IOError as e:
                return False, f"Failed to write temporary certificate file: {str(e)}"

    try:
        presenter = LdapsPresenter(server_address=server, port=int(port), path_to_cert_file=cert_path)
        presenter.set_server()
        is_ok, message = presenter.test_connection_and_search(base_dn)
        return is_ok, message
    except Exception as e:
        return False, f"LDAPS connection failed: {str(e)}"
    finally:
        # Clean up the temporary certificate file only if we created it
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
        proxmox_server = config_manager.get('PROXMOX_SERVER')
        node = config_manager.get('NODE')
        pve_api_token = config_manager.get('PVEAPITOKEN')
        print(proxmox_server, node, pve_api_token)
        headers = {
            'Authorization': f'PVEAPIToken={pve_api_token}',
        }

        # Fetching bridges
        print("will do requests")
        bridges_response = requests.get(
            f'https://{proxmox_server}:8006/api2/json/nodes/{node}/network', headers=headers, verify="infrastructure/persistence/certificats/ssrootca.cer")
        print(bridges_response)
        bridges_response.raise_for_status()  # Raise an HTTPError on bad status
        bridges = [bridge['iface'] for bridge in bridges_response.json()[
            'data'] if bridge['type'] == 'bridge']

        # Fetching templates
        templates_response_qemu = requests.get(
            f'https://{proxmox_server}:8006/api2/json/nodes/{node}/qemu', headers=headers, verify="infrastructure/persistence/certificats/ssrootca.cer")
        templates_response_qemu.raise_for_status()  # Raise an HTTPError on bad status
        templates_response_lxc = requests.get(
            f'https://{proxmox_server}:8006/api2/json/nodes/{node}/lxc', headers=headers, verify="infrastructure/persistence/certificats/ssrootca.cer")
        templates_response_lxc.raise_for_status()  # Raise an HTTPError on bad status

        templates = [
            vm['name'] for vm in templates_response_qemu.json()['data'] if vm.get('template') == 1
        ] + [
            container['name'] for container in templates_response_lxc.json()['data'] if container.get('template') == 1
        ]

        return jsonify({
            'bridges': bridges,
            'templates': templates
        })
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500


@app.route('/save-config', methods=['POST'])
def save_config():
    """
    Saves the configuration from the control panel.
    """
    data = request.json
    secrets = ['PVEAPITOKEN', 'LDAPS_CERT', 'PROXMOX_SERVER', 'LDAPS_SERVER', 'LDAPS_BASE_DN', 'NODE']
    
    # Map frontend keys to backend (.env) keys
    key_map = {
        "proxmoxServer": "PROXMOX_SERVER",
        "proxmoxNode": "NODE",
        "proxmoxToken": "PVEAPITOKEN",
        "ldapsServer": "LDAPS_SERVER",
        "ldapsPort": "LDAPS_SERVER_PORT",
        "ldapsCert": "LDAPS_CERT",
        "ldapsBaseDN": "LDAPS_BASE_DN",
        "ldapsUserOU": "LDAPS_USER_OU"
    }

    config_to_save = {key_map[k]: v for k, v in data.items() if k in key_map}

    if config_manager.save_config(config_to_save, secrets):
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


if __name__ == '__main__':
    host = config_manager.get('BACKEND_HOST', '0.0.0.0')
    port = int(config_manager.get('BACKEND_PORT', 5000))
    app.run(host=host, debug=True, port=port)
