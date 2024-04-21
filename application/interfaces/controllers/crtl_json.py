"""
Json controller
"""

from application.interfaces.presenters.prst_json import JsonPrst
from infrastructure.data.files_manager import FilesManager


class JsonCrtl:
    """
    
    """
    def __init__(self, json_file_path):
        self.path = json_file_path
        self.file_manager = FilesManager()

        # if not self.file_manager.exist(json_file_path):
        #     print("error: file not found")
        #     return None
        self.presenter = JsonPrst(json_file_path)

    def update(self, value):
        """
        Update json
        :return: bool depent of execution result
        """
        if value is None or value == "":
            print("JsonCrtl | Error | Value empty")
            return False
        return self.presenter.update_json(value)

    def read(self):
        """
        :return: json file content
        """
        return self.presenter.read_json()
