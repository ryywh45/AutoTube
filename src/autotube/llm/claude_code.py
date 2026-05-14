import asyncio
import json
import logging
import shutil

from pydantic import BaseModel

from autotube.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class ClaudeCodeError(RuntimeError):
    """Raised when the claude CLI returns an error or unparseable output."""


class ClaudeCodeProvider(LLMProvider):
    """LLM provider backed by the locally installed `claude` CLI.

    Requires Claude Code to be installed and the user to be logged in (OAuth).
    Each call spawns a non-interactive subprocess (`claude -p --output-format json`).

    Trade-offs vs. a direct SDK provider:
      - Higher per-call latency (subprocess startup + CLI overhead, ~2-7s).
      - `temperature` / `max_tokens` cannot be set; only `effort` (low|medium|high|xhigh|max).
      - Project CLAUDE.md is auto-loaded unless the caller passes `cwd` to a directory without one.
      - Billing follows the user's Claude subscription, not a project API key.
    """

    DEFAULT_MODEL = "sonnet"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        *,
        claude_path: str | None = None,
        cwd: str | None = None,
        extra_args: list[str] | None = None,
        timeout: float | None = 300.0,
    ):
        resolved = claude_path or shutil.which("claude")
        if not resolved:
            raise ClaudeCodeError(
                "`claude` executable not found in PATH. Install Claude Code and ensure "
                "the `claude` command is available, or pass `claude_path=...`."
            )
        self._claude_path = resolved
        self._model = model
        self._cwd = cwd
        self._extra_args = list(extra_args or [])
        self._timeout = timeout

    def _base_args(self, system: str, effort: str | None) -> list[str]:
        args = [
            self._claude_path,
            "-p",
            "--output-format",
            "json",
            "--model",
            self._model,
            "--tools",
            "",
            "--no-session-persistence",
            "--disable-slash-commands",
        ]
        if system:
            args += ["--system-prompt", system]
        if effort:
            args += ["--effort", effort]
        args += self._extra_args
        return args

    async def _run(self, args: list[str], prompt: str) -> dict:
        logger.debug("Invoking claude CLI: %s", args)
        proc = await asyncio.create_subprocess_exec(
            *args,
            prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self._timeout)
        except asyncio.TimeoutError as e:
            proc.kill()
            await proc.wait()
            raise ClaudeCodeError(f"claude CLI timed out after {self._timeout}s") from e

        if proc.returncode != 0:
            raise ClaudeCodeError(
                f"claude CLI exited with code {proc.returncode}: {stderr.decode(errors='replace')}"
            )

        try:
            payload = json.loads(stdout.decode())
        except json.JSONDecodeError as e:
            raise ClaudeCodeError(
                f"Failed to parse claude CLI output as JSON: {e}\nstdout: {stdout!r}"
            ) from e

        if payload.get("is_error"):
            raise ClaudeCodeError(f"claude CLI reported error: {payload.get('result')}")

        return payload

    @staticmethod
    def _extract_usage(payload: dict) -> dict[str, int]:
        usage = payload.get("usage") or {}
        return {
            "input_tokens": int(usage.get("input_tokens", 0)),
            "output_tokens": int(usage.get("output_tokens", 0)),
            "cache_read_input_tokens": int(usage.get("cache_read_input_tokens", 0)),
            "cache_creation_input_tokens": int(usage.get("cache_creation_input_tokens", 0)),
        }

    async def generate(self, prompt: str, *, system: str = "", **kwargs) -> LLMResponse:
        args = self._base_args(system=system, effort=kwargs.get("effort"))
        payload = await self._run(args, prompt)
        return LLMResponse(
            content=payload.get("result", ""),
            model=self._model,
            usage=self._extract_usage(payload),
        )

    async def generate_structured(
        self, prompt: str, *, system: str = "", response_model: type[BaseModel], **kwargs
    ) -> BaseModel:
        schema = response_model.model_json_schema()
        args = self._base_args(system=system, effort=kwargs.get("effort"))
        args += ["--json-schema", json.dumps(schema)]
        payload = await self._run(args, prompt)

        structured = payload.get("structured_output")
        if structured is None:
            raise ClaudeCodeError(
                "claude CLI did not return `structured_output`; "
                f"raw result: {payload.get('result')!r}"
            )
        return response_model.model_validate(structured)
