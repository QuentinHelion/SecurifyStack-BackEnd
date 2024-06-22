"""
Main app file, all api route are declared there
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

from application.interfaces.controllers.crtl_json import JsonCrtl
from application.interfaces.controllers.ldaps_controller import LdapsController
from infrastructure.data.args import Args
from infrastructure.data.env_reader import EnvReader
from infrastructure.data.token import generate_token

import random
import string

args_checker = Args()

app = Flask(__name__)
CORS(app)

env_reader = EnvReader()
env_reader.load()

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

@app.route('/login', methods=['GET'])
def login():
    """
    :return: auth token
    """
    ldaps_controller = LdapsController(
        server_address=env_reader.get("LDAP_SERVER"),
        path_to_cert_file="infrastructure/persistence/certificats/ssrootca.cer",
        port=env_reader.get("LDAPS_SERVER_PORT")
    )

    result = ldaps_controller.connect(
        CN=request.args["CN"],
        DC=request.args["DC"],
        password=request.args["password"]
    )

    if not result:
        print("User | Error | User not found")
        return jsonify({
            "status": "400",
            "message": "User not found"
        }), 400

    token = generate_token(16)

    return jsonify({
        "status": "200",
        "message": token
    }), 400


if __name__ == '__main__':
    app.run(debug=True, port=5000)
