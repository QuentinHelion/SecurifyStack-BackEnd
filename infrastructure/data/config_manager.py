import os
import json
from cryptography.fernet import Fernet, InvalidToken
from dotenv import find_dotenv, set_key, load_dotenv

class ConfigManager:
    def __init__(self, config_path='infrastructure/persistence/config.json', env_path=None):
        self.config_path = config_path
        self.env_path = env_path if env_path else find_dotenv()
        self.secret_keys = ['PVEAPITOKEN', 'LDAPS_CERT', 'PROXMOX_SERVER', 'LDAPS_SERVER', 'LDAPS_BASE_DN']
        
        if not self.env_path or not os.path.exists(self.env_path):
            raise FileNotFoundError("CRITICAL: .env file not found. The application cannot start without it.")
        
        load_dotenv(dotenv_path=self.env_path)

        self.key = self._load_key()
        self.cipher = Fernet(self.key)
        self.config = self._load_config()

    def _load_key(self):
        """Loads the encryption key from .env. Raises an error if not found."""
        key = os.getenv('MASTER_KEY')
        if key:
            return key.encode()
        
        raise ValueError("CRITICAL: MASTER_KEY not found in .env file. The application cannot decrypt its configuration.")

    def _load_config(self):
        """Loads and decrypts the config.json file."""
        if not os.path.exists(self.config_path):
            return {}
        
        with open(self.config_path, 'r') as f:
            encrypted_config = json.load(f)

        decrypted_config = {}
        for key, value in encrypted_config.items():
            if key in self.secret_keys:
                if not value: # Handle empty secrets
                    decrypted_config[key] = value
                    continue
                try:
                    decrypted_config[key] = self.cipher.decrypt(value.encode()).decode()
                except InvalidToken:
                    raise ValueError(f"CRITICAL: Failed to decrypt '{key}' from config.json. The MASTER_KEY in your .env file may be incorrect or does not match this configuration.")
            else:
                decrypted_config[key] = value
        return decrypted_config

    def get(self, key, default=None):
        """Gets a value from config, falling back to environment variables."""
        return self.config.get(key, os.getenv(key, default))

    def save_config(self, new_config):
        """Encrypts secrets and saves the entire configuration."""
        full_config = self.config.copy()
        full_config.update(new_config)

        encrypted_config = {}
        for key, value in full_config.items():
            if key in self.secret_keys and value:
                encrypted_config[key] = self.cipher.encrypt(value.encode()).decode()
            else:
                encrypted_config[key] = value
        
        with open(self.config_path, 'w') as f:
            json.dump(encrypted_config, f, indent=4)
        
        # Reload the in-memory config
        self.config = self._load_config()
        return True 