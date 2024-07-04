"""
Main app file, all api route are declared there
"""

from flask import Flask, request, jsonify, abort
from flask_cors import CORS

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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
