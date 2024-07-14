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
from infrastructure.data.args import Args
from infrastructure.data.env_reader import EnvReader
from infrastructure.data.token import generate_token
from application.services.terraform_service import TerraformService

args_checker = Args()

app = Flask(__name__)
CORS(app)

env_reader = EnvReader()
env_reader.load()

USERS_TOKENS = []
EXCLUDED_ROUTES = ["/login"]


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
    ldaps_controller = LdapsController(
        server_address=env_reader.get("LDAPS_SERVER"),
        path_to_cert_file="infrastructure/persistence/certificats/ssrootca.cer",
        port=env_reader.get("LDAPS_SERVER_PORT")

    )

    result = ldaps_controller.connect(
        cn=[request.args["cn"], "Users"],
        dc=[request.args["dc"], "corp"],
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
        proxmox_server = env_reader.get('PROXMOX_SERVER')
        node = env_reader.get('NODE')
        pve_api_token = env_reader.get('PVEAPITOKEN')
        print(proxmox_server, node, pve_api_token)
        headers = {
            'Authorization': f'PVEAPIToken={pve_api_token}',
        }

        # Fetching bridges
        print("will do requests")
        bridges_response = requests.get(
            f'https://{proxmox_server}:8006/api2/json/nodes/{node}/network', headers=headers, verify=False)
        print(bridges_response)
        bridges_response.raise_for_status()  # Raise an HTTPError on bad status
        bridges = [bridge['iface'] for bridge in bridges_response.json()[
            'data'] if bridge['type'] == 'bridge']

        # Fetching templates
        templates_response_qemu = requests.get(
            f'https://{proxmox_server}:8006/api2/json/nodes/{node}/qemu', headers=headers, verify=False)
        templates_response_qemu.raise_for_status()  # Raise an HTTPError on bad status
        templates_response_lxc = requests.get(
            f'https://{proxmox_server}:8006/api2/json/nodes/{node}/lxc', headers=headers, verify=False)
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
    app.run(host='0.0.0.0', debug=True, port=5000)
