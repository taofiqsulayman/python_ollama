from core.auth.base import AuthProvider
from config.settings import settings
import jwt
import requests

class KeycloakAuth(AuthProvider):
    def __init__(self):
        self.realm_url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
    
    def get_token(self, username: str, password: str):
        token_url = f"{self.realm_url}/protocol/openid-connect/token"
        data = {
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
            "grant_type": "password",
            "username": username,
            "password": password
        }
        response = requests.post(token_url, data=data)
        return response.json() if response.status_code == 200 else None
    
    def verify_token(self, token: str):
        try:
            public_key_url = f"{self.realm_url}/protocol/openid-connect/certs"
            key_response = requests.get(public_key_url)
            public_key = key_response.json()['keys'][0]
            return jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=settings.KEYCLOAK_CLIENT_ID
            )
        except Exception:
            return None