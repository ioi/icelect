# Icelect - Cryptographic functions
# (c) 2025 Martin Mareš <mj@ucw.cz>

import base64
import hashlib
import secrets


def gen_credential() -> str:
    rand = secrets.token_bytes(5)
    cred = base64.b32encode(rand).decode('us-ascii')
    cred = cred.replace('O', '8').replace('I', '9')
    return cred


def cred_to_h1(cred: str) -> str:
    h1bin = hashlib.sha256(cred.encode('us-ascii')).digest()
    h1 = base64.b64encode(h1bin[:18]).decode('us-ascii')
    return h1


def h1_to_h2(h1: str) -> str:
    h2bin = hashlib.sha256(h1.encode('us-ascii')).digest()
    h2 = base64.b64encode(h2bin[:18]).decode('us-ascii')
    return h2
