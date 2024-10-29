from typing import Optional, Dict, Any
from core.auth.base import AuthProvider

class DevAuth(AuthProvider):
    def __init__(self):
        self.users = {
            "admin": {
                "password": "admin123",
                "role": "advanced",
                "sub": "1",
                "preferred_username": "admin"
            },
            "user": {
                "password": "user123",
                "role": "basic",
                "sub": "2",
                "preferred_username": "user"
            }
        }
    
    def get_token(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        if username in self.users and self.users[username]["password"] == password:
            return {"access_token": f"dev_token_{username}"}
        return None
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        username = token.replace("dev_token_", "")
        if username in self.users:
            return {
                "sub": self.users[username]["sub"],
                "preferred_username": username,
                "role": self.users[username]["role"]
            }
        return None