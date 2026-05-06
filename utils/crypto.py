import json
import base64
import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from dotenv import load_dotenv

load_dotenv()

ENC_KEY = os.getenv("ENC_KEY")

if not ENC_KEY:
    raise ValueError("ENC_KEY missing")

# Must be exactly 32 chars for AES-256
KEY = ENC_KEY.encode("utf-8")


def encrypt_data(data):

    cipher = AES.new(
        KEY,
        AES.MODE_ECB
    )

    encrypted = cipher.encrypt(
        pad(
            json.dumps(data).encode(),
            AES.block_size
        )
    )

    return base64.b64encode(
        encrypted
    ).decode()


def decrypt_data(payload):

    cipher = AES.new(
        KEY,
        AES.MODE_ECB
    )

    decrypted = unpad(
        cipher.decrypt(
            base64.b64decode(payload)
        ),
        AES.block_size
    )

    return json.loads(
        decrypted.decode()
    )