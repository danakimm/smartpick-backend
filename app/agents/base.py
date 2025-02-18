from typing import Dict, Any
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트의 주요 실행 로직"""
        pass 