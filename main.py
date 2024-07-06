"""
Main app file, all api route are declared there
"""

from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import os
import subprocess
from application.interfaces.controllers.crtl_json import JsonCrtl
from application.interfaces.controllers.ldaps_controller import LdapsController
from infrastructure.data.args import Args
from infrastructure.data.env_reader import EnvReader
from infrastructure.data.token import generate_token

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
        if request.args["token"] not in USERS_TOKENS:
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

def write_tfvars_file(terraform_script_path, tfvars):
    tfvars_content = '\n'.join([f'{key} = "{value}"' if isinstance(value, str) else f'{key} = {value}' for key, value in tfvars.items()])
    tfvars_file_path = os.path.join('/root/TerraformCode', terraform_script_path, 'terraform.tfvars')
    with open(tfvars_file_path, 'w') as tfvars_file:
        tfvars_file.write(tfvars_content)

def run_terraform_command(terraform_script_path):
    command = f'cd /root/TerraformCode/{terraform_script_path} && terraform init && terraform plan && terraform apply -auto-approve'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode('utf-8'), error.decode('utf-8')

@app.route('/run-terraform', methods=['POST'])
def run_terraform():
    if 'case' not in request.json:
        return jsonify({'error': 'Case not provided'}), 400

    case = request.json['case']
    terraform_script_path = ''

    if case == 'Deploy-1':
        terraform_script_path = 'Deploy-1'
    elif case == 'Deploy-any-count':
        terraform_script_path = 'Deploy-any-count'
    elif case == 'Deploy-any-names':
        terraform_script_path = 'Deploy-any-names'
    else:
        return jsonify({'error': 'Invalid case'}), 400

    # Common required fields
    common_required_fields = ['clone']
    optional_fields = ['cores', 'sockets', 'memory', 'disk_size', 'network_model', 'nameserver']

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
        case_specific_required_fields = ['vm_name', 'vm_id', 'ip', 'gw', 'network_bridge', 'network_tag']
    elif case == 'Deploy-any-count':
        case_specific_required_fields = ['base_name', 'count', 'start_vmid', 'start_ip', 'gw', 'network_bridge', 'network_tag']
    elif case == 'Deploy-any-names':
        case_specific_required_fields = ['hostnames', 'count', 'start_vmid', 'start_ip', 'gw', 'network_bridge', 'network_tag']
        
        # Check if the number of hostnames matches the count
        if 'hostnames' in request.json and 'count' in request.json:
            hostnames = request.json['hostnames']
            count = request.json['count']
            if len(hostnames) != count:
                errors.append('The number of hostnames does not match the count')

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

    if errors:
        return jsonify({'error': 'Missing required fields', 'details': errors}), 400

    try:
        print(tfvars)
        # Write the terraform.tfvars file
        write_tfvars_file(terraform_script_path, tfvars)
        print("data written in terraform.tfvars")
        # Run Terraform command
        output, error = run_terraform_command(terraform_script_path)

        return jsonify({'output': output.splitlines()[-2], 'error': error}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
