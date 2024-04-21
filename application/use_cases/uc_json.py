"""
Json usage controller
"""
import json

class JsonCrtl:
    def __init__(self, json_file_path):
        self.json_file_path = json_file_path

    def read_json(self):
        """
        :return: json file content
        """
        with open(self.json_file_path, 'r') as file:
            return json.load(file)

    def update_json(self, data):
        """
        Permit update json file
        :return: json file update result
        """
        with open(self.json_file_path, 'w') as file:
            return json.dump(data, file)

