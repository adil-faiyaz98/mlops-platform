# security/jwt/jwt_utils.py

import jwt
import time
from datetime import datetime, timedelta
from security.jwt.jwt_config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_SECONDS


def generate_jwt_token(payload):
    """
    Generates a JWT token.

    Args:
        payload (dict): The payload to include in the JWT.

    Returns:
        str: The JWT token.
    """
    try:
        payload['exp'] = datetime.utcnow() + timedelta(seconds=JWT_EXPIRY_SECONDS) # Set expiration time
        encoded_jwt = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    except Exception as e:
        print(f"Error generating JWT: {e}")
        return None

def verify_jwt_token(token):
    """
    Verifies a JWT token.

    Args:
        token (str): The JWT token to verify.

    Returns:
        dict: The decoded payload if the token is valid, None otherwise.
    """
    try:
        decoded_payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_payload
    except jwt.ExpiredSignatureError:
        print("JWT token has expired.")
        return None
    except jwt.InvalidTokenError:
        print("Invalid JWT token.")
        return None
    except Exception as e:
        print(f"Error verifying JWT: {e}")
        return None


if __name__ == '__main__':
    # Example Usage
    payload = {"user_id": 123, "username": "testuser"}
    token = generate_jwt_token(payload)

    if token:
        print(f"Generated JWT: {token}")
        decoded_payload = verify_jwt_token(token)
        if decoded_payload:
            print(f"Decoded Payload: {decoded_payload}")
        else:
            print("Token verification failed.")