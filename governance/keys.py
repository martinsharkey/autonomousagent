import os
import secrets
import hashlib
from typing import Optional
from datetime import datetime
from pathlib import Path

KEYS_DIR = Path(".keys")
AUDIT_LOG_KEY_ENV = "AUDIT_LOG_HMAC_KEY"
SNAPSHOT_KEY_ENV = "SNAPSHOT_HMAC_KEY"
ZERO_TRUST_KEY_ENV = "ZERO_TRUST_HMAC_KEY"

class KeyManager:
    def __init__(self):
        self._keys = {}
        self._load_keys()
    
    def _load_keys(self):
        self._keys[AUDIT_LOG_KEY_ENV] = self._get_or_create_key(AUDIT_LOG_KEY_ENV)
        self._keys[SNAPSHOT_KEY_ENV] = self._get_or_create_key(SNAPSHOT_KEY_ENV)
        self._keys[ZERO_TRUST_KEY_ENV] = self._get_or_create_key(ZERO_TRUST_KEY_ENV)
    
    def _get_or_create_key(self, key_name: str) -> str:
        env_value = os.getenv(key_name)
        if env_value:
            return env_value
        
        key_file = KEYS_DIR / f"{key_name}.key"
        if key_file.exists():
            return key_file.read_text().strip()
        
        new_key = self._generate_key()
        self._save_key(key_name, new_key)
        return new_key
    
    def _generate_key(self) -> str:
        return secrets.token_hex(32)
    
    def _save_key(self, key_name: str, key_value: str):
        KEYS_DIR.mkdir(exist_ok=True)
        key_file = KEYS_DIR / f"{key_name}.key"
        key_file.write_text(key_value)
        
        if os.name != 'nt':
            key_file.chmod(0o600)
    
    def get_key(self, key_name: str) -> str:
        if key_name not in self._keys:
            self._keys[key_name] = self._get_or_create_key(key_name)
        return self._keys[key_name]
    
    def rotate_key(self, key_name: str) -> str:
        old_key = self._keys.get(key_name)
        
        new_key = self._generate_key()
        self._keys[key_name] = new_key
        
        os.environ[key_name] = new_key
        self._save_key(key_name, new_key)
        
        rotation_log = KEYS_DIR / "rotation.log"
        with open(rotation_log, 'a') as f:
            timestamp = datetime.utcnow().isoformat()
            f.write(f"{timestamp}: Rotated {key_name}\n")
        
        return new_key
    
    def verify_key_exists(self, key_name: str) -> bool:
        return key_name in self._keys or os.getenv(key_name) is not None

_key_manager = KeyManager()

def get_hmac_key(key_type: str) -> str:
    return _key_manager.get_key(key_type)

def rotate_hmac_key(key_type: str) -> str:
    return _key_manager.rotate_key(key_type)

def get_audit_log_key() -> str:
    return get_hmac_key(AUDIT_LOG_KEY_ENV)

def get_snapshot_key() -> str:
    return get_hmac_key(SNAPSHOT_KEY_ENV)

def get_zero_trust_key() -> str:
    return get_hmac_key(ZERO_TRUST_KEY_ENV)
