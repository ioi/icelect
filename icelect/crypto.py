# Icelect - Cryptographic functions
# (c) 2025 Martin Mareš <mj@ucw.cz>

import base64
import hashlib
import hmac
import secrets


def gen_credential() -> str:
    rand = secrets.token_bytes(5)
    cred = base64.b32encode(rand).decode('us-ascii')
    cred = cred.replace('O', '8').replace('I', '9')
    return cred


def cred_to_h1(cred: str) -> str:
    h1bin = hashlib.sha256(('H1:' + cred).encode('us-ascii')).digest()
    h1 = base64.b64encode(h1bin[:18]).decode('us-ascii')
    return h1


def cred_to_h2(cred: str) -> str:
    h2bin = hashlib.sha256(('H2:' + cred).encode('us-ascii')).digest()
    h2 = base64.b64encode(h2bin[:18]).decode('us-ascii')
    return h2


def gen_key() -> str:
    return base64.b64encode(secrets.token_bytes(24)).decode('us-ascii')


def h1_to_receipt(h1: str, key: str) -> str:
    return _sign(h1, key)[:8]


def h1_to_verifier(h1: str, key: str) -> str:
    return _sign(h1, key)


def _sign(msg: str, key: str) -> str:
    hkey = hashlib.sha256(key.encode('us-ascii')).digest()   # We need key size == hash function block size.
    digest = hmac.digest(hkey, msg.encode('us-ascii'), 'sha256')
    return base64.b64encode(digest[:18]).decode('us-ascii')
