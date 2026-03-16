from pydantic import BaseModel

from autotube.llm.base import LLMProvider, LLMResponse


class StubLLMProvider(LLMProvider):
    """A stub LLM provider for testing and development.

    Returns a fixed response or a caller-supplied response.
    """

    def __init__(self, default_response: str = "This is a stub response."):
        self._default_response = default_response

    async def generate(self, prompt: str, *, system: str = "", **kwargs) -> LLMResponse:
        return LLMResponse(
            content=self._default_response,
            model="stub",
            usage={"input_tokens": len(prompt), "output_tokens": len(self._default_response)},
        )

    async def generate_structured(
        self, prompt: str, *, system: str = "", response_model: type[BaseModel], **kwargs
    ) -> BaseModel:
        """Attempt to create a response_model instance with default values."""
        return response_model.model_validate({})
