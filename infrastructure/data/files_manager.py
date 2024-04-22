"""
This file contain all method to manage file
"""
import os


class FilesManager:
    """
    FilesManager object
    """

    @staticmethod
    def exist(file_path):
        """
        :return: bool depend on if file exist
        """
        return os.path.exists(file_path)

    def create(self, file_path):
        """
        create file
        """
        with open(file_path, 'w', encoding="utf-8"):
            pass  # Do nothing, just creating the file

        return self.exist(file_path)

    def delete(self, file_path):
        """
        check if file exist and delete it
        """
        if self.exist(file_path):
            os.remove(file_path)

        return not self.exist(file_path)
