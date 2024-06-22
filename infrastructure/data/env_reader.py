
"""
    Tool used to read .env file
"""
import os
from dotenv import load_dotenv


class EnvReader:
    """"
        Used to read .env file
    """
    def __init__(self, path=".env"):
        self.path = path
        self.load()

    def load(self):
        """
            Load .env file
        """
        load_dotenv(dotenv_path=self.path)

    def get(self, key, default=None):
        """
            :param key:
            :param default:
            :return: key value
        """
        return os.getenv(key, default)
