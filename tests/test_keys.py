import pytest
import os
import tempfile
import shutil
from pathlib import Path
from governance.keys import (
    KeyManager,
    get_hmac_key,
    rotate_hmac_key,
    get_audit_log_key,
    get_snapshot_key,
    get_zero_trust_key,
    AUDIT_LOG_KEY_ENV,
    SNAPSHOT_KEY_ENV,
    ZERO_TRUST_KEY_ENV,
    KEYS_DIR
)


class TestKeyManager:
    def setup_method(self):
        for key in [AUDIT_LOG_KEY_ENV, SNAPSHOT_KEY_ENV, ZERO_TRUST_KEY_ENV]:
            if key in os.environ:
                del os.environ[key]
        
        if KEYS_DIR.exists():
            shutil.rmtree(KEYS_DIR)

    def teardown_method(self):
        for key in [AUDIT_LOG_KEY_ENV, SNAPSHOT_KEY_ENV, ZERO_TRUST_KEY_ENV]:
            if key in os.environ:
                del os.environ[key]
        
        if KEYS_DIR.exists():
            shutil.rmtree(KEYS_DIR)

    def test_key_manager_creates_keys(self):
        manager = KeyManager()
        
        audit_key = manager.get_key(AUDIT_LOG_KEY_ENV)
        assert audit_key is not None
        assert len(audit_key) == 64

    def test_key_manager_persists_keys(self):
        manager1 = KeyManager()
        key1 = manager1.get_key(AUDIT_LOG_KEY_ENV)
        
        manager2 = KeyManager()
        key2 = manager2.get_key(AUDIT_LOG_KEY_ENV)
        
        assert key1 == key2

    def test_key_manager_uses_env_vars(self):
        test_key = "test_key_from_env_1234567890abcdef"
        os.environ[AUDIT_LOG_KEY_ENV] = test_key
        
        manager = KeyManager()
        retrieved_key = manager.get_key(AUDIT_LOG_KEY_ENV)
        
        assert retrieved_key == test_key

    def test_rotate_key(self):
        manager = KeyManager()
        old_key = manager.get_key(AUDIT_LOG_KEY_ENV)
        
        new_key = manager.rotate_key(AUDIT_LOG_KEY_ENV)
        
        assert new_key != old_key
        assert len(new_key) == 64
        assert manager.get_key(AUDIT_LOG_KEY_ENV) == new_key

    def test_rotate_key_updates_env(self):
        manager = KeyManager()
        new_key = manager.rotate_key(AUDIT_LOG_KEY_ENV)
        
        assert os.environ[AUDIT_LOG_KEY_ENV] == new_key

    def test_rotate_key_logs_rotation(self):
        manager = KeyManager()
        manager.rotate_key(AUDIT_LOG_KEY_ENV)
        
        rotation_log = KEYS_DIR / "rotation.log"
        assert rotation_log.exists()
        
        log_content = rotation_log.read_text()
        assert AUDIT_LOG_KEY_ENV in log_content
        assert "Rotated" in log_content

    def test_verify_key_exists(self):
        manager = KeyManager()
        
        assert manager.verify_key_exists(AUDIT_LOG_KEY_ENV) is True
        assert manager.verify_key_exists("NONEXISTENT_KEY") is False

    def test_different_keys_for_different_purposes(self):
        manager = KeyManager()
        
        audit_key = manager.get_key(AUDIT_LOG_KEY_ENV)
        snapshot_key = manager.get_key(SNAPSHOT_KEY_ENV)
        zero_trust_key = manager.get_key(ZERO_TRUST_KEY_ENV)
        
        assert audit_key != snapshot_key
        assert snapshot_key != zero_trust_key
        assert audit_key != zero_trust_key

    def test_key_file_permissions(self):
        manager = KeyManager()
        manager.get_key(AUDIT_LOG_KEY_ENV)
        
        key_file = KEYS_DIR / f"{AUDIT_LOG_KEY_ENV}.key"
        assert key_file.exists()
        
        if os.name != 'nt':
            mode = key_file.stat().st_mode
            assert mode & 0o777 == 0o600


class TestKeyHelperFunctions:
    def setup_method(self):
        for key in [AUDIT_LOG_KEY_ENV, SNAPSHOT_KEY_ENV, ZERO_TRUST_KEY_ENV]:
            if key in os.environ:
                del os.environ[key]
        
        if KEYS_DIR.exists():
            shutil.rmtree(KEYS_DIR)

    def teardown_method(self):
        for key in [AUDIT_LOG_KEY_ENV, SNAPSHOT_KEY_ENV, ZERO_TRUST_KEY_ENV]:
            if key in os.environ:
                del os.environ[key]
        
        if KEYS_DIR.exists():
            shutil.rmtree(KEYS_DIR)

    def test_get_audit_log_key(self):
        key = get_audit_log_key()
        assert key is not None
        assert len(key) == 64

    def test_get_snapshot_key(self):
        key = get_snapshot_key()
        assert key is not None
        assert len(key) == 64

    def test_get_zero_trust_key(self):
        key = get_zero_trust_key()
        assert key is not None
        assert len(key) == 64

    def test_rotate_hmac_key(self):
        old_key = get_audit_log_key()
        new_key = rotate_hmac_key(AUDIT_LOG_KEY_ENV)
        
        assert new_key != old_key
        assert get_audit_log_key() == new_key
