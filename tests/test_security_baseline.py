from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from nanobot.agent.tools.filesystem import _resolve_path
from nanobot.agent.tools.web import _validate_url
from nanobot.channels.base import BaseChannel
from nanobot.bus.queue import MessageBus
from nanobot.config.loader import save_config
from nanobot.config.schema import Config
from nanobot.security.policy import ToolPolicy


class _DummyChannel(BaseChannel):
    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def send(self, msg) -> None:
        _ = msg
        return None


def test_filesystem_rejects_prefix_sibling_escape(tmp_path: Path) -> None:
    allowed = tmp_path / "workspace"
    sibling = tmp_path / "workspace_evil"
    allowed.mkdir()
    sibling.mkdir()

    with pytest.raises(PermissionError):
        _resolve_path(str(sibling / "secret.txt"), allowed)


def test_web_validate_url_blocks_private_and_link_local_targets() -> None:
    ok, reason = _validate_url("http://127.0.0.1:8080/admin")
    assert ok is False
    assert "Blocked" in reason

    ok, reason = _validate_url("http://169.254.169.254/latest/meta-data/")
    assert ok is False
    assert "Blocked" in reason


def test_web_validate_url_blocks_hostnames_resolving_to_private_ips(monkeypatch) -> None:
    monkeypatch.setattr(
        "nanobot.agent.tools.web._resolve_host_ips",
        lambda host: {"10.1.2.3"} if host == "internal.example" else {"93.184.216.34"},
    )

    ok, reason = _validate_url("http://internal.example/resource")
    assert ok is False
    assert "non-public IP" in reason


def test_channel_default_deny_when_allowlist_empty() -> None:
    cfg = SimpleNamespace(allow_from=[], allow_unlisted_senders=False)
    channel = _DummyChannel(cfg, MessageBus())
    assert channel.is_allowed("user-1") is False


def test_channel_can_opt_in_to_allow_unlisted_senders() -> None:
    cfg = SimpleNamespace(allow_from=[], allow_unlisted_senders=True)
    channel = _DummyChannel(cfg, MessageBus())
    assert channel.is_allowed("user-1") is True


def test_tool_policy_blocks_and_allows() -> None:
    policy = ToolPolicy(blocked_tools=["exec", "write_file"], allowed_tools=[])
    assert policy.is_allowed("read_file") is True
    assert policy.is_allowed("exec") is False
    assert "blocked by security policy" in policy.rejection_reason("exec")


def test_save_config_uses_restrictive_permissions(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    save_config(Config(), path)

    assert path.exists()
    if os.name != "nt":
        mode = path.stat().st_mode & 0o777
        parent_mode = path.parent.stat().st_mode & 0o777
        assert mode == 0o600
        assert parent_mode == 0o700
