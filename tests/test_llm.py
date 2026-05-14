import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from autotube.llm import ClaudeCodeError, ClaudeCodeProvider, StubLLMProvider


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


class _Greeting(BaseModel):
    greeting: str
    language: str


def _fake_proc(stdout_payload: dict, returncode: int = 0, stderr: bytes = b""):
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(json.dumps(stdout_payload).encode(), stderr))
    proc.returncode = returncode
    proc.kill = AsyncMock()
    proc.wait = AsyncMock()
    return proc


class TestClaudeCodeProvider:
    def test_missing_executable_raises(self):
        with patch("autotube.llm.claude_code.shutil.which", return_value=None):
            with pytest.raises(ClaudeCodeError, match="not found"):
                ClaudeCodeProvider()

    @pytest.mark.asyncio
    async def test_generate_parses_result(self):
        payload = {
            "is_error": False,
            "result": "hi there",
            "usage": {"input_tokens": 5, "output_tokens": 2},
        }
        with patch("autotube.llm.claude_code.shutil.which", return_value="/usr/bin/claude"):
            provider = ClaudeCodeProvider(model="sonnet")
        with patch(
            "autotube.llm.claude_code.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_fake_proc(payload)),
        ) as spawn:
            response = await provider.generate("hello", system="you are helpful")

        assert response.content == "hi there"
        assert response.model == "sonnet"
        assert response.usage["input_tokens"] == 5
        assert response.usage["output_tokens"] == 2

        args = spawn.call_args.args
        assert "-p" in args
        assert "--output-format" in args and "json" in args
        assert "--system-prompt" in args
        assert args[args.index("--system-prompt") + 1] == "you are helpful"
        assert args[-1] == "hello"

    @pytest.mark.asyncio
    async def test_generate_propagates_cli_error(self):
        payload = {"is_error": True, "result": "Not logged in"}
        with patch("autotube.llm.claude_code.shutil.which", return_value="/usr/bin/claude"):
            provider = ClaudeCodeProvider()
        with patch(
            "autotube.llm.claude_code.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_fake_proc(payload)),
        ):
            with pytest.raises(ClaudeCodeError, match="Not logged in"):
                await provider.generate("x")

    @pytest.mark.asyncio
    async def test_generate_propagates_nonzero_exit(self):
        proc = AsyncMock()
        proc.communicate = AsyncMock(return_value=(b"", b"boom"))
        proc.returncode = 2
        with patch("autotube.llm.claude_code.shutil.which", return_value="/usr/bin/claude"):
            provider = ClaudeCodeProvider()
        with patch(
            "autotube.llm.claude_code.asyncio.create_subprocess_exec",
            AsyncMock(return_value=proc),
        ):
            with pytest.raises(ClaudeCodeError, match="exited with code 2"):
                await provider.generate("x")

    @pytest.mark.asyncio
    async def test_generate_structured_uses_json_schema(self):
        payload = {
            "is_error": False,
            "result": "こんにちは",
            "structured_output": {"greeting": "こんにちは", "language": "Japanese"},
            "usage": {},
        }
        with patch("autotube.llm.claude_code.shutil.which", return_value="/usr/bin/claude"):
            provider = ClaudeCodeProvider()
        with patch(
            "autotube.llm.claude_code.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_fake_proc(payload)),
        ) as spawn:
            result = await provider.generate_structured(
                "Greet me in Japanese", response_model=_Greeting
            )

        assert isinstance(result, _Greeting)
        assert result.greeting == "こんにちは"
        assert result.language == "Japanese"

        args = spawn.call_args.args
        assert "--json-schema" in args
        schema_str = args[args.index("--json-schema") + 1]
        schema = json.loads(schema_str)
        assert "greeting" in schema["properties"]

    @pytest.mark.asyncio
    async def test_generate_structured_missing_output_raises(self):
        payload = {"is_error": False, "result": "no schema match", "usage": {}}
        with patch("autotube.llm.claude_code.shutil.which", return_value="/usr/bin/claude"):
            provider = ClaudeCodeProvider()
        with patch(
            "autotube.llm.claude_code.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_fake_proc(payload)),
        ):
            with pytest.raises(ClaudeCodeError, match="structured_output"):
                await provider.generate_structured("x", response_model=_Greeting)
