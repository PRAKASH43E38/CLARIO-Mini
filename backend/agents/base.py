from abc import ABC, abstractmethod
from typing import Any
from backend.providers.service import ProviderService, provider_service
from backend.schemas.contracts import AgentTask, AgentResult


class BaseAgent(ABC):
    """
    Base class for all specialized CLARIO agents.
    
    Architectural Rules:
    1. CLARIO-AI is the only orchestrator.
    2. Agents must never orchestrate each other.
    3. Agents must call the provider abstraction rather than a direct LLM vendor.
    """

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        providers: ProviderService | None = None,
    ) -> None:
        self.name = name
        self.role = role
        self.description = description
        self.providers = providers or provider_service

    @abstractmethod
    async def process_task(self, task: AgentTask) -> AgentResult:
        """Process an assigned task and return a standardized AgentResult."""
        pass
