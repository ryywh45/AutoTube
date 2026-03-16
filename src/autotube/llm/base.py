from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""

    content: str
    model: str
    usage: dict[str, int] = {}


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All providers (OpenAI, Anthropic, Gemini, etc.) must implement this interface.
    """

    @abstractmethod
    async def generate(self, prompt: str, *, system: str = "", **kwargs) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt.
            system: Optional system prompt.
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.).

        Returns:
            Standardized LLMResponse.
        """

    @abstractmethod
    async def generate_structured(
        self, prompt: str, *, system: str = "", response_model: type[BaseModel], **kwargs
    ) -> BaseModel:
        """Generate a structured response that conforms to a Pydantic model.

        Args:
            prompt: The user prompt.
            system: Optional system prompt.
            response_model: The Pydantic model class to parse the response into.
            **kwargs: Provider-specific parameters.

        Returns:
            An instance of response_model.
        """
