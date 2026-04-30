import uuid
from jose import jwt

SECRET = "supersecretkey"
ALGO = "HS256"


def create_token(username):
    payload = {
        "user_id": str(uuid.uuid4()),
        "username": username
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def decode_token(token):
    return jwt.decode(token, SECRET, algorithms=[ALGO])
