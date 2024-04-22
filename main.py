"""
Main app file, all api route are declared there
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

from application.interfaces.controllers.crtl_json import JsonCrtl
from infrastructure.data.args import Args

args_checker = Args()

app = Flask(__name__)
CORS(app)


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
    file = request.files["checklist"]

    if not args_checker.args_file(file):
        return jsonify({
            "status": "400",
            "message": "Missing args"
        }), 400

    if 'checklist' not in request.files:
        return jsonify({
            "status": "400",
            "message": "Missing args"
        }), 400

    print("Checklist Update | Info | File ok, starting...")

    file_content = file.read()
    print(file_content)

    json_crtl = JsonCrtl("infrastructure/persistence/checklist.json")
    response = json_crtl.update(file_content)

    return jsonify(response), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
