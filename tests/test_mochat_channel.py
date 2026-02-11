import pytest

from nanobot.bus.queue import MessageBus
from nanobot.channels.mochat import MochatChannel
from nanobot.config.schema import MochatConfig


@pytest.mark.asyncio
async def test_watch_payload_panel_falls_back_to_panel_id() -> None:
    channel = MochatChannel(MochatConfig(), MessageBus())
    seen: list[tuple[str, str]] = []

    async def _capture(target_id: str, event: dict, target_kind: str) -> None:
        seen.append((target_kind, target_id))

    channel._process_inbound_event = _capture  # type: ignore[method-assign]

    await channel._handle_watch_payload(
        {
            "panelId": "panel-42",
            "events": [{"type": "message.add", "payload": {"author": "user"}}],
        },
        "panel",
    )

    assert seen == [("panel", "panel-42")]


@pytest.mark.asyncio
async def test_watch_payload_session_requires_session_id() -> None:
    channel = MochatChannel(MochatConfig(), MessageBus())
    seen: list[tuple[str, str]] = []

    async def _capture(target_id: str, event: dict, target_kind: str) -> None:
        seen.append((target_kind, target_id))

    channel._process_inbound_event = _capture  # type: ignore[method-assign]

    await channel._handle_watch_payload(
        {
            "panelId": "panel-42",
            "events": [{"type": "message.add", "payload": {"author": "user"}}],
        },
        "session",
    )

    assert seen == []
