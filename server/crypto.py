# server/crypto.py
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import constant_time
from cryptography.hazmat.backends import default_backend
import os, json, base64

def sha256_bytes(data: bytes) -> str:
    h = hashes.Hash(hashes.SHA256(), backend=default_backend())
    h.update(data)
    return h.finalize().hex()

def generate_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key

def rsa_sign_pss(private_key, message_bytes: bytes) -> bytes:
    return private_key.sign(
        message_bytes,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )

def rsa_verify_pss(public_key, message_bytes: bytes, signature: bytes) -> bool:
    try:
        public_key.verify(
            signature,
            message_bytes,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False

def aes256gcm_encrypt(key: bytes, iv: bytes, plaintext: bytes, aad: bytes) -> tuple[bytes, bytes]:
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(iv, plaintext, aad)   # returns ciphertext||tag
    # AESGCM in cryptography appends 16-byte tag at the end
    return ct[:-16], ct[-16:]

def aes256gcm_decrypt(key: bytes, iv: bytes, ciphertext: bytes, tag: bytes, aad: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ciphertext + tag, aad)

def canonicalize_header(header: dict) -> bytes:
    # stable ordering & whitespace
    return json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")

def b64e(b: bytes) -> str: return base64.b64encode(b).decode("utf-8")
def b64d(s: str) -> bytes: return base64.b64decode(s.encode("utf-8"))

# ======== At-rest key wrapping ========
# AES content keys must not be stored next to the ciphertext in cleartext.
# We wrap them with a master key (env MASTER_KEY) using AES-256-GCM.
# Stored format (base64): b"v1:" || iv(12) || ciphertext||tag
_WRAP_PREFIX = b"v1:"
_WRAP_AAD = b"docutrack-key-wrap"

def _master_key() -> bytes:
    mk = os.getenv("MASTER_KEY")
    if mk:
        try:
            raw = base64.b64decode(mk, validate=True)
        except Exception:
            raw = mk.encode("utf-8")
    else:
        # Dev fallback: usable but insecure. Set MASTER_KEY in production.
        raw = b"docutrack-dev-master-key-change-me"
    h = hashes.Hash(hashes.SHA256(), backend=default_backend())
    h.update(raw)
    return h.finalize()  # 32 bytes

def wrap_key(key: bytes) -> str:
    iv = os.urandom(12)
    aesgcm = AESGCM(_master_key())
    blob = _WRAP_PREFIX + iv + aesgcm.encrypt(iv, key, _WRAP_AAD)
    return base64.b64encode(blob).decode("utf-8")

def unwrap_key(stored: str) -> bytes:
    raw = base64.b64decode(stored.encode("utf-8"))
    if raw.startswith(_WRAP_PREFIX):
        body = raw[len(_WRAP_PREFIX):]
        iv, ct = body[:12], body[12:]
        return AESGCM(_master_key()).decrypt(iv, ct, _WRAP_AAD)
    # Legacy rows stored the raw AES key as plain base64.
    return raw
