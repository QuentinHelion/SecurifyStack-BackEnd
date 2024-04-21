"""
This file contain all method to manage file
"""
import os

class FilesManager:
    def __init__(self)
    

    def create(file_path):
        """
        create file
        """
        with open(file_path, 'w'):
            pass  # Do nothing, just creating the file
        
        return self.exist(file_path)

    def delete(file_path):
        """
        check if file exist and delete it
        """
        if self.exist(file_path):
            os.remove(file_path)
            
        return !self.exist(file_path)


    def exist(file_path):
        """
        :return: bool depend if file exist
        """
        return os.path.exists(file_path)


