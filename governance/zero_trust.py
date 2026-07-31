import hmac
import hashlib
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

_SECRET_KEY = None


def _get_secret_key() -> str:
    """Lazy-load HMAC secret key on first use (not at import time)."""
    global _SECRET_KEY
    if _SECRET_KEY is None:
        _SECRET_KEY = os.getenv("HMAC_SECRET_KEY")
        if not _SECRET_KEY:
            raise ValueError(
                "CRITICAL: HMAC_SECRET_KEY environment variable not set. "
                "Set a strong secret before running: "
                "export HMAC_SECRET_KEY='<your-random-secret-key>'"
            )
    return _SECRET_KEY


def sign_payload(payload: Dict[str, Any], secret: Optional[str] = None) -> str:
    if secret is None:
        secret = _get_secret_key()
    payload_json = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_json.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_payload(payload: Dict[str, Any], signature: str, secret: Optional[str] = None) -> bool:
    if secret is None:
        secret = _get_secret_key()
    expected_signature = sign_payload(payload, secret)
    return hmac.compare_digest(signature, expected_signature)

def create_signed_message(sender: str, receiver: str, message: Dict[str, Any], secret: Optional[str] = None) -> Dict[str, Any]:
    if secret is None:
        secret = _get_secret_key()
    signed_message = {
        "sender": sender,
        "receiver": receiver,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": message,
        "signature": sign_payload(message, secret)
    }
    return signed_message

def validate_signed_message(signed_message: Dict[str, Any], secret: Optional[str] = None) -> bool:
    if secret is None:
        secret = _get_secret_key()
    if "signature" not in signed_message or "payload" not in signed_message:
        return False
    
    return verify_payload(signed_message["payload"], signed_message["signature"], secret)

def validate_json_schema(data: Dict[str, Any], required_fields: list) -> bool:
    for field in required_fields:
        if field not in data:
            return False
    return True
