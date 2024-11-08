# auth.py
import os
from functools import wraps
import jwt
import requests
from urllib.parse import urljoin, urlencode
import streamlit as st
from models import User
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from jwt import PyJWKClient
import time

class KeycloakAuth:
    def __init__(self):
        self.keycloak_url = os.getenv('KEYCLOAK_URL')
        self.realm = os.getenv('KEYCLOAK_REALM')
        self.client_id = os.getenv('KEYCLOAK_CLIENT_ID')
        self.client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET')
        self.redirect_uri = os.getenv('REDIRECT_URI') 
        self.realm_url = f"{self.keycloak_url}/realms/{self.realm}"
        
    def get_authorization_url(self):
        """Construct the authorization URL for Keycloak."""
        auth_url = f"{self.realm_url}/protocol/openid-connect/auth"
        params = f"client_id={self.client_id}&response_type=code&scope=openid+profile+email&redirect_uri={self.redirect_uri}"
    
        return f"{auth_url}?{params}"

    
    def exchange_code_for_tokens(self, code: str):
        """Exchange authorization code for access and refresh tokens."""
        token_url = f"{self.realm_url}/protocol/openid-connect/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get token: {response.content}")

    def refresh_token(self, refresh_token: str):
        """Refresh the access token using a refresh token."""
        token_url = f"{self.realm_url}/protocol/openid-connect/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception("Failed to refresh token")

    def get_keycloak_token(self, auth_code):
        """Exchange authorization code for access and refresh tokens."""
        try:
            tokens = self.exchange_code_for_tokens(auth_code)
            return tokens.get("access_token"), tokens.get("refresh_token")
        except Exception as e:
            raise Exception(f"Token exchange failed: {str(e)}")

    def get_user_info(self, access_token):
        """Fetch user info using the access token."""
        user_info_url = f"{self.realm_url}/protocol/openid-connect/userinfo"
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(user_info_url, headers=headers)
        
        if response.status_code == 200:
            return response.json()  
        else:
            raise Exception(f"Failed to fetch user info: {response.content}")

    def is_token_expired(self, token):
        try:
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            expiration_time = decoded_token.get("exp")
            return expiration_time < time.time()
        except jwt.DecodeError:
            return True 

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'token' not in st.session_state:
            st.warning("Please log in to access this feature.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper
print(st, "Login required")
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


    # webbrowser.open(auth_url) 
