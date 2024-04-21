"""
Json controller
"""

from application.controllers.presenters.prst_json import JsonPrst
from infrastructure.data.files_manager import FilesManager


class JsonCrtl:
    """
    
    """
    def __init__(self, json_file_path):
        self.path = json_file_path
        self.file_manager = FilesManager()
        if !self.file_manager.exist(file_path):
            print("error: file not found")
            return False
        self.presenter = JsonPrst(json_file_path)
        
    def update(self, value):
        """
        Update json
        :return: bool depent of execution result
        """
        if value is None || value == "":
            print("JsonCrtl | Error | Value empty")
            return False
        return self.presenter.update_json(value)

    def read(self):
        """
        :return: json file content
        """
        return self.presenter.read_json()
