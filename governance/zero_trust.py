import hmac
import hashlib
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

SECRET_KEY = os.getenv("HMAC_SECRET_KEY", "council_default_secret_key_change_in_production")

def sign_payload(payload: Dict[str, Any], secret: str = SECRET_KEY) -> str:
    payload_json = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_json.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_payload(payload: Dict[str, Any], signature: str, secret: str = SECRET_KEY) -> bool:
    expected_signature = sign_payload(payload, secret)
    return hmac.compare_digest(signature, expected_signature)

def create_signed_message(sender: str, receiver: str, message: Dict[str, Any], secret: str = SECRET_KEY) -> Dict[str, Any]:
    signed_message = {
        "sender": sender,
        "receiver": receiver,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": message,
        "signature": sign_payload(message, secret)
    }
    return signed_message

def validate_signed_message(signed_message: Dict[str, Any], secret: str = SECRET_KEY) -> bool:
    if "signature" not in signed_message or "payload" not in signed_message:
        return False
    
    return verify_payload(signed_message["payload"], signed_message["signature"], secret)

def validate_json_schema(data: Dict[str, Any], required_fields: list) -> bool:
    for field in required_fields:
        if field not in data:
            return False
    return True
