from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class AuthProvider(ABC):
    @abstractmethod
    def get_token(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        pass