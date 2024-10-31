# auth.py
import os
from functools import wraps
import jwt
import requests
from urllib.parse import urljoin
import streamlit as st
from models import User
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from jwt import PyJWKClient

class KeycloakAuth:
    def __init__(self):
        self.keycloak_url = os.getenv('KEYCLOAK_URL')
        self.realm = os.getenv('KEYCLOAK_REALM')
        self.client_id = os.getenv('KEYCLOAK_CLIENT_ID')
        self.client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET')
        self.realm_url = f"{self.keycloak_url}/realms/{self.realm}"
        
    def get_token(self, username: str, password: str):
        token_url = f"{self.realm_url}/protocol/openid-connect/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "password",
            "username": username,
            "password": password
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            return response.json()
        return None

    def verify_token(self, token: str):
        try:
            public_key_url = f"{self.realm_url}/protocol/openid-connect/certs"
            key_response = requests.get(public_key_url)
        
            jwk_client = PyJWKClient(public_key_url)

            token_payload = jwt.decode(token, options={"verify_signature": False})
            
 
            signing_key = jwk_client.get_signing_key_from_jwt(token).key

            decoded_token = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                audience=self.client_id
            )
            return decoded_token
        except Exception as e:
            print(f"Token verification failed: {e}")
            return None

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'token' not in st.session_state:
            st.warning("Please log in to access this feature.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

def role_required(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'user_role' not in st.session_state or st.session_state['user_role'] != required_role:
                st.warning(f"You need {required_role} access to use this feature.")
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator