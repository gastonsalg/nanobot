"""Codex CLI-backed provider implementation."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

from nanobot.providers.base import LLMProvider, LLMResponse


class CodexCLIProvider(LLMProvider):
    """Provider that delegates generation to the local authenticated `codex` CLI."""

    def __init__(
        self,
        default_model: str = "openai/gpt-5.3-codex",
        codex_command: str = "codex",
        working_dir: str | None = None,
        sandbox_mode: str = "read-only",
        timeout: int = 180,
    ):
        super().__init__(api_key=None, api_base=None)
        self.default_model = default_model
        self.codex_command = codex_command
        self.working_dir = str(Path(working_dir or Path.cwd()).resolve())
        self.sandbox_mode = sandbox_mode
        self.timeout = timeout

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        del max_tokens, temperature
        prompt = self._build_prompt(messages, tools=tools)
        model_name = self._resolve_model_name(model or self.default_model)

        output_path = self._new_output_path()
        args = [
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            self.sandbox_mode,
            "--color",
            "never",
            "--output-last-message",
            output_path,
        ]
        if model_name:
            args.extend(["--model", model_name])
        args.append("-")

        stdout_text = ""
        stderr_text = ""
        return_code = 1

        try:
            process = await asyncio.create_subprocess_exec(
                self.codex_command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
            )
        except Exception as e:
            self._cleanup_output_path(output_path)
            return LLMResponse(
                content=f"Error calling Codex CLI: {e}",
                finish_reason="error",
            )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode("utf-8")),
                timeout=self.timeout,
            )
            return_code = process.returncode or 0
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            process.kill()
            self._cleanup_output_path(output_path)
            return LLMResponse(
                content=f"Error calling Codex CLI: command timed out after {self.timeout} seconds",
                finish_reason="error",
            )

        message = self._read_last_message(output_path) or self._extract_message_from_jsonl(stdout_text)
        self._cleanup_output_path(output_path)

        if return_code != 0:
            detail = stderr_text.strip() or stdout_text.strip() or f"exit code {return_code}"
            return LLMResponse(
                content=f"Error calling Codex CLI: {detail}",
                finish_reason="error",
            )

        if not message:
            return LLMResponse(
                content="Error calling Codex CLI: no assistant message returned",
                finish_reason="error",
            )

        return LLMResponse(content=message.strip(), finish_reason="stop")

    def get_default_model(self) -> str:
        return self.default_model

    def _resolve_model_name(self, model: str) -> str:
        normalized = (model or "").strip()
        if normalized.lower().startswith("openai/"):
            return normalized.split("/", 1)[1]
        return normalized

    def _build_prompt(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        rendered_messages: list[str] = []
        for message in messages:
            role = str(message.get("role", "user")).upper()
            content = self._render_content(message.get("content"))
            rendered_messages.append(f"{role}:\n{content}")

        prompt_parts = [
            "You are the model backend for goodbot.",
            "Respond with the assistant's next message only.",
            "Do not run shell commands, do not edit files, and do not describe tool execution.",
            "Tool-calling is disabled in this backend mode.",
        ]

        if tools:
            prompt_parts.append(
                "Available tool definitions are provided for context only; do not emit tool calls."
            )

        prompt_parts.extend(
            [
                "",
                "Conversation transcript:",
                "\n\n".join(rendered_messages),
                "",
                "ASSISTANT:",
            ]
        )
        return "\n".join(prompt_parts)

    def _render_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)

    def _extract_message_from_jsonl(self, output: str) -> str:
        if not output:
            return ""

        message = ""
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = str(event.get("type", "")).lower()
            if event_type == "item.completed":
                item = event.get("item")
                if isinstance(item, dict) and str(item.get("type", "")).lower() in {
                    "agent_message",
                    "assistant_message",
                }:
                    text = self._extract_text(item)
                    if text:
                        message = text
            elif event_type in {"assistant_message", "agent_message", "response.completed"}:
                text = self._extract_text(event)
                if text:
                    message = text

        return message

    def _extract_text(self, payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        if isinstance(payload, list):
            parts = [self._extract_text(item) for item in payload]
            return "\n".join([part for part in parts if part]).strip()
        if isinstance(payload, dict):
            direct_text = payload.get("text")
            if isinstance(direct_text, str):
                return direct_text
            for key in ("content", "message", "output"):
                if key in payload:
                    candidate = self._extract_text(payload[key])
                    if candidate:
                        return candidate
        return ""

    def _new_output_path(self) -> str:
        handle = tempfile.NamedTemporaryFile(prefix="nanobot-codex-", suffix=".txt", delete=False)
        path = handle.name
        handle.close()
        return path

    def _read_last_message(self, path: str) -> str:
        file_path = Path(path)
        if not file_path.exists():
            return ""
        try:
            return file_path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def _cleanup_output_path(self, path: str) -> None:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
