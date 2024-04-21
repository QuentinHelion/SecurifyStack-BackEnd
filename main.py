"""
Main app file, all api route are declared there
"""

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route('/checklist/get', methods=['GET'])
def checklist_get():
    """
    :return: ping result
    """
    from application.interfaces.controllers.crtl_json import JsonCrtl

    json_crtl = JsonCrtl("infrastructure/persistence/checklist.json")
    response = json_crtl.read()

    return response


@app.route('/checklist/update', methods=['GET'])
def checklist_update():
    """
    :return: bool depend on success of checklist update
    """

    response = "/checklist/update"

    return response


if __name__ == '__main__':
    app.run(debug=True, port=5000)
