import pytest

from autotube.llm import StubLLMProvider


class TestStubLLMProvider:
    @pytest.mark.asyncio
    async def test_generate(self):
        provider = StubLLMProvider(default_response="hello")
        response = await provider.generate("test prompt")
        assert response.content == "hello"
        assert response.model == "stub"

    @pytest.mark.asyncio
    async def test_generate_custom_response(self):
        provider = StubLLMProvider(default_response="custom")
        response = await provider.generate("anything")
        assert response.content == "custom"
