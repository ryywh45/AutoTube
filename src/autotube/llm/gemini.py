import json
import logging

from google import genai
from google.genai import types
from pydantic import BaseModel

from autotube.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, api_key: str, model: str = "gemini-3.1-flash-lite-preview"):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def generate(self, prompt: str, *, system: str = "", **kwargs) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=kwargs.get("temperature"),
            max_output_tokens=kwargs.get("max_tokens"),
        )
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        usage: dict[str, int] = {}
        if response.usage_metadata:
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count or 0,
                "output_tokens": response.usage_metadata.candidates_token_count or 0,
            }
        return LLMResponse(
            content=response.text or "",
            model=self._model,
            usage=usage,
        )

    async def generate_structured(
        self, prompt: str, *, system: str = "", response_model: type[BaseModel], **kwargs
    ) -> BaseModel:
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=kwargs.get("temperature"),
            max_output_tokens=kwargs.get("max_tokens"),
            response_mime_type="application/json",
            response_schema=response_model,
        )
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        data = json.loads(response.text or "{}")
        return response_model.model_validate(data)
