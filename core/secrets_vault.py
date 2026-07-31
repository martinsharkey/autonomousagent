"""Portable encrypted secrets vault for multi-daemon deployment.

The council needs API keys to function, but keys can't live in plaintext
in the repo. This module implements an encrypted vault that:

1. Stores ALL secrets in a single encrypted file (secrets.vault)
2. Requires only ONE master key to unlock everything
3. The master key is the ONLY thing that needs to be set per-platform:
   - HF Spaces: set as a Space secret
   - Replit: set as a Replit secret
   - GitHub Actions: set as a repo secret
   - Local: set in .env as COUNCIL_MASTER_KEY

Usage:
    # Store a secret (operator does this once)
    vault = get_vault()
    vault.set("HF_API_KEY", "hf_xxxxx")
    vault.set("TELEGRAM_BOT_TOKEN", "123456:ABC...")
    vault.save()  # Encrypts and writes to secrets.vault

    # Retrieve a secret (daemon does this at startup)
    vault = get_vault()
    hf_key = vault.get("HF_API_KEY")

    # The encrypted secrets.vault file is safe to commit to git.
    # Without COUNCIL_MASTER_KEY, it's just random bytes.
"""

import os
import json
import hashlib
import base64
import secrets as secrets_module
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

# Try to use cryptography library, fall back to simple XOR if not available
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


VAULT_FILE = Path("secrets.vault")
VAULT_METADATA_FILE = Path("secrets.vault.meta")
MASTER_KEY_ENV = "COUNCIL_MASTER_KEY"


def _derive_key(master_key: str, salt: bytes) -> bytes:
    """Derive a 256-bit encryption key from the master passphrase using PBKDF2."""
    return hashlib.pbkdf2_hmac(
        'sha256',
        master_key.encode('utf-8'),
        salt,
        iterations=100_000,
        dklen=32
    )


def _encrypt_aesgcm(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt using AES-256-GCM (requires cryptography library)."""
    aesgcm = AESGCM(key)
    nonce = secrets_module.token_bytes(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext  # prepend nonce


def _decrypt_aesgcm(data: bytes, key: bytes) -> bytes:
    """Decrypt AES-256-GCM."""
    aesgcm = AESGCM(key)
    nonce = data[:12]
    ciphertext = data[12:]
    return aesgcm.decrypt(nonce, ciphertext, None)


def _encrypt_xor(plaintext: bytes, key: bytes) -> bytes:
    """Fallback XOR encryption when cryptography lib is unavailable.
    
    NOT cryptographically strong for large data, but adequate for
    short secret strings when the real crypto lib isn't installed.
    Uses key-stream expansion via SHA-256 counter mode.
    """
    nonce = secrets_module.token_bytes(16)
    keystream = b""
    counter = 0
    while len(keystream) < len(plaintext):
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, 'big')).digest()
        keystream += block
        counter += 1
    
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, keystream[:len(plaintext)]))
    # HMAC for integrity
    mac = hashlib.sha256(key + nonce + ciphertext).digest()[:16]
    return nonce + mac + ciphertext


def _decrypt_xor(data: bytes, key: bytes) -> bytes:
    """Decrypt XOR fallback."""
    nonce = data[:16]
    mac = data[16:32]
    ciphertext = data[32:]
    
    # Verify integrity
    expected_mac = hashlib.sha256(key + nonce + ciphertext).digest()[:16]
    if mac != expected_mac:
        raise ValueError("Vault integrity check failed — wrong master key or corrupted vault")
    
    keystream = b""
    counter = 0
    while len(keystream) < len(ciphertext):
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, 'big')).digest()
        keystream += block
        counter += 1
    
    return bytes(a ^ b for a, b in zip(ciphertext, keystream[:len(ciphertext)]))


class SecretsVault:
    """Encrypted portable secrets vault.
    
    All API keys are stored encrypted with a single master passphrase.
    The encrypted vault file (secrets.vault) is safe to commit to git.
    Only the COUNCIL_MASTER_KEY env var is needed per-platform.
    """
    
    def __init__(self, master_key: Optional[str] = None, vault_path: Optional[Path] = None):
        self._master_key = master_key or os.getenv(MASTER_KEY_ENV)
        self._vault_path = vault_path or VAULT_FILE
        self._meta_path = vault_path.with_suffix('.vault.meta') if vault_path else VAULT_METADATA_FILE
        self._secrets: Dict[str, str] = {}
        self._salt: bytes = b""
        self._loaded = False
        self._crypto_backend = "aesgcm" if HAS_CRYPTO else "xor-sha256"
        
        if self._master_key:
            self._load()
    
    @property
    def is_unlocked(self) -> bool:
        """Whether the vault has been unlocked with a valid master key."""
        return self._loaded and bool(self._master_key)
    
    @property  
    def available_keys(self) -> List[str]:
        """List secret names (not values) stored in the vault."""
        return list(self._secrets.keys())
    
    def _load(self) -> None:
        """Load and decrypt the vault file."""
        if not self._vault_path.exists():
            # No vault yet — start fresh
            self._salt = secrets_module.token_bytes(32)
            self._secrets = {}
            self._loaded = True
            return
        
        try:
            raw = self._vault_path.read_bytes()
            # First 32 bytes are the salt
            self._salt = raw[:32]
            encrypted_data = raw[32:]
            
            key = _derive_key(self._master_key, self._salt)
            
            if HAS_CRYPTO:
                plaintext = _decrypt_aesgcm(encrypted_data, key)
            else:
                plaintext = _decrypt_xor(encrypted_data, key)
            
            self._secrets = json.loads(plaintext.decode('utf-8'))
            self._loaded = True
        except Exception as e:
            print(f"WARNING: Failed to decrypt vault: {e}")
            print("  Check that COUNCIL_MASTER_KEY is correct.")
            self._secrets = {}
            self._loaded = False
    
    def get(self, key_name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret value. Falls back to environment variable if vault doesn't have it."""
        # Check vault first
        value = self._secrets.get(key_name)
        if value:
            return value
        # Fall back to env var (for backward compatibility)
        env_value = os.getenv(key_name)
        if env_value:
            return env_value
        return default
    
    def set(self, key_name: str, value: str) -> None:
        """Set a secret in the vault (call .save() to persist)."""
        if not self._master_key:
            raise RuntimeError(
                f"Cannot set secrets without {MASTER_KEY_ENV}. "
                "Set it in your environment first."
            )
        if not self._loaded:
            self._salt = secrets_module.token_bytes(32)
            self._loaded = True
        self._secrets[key_name] = value
    
    def delete(self, key_name: str) -> bool:
        """Remove a secret from the vault."""
        if key_name in self._secrets:
            del self._secrets[key_name]
            return True
        return False
    
    def save(self) -> None:
        """Encrypt and persist the vault to disk."""
        if not self._master_key:
            raise RuntimeError(f"Cannot save vault without {MASTER_KEY_ENV}")
        
        if not self._salt:
            self._salt = secrets_module.token_bytes(32)
        
        plaintext = json.dumps(self._secrets, indent=2).encode('utf-8')
        key = _derive_key(self._master_key, self._salt)
        
        if HAS_CRYPTO:
            encrypted = _encrypt_aesgcm(plaintext, key)
        else:
            encrypted = _encrypt_xor(plaintext, key)
        
        # Write salt + encrypted data
        self._vault_path.write_bytes(self._salt + encrypted)
        
        # Write metadata (not secret, just tracking info)
        meta = {
            "last_updated": datetime.utcnow().isoformat(),
            "num_secrets": len(self._secrets),
            "secret_names": list(self._secrets.keys()),
            "crypto_backend": self._crypto_backend,
            "vault_version": 1,
        }
        self._meta_path.write_text(json.dumps(meta, indent=2))
    
    def export_to_env_dict(self) -> Dict[str, str]:
        """Export all secrets as a dict (for injecting into subprocess env)."""
        return dict(self._secrets)
    
    def inject_into_environment(self) -> int:
        """Inject all vault secrets into os.environ (for current process)."""
        count = 0
        for key, value in self._secrets.items():
            if not os.getenv(key):  # Don't override existing env vars
                os.environ[key] = value
                count += 1
        return count
    
    def get_status(self) -> Dict[str, any]:
        """Get vault status for health checks."""
        return {
            "unlocked": self.is_unlocked,
            "num_secrets": len(self._secrets),
            "secret_names": list(self._secrets.keys()),
            "vault_exists": self._vault_path.exists(),
            "crypto_backend": self._crypto_backend,
            "master_key_set": bool(self._master_key),
        }


# --- Singleton ---
_vault_instance: Optional[SecretsVault] = None


def get_vault() -> SecretsVault:
    """Get the global vault instance."""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = SecretsVault()
    return _vault_instance


def bootstrap_vault(master_key: str) -> SecretsVault:
    """Bootstrap a new vault with an explicit master key.
    
    Used by the operator to initially set up secrets:
        python -c "from core.secrets_vault import *; bootstrap_and_store()"
    """
    global _vault_instance
    _vault_instance = SecretsVault(master_key=master_key)
    return _vault_instance


# --- CLI helper for operator ---
def interactive_setup():
    """Interactive vault setup for the operator.
    
    Run: python -m core.secrets_vault
    """
    import getpass
    
    print("=" * 60)
    print("  COUNCIL SECRETS VAULT SETUP")
    print("=" * 60)
    print()
    print("This creates an encrypted vault that stores all API keys.")
    print("The vault file (secrets.vault) is safe to commit to git.")
    print("Only the master passphrase is needed per deployment platform.")
    print()
    
    master_key = os.getenv(MASTER_KEY_ENV)
    if not master_key:
        master_key = getpass.getpass(f"Enter master passphrase (or set {MASTER_KEY_ENV}): ")
        if not master_key:
            print("ERROR: Master passphrase cannot be empty")
            return
    
    vault = SecretsVault(master_key=master_key)
    
    print(f"\nVault unlocked. Currently has {len(vault.available_keys)} secrets.")
    if vault.available_keys:
        print(f"  Existing: {', '.join(vault.available_keys)}")
    
    print("\nEnter secrets (empty name to finish):")
    while True:
        name = input("  Secret name (e.g. HF_API_KEY): ").strip()
        if not name:
            break
        value = getpass.getpass(f"  Value for {name}: ")
        if value:
            vault.set(name, value)
            print(f"    ✓ {name} stored")
    
    vault.save()
    print(f"\n✓ Vault saved to {vault._vault_path}")
    print(f"  Contains {len(vault.available_keys)} secrets: {', '.join(vault.available_keys)}")
    print(f"\n  To use on other platforms, set:")
    print(f"    {MASTER_KEY_ENV}={master_key}")
    print(f"\n  Then the daemon will auto-decrypt all keys at startup.")


if __name__ == "__main__":
    interactive_setup()
