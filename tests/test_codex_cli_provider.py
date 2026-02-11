import asyncio
import json
from pathlib import Path

import pytest

from nanobot.providers.codex_cli_provider import CodexCLIProvider


class _DummyProcess:
    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self.killed = False

    async def communicate(self, input: bytes | None = None) -> tuple[bytes, bytes]:
        self.input = input
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.killed = True


@pytest.mark.asyncio
async def test_codex_cli_provider_uses_output_file_and_strips_openai_prefix(
    tmp_path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        output_path = args[args.index("--output-last-message") + 1]
        Path(output_path).write_text("hello from codex", encoding="utf-8")
        return _DummyProcess(stdout=b"", stderr=b"", returncode=0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    provider = CodexCLIProvider(default_model="openai/gpt-5.3-codex", working_dir=str(tmp_path))
    response = await provider.chat([{"role": "user", "content": "hello"}])

    assert response.content == "hello from codex"
    assert response.has_tool_calls is False
    args = captured["args"]
    assert args[0] == "codex"
    assert "--model" in args
    assert args[args.index("--model") + 1] == "gpt-5.3-codex"
    assert "--sandbox" in args
    kwargs = captured["kwargs"]
    assert kwargs["cwd"] == str(tmp_path)
    assert kwargs["stdin"] == asyncio.subprocess.PIPE


@pytest.mark.asyncio
async def test_codex_cli_provider_parses_agent_message_from_jsonl(tmp_path, monkeypatch) -> None:
    jsonl = "\n".join(
        [
            json.dumps({"type": "other.event", "value": "ignore"}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "jsonl response"},
                }
            ),
        ]
    )

    async def fake_create_subprocess_exec(*args, **kwargs):
        output_path = args[args.index("--output-last-message") + 1]
        Path(output_path).write_text("", encoding="utf-8")
        return _DummyProcess(stdout=jsonl.encode("utf-8"), stderr=b"", returncode=0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    provider = CodexCLIProvider(default_model="openai/gpt-5.3-codex", working_dir=str(tmp_path))
    response = await provider.chat([{"role": "user", "content": "hello"}])

    assert response.content == "jsonl response"


@pytest.mark.asyncio
async def test_codex_cli_provider_returns_error_on_nonzero_exit(tmp_path, monkeypatch) -> None:
    async def fake_create_subprocess_exec(*args, **kwargs):
        output_path = args[args.index("--output-last-message") + 1]
        Path(output_path).write_text("", encoding="utf-8")
        return _DummyProcess(stdout=b"", stderr=b"fatal", returncode=1)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    provider = CodexCLIProvider(default_model="openai/gpt-5.3-codex", working_dir=str(tmp_path))
    response = await provider.chat([{"role": "user", "content": "hello"}])

    assert response.finish_reason == "error"
    assert response.content is not None
    assert "fatal" in response.content
