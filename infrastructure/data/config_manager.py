import os
import json
from cryptography.fernet import Fernet
from dotenv import find_dotenv, set_key

class ConfigManager:
    def __init__(self, config_path='infrastructure/persistence/config.json', env_path=None):
        self.config_path = config_path
        self.env_path = env_path if env_path else find_dotenv()
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)
        self.config = self._load_config()

    def _load_or_generate_key(self):
        """Loads encryption key from .env or generates a new one."""
        key = os.getenv('MASTER_KEY')
        if key:
            return key.encode()
        
        # Generate new key and save it to .env
        new_key = Fernet.generate_key()
        set_key(self.env_path, 'MASTER_KEY', new_key.decode())
        return new_key

    def _load_config(self):
        """Loads and decrypts the config.json file."""
        if not os.path.exists(self.config_path):
            return {}
        
        with open(self.config_path, 'r') as f:
            encrypted_config = json.load(f)

        decrypted_config = {}
        for key, value in encrypted_config.items():
            try:
                decrypted_config[key] = self.cipher.decrypt(value.encode()).decode()
            except Exception:
                # If decryption fails, it might be a non-encrypted value
                decrypted_config[key] = value
        return decrypted_config

    def get(self, key, default=None):
        """Gets a value from config, falling back to environment variables."""
        return self.config.get(key, os.getenv(key, default))

    def save_config(self, new_config, secrets_to_encrypt):
        """Encrypts secrets and saves the entire configuration."""
        full_config = self.config.copy()
        full_config.update(new_config)

        encrypted_config = {}
        for key, value in full_config.items():
            if key in secrets_to_encrypt and value:
                encrypted_config[key] = self.cipher.encrypt(value.encode()).decode()
            else:
                encrypted_config[key] = value
        
        with open(self.config_path, 'w') as f:
            json.dump(encrypted_config, f, indent=4)
        
        # Reload the in-memory config
        self.config = self._load_config()
        return True 