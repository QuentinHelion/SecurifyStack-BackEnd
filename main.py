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
    from application.interface.controllers.crtl_json import JsonCrtl

    read_json()

    return response

@app.route('/checklist/update', methods=['GET'])
def checklist_update():
    """
    :return: bool depend to success of checklist update
    """
    args = request.args.get('checklist', None)
    if args is None or args == '':
        response = make_response("Missing args")
        response.status_code = 400

    pinger = Pinger(
        addr=addr
    )
    ping_result = pinger.ping()
    response = make_response(jsonify(ping_result))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
