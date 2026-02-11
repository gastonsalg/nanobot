import asyncio

import pytest

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.teams import TeamsChannel
from nanobot.config.schema import TeamsConfig


def _config(allow_unlisted: bool = True, mode: str = "stub") -> TeamsConfig:
    return TeamsConfig(
        enabled=True,
        mode=mode,
        allow_unlisted_senders=allow_unlisted,
        allow_from=[],
    )


@pytest.mark.asyncio
async def test_teams_inbound_activity_maps_to_bus_message() -> None:
    bus = MessageBus()
    channel = TeamsChannel(_config(allow_unlisted=True), bus)
    activity = {
        "type": "message",
        "id": "activity-1",
        "serviceUrl": "https://smba.trafficmanager.net/emea/",
        "from": {"id": "user-42"},
        "conversation": {"id": "conv-99", "tenantId": "tenant-abc"},
        "text": "hello from teams",
    }

    accepted = await channel.ingest_activity(activity)
    assert accepted is True

    inbound = await asyncio.wait_for(bus.consume_inbound(), timeout=0.2)
    assert inbound.channel == "teams"
    assert inbound.sender_id == "user-42"
    assert inbound.chat_id == "conv-99"
    assert inbound.content == "hello from teams"
    assert inbound.metadata["activity_id"] == "activity-1"
    assert inbound.metadata["tenant_id"] == "tenant-abc"
    assert inbound.metadata["teams"]["service_url"] == "https://smba.trafficmanager.net/emea/"


@pytest.mark.asyncio
async def test_teams_inbound_is_blocked_by_default_sender_policy() -> None:
    bus = MessageBus()
    channel = TeamsChannel(_config(allow_unlisted=False), bus)
    activity = {
        "type": "message",
        "from": {"id": "user-blocked"},
        "conversation": {"id": "conv-1"},
        "text": "should be denied",
    }

    accepted = await channel.ingest_activity(activity)
    assert accepted is True  # payload parsed, but sender policy may still reject publish
    assert bus.inbound_size == 0


def test_teams_outbound_payload_format() -> None:
    channel = TeamsChannel(_config(), MessageBus())
    outbound = OutboundMessage(
        channel="teams",
        chat_id="conv-100",
        content="agent reply",
        reply_to="activity-2",
    )

    payload = channel._format_outbound_payload(outbound)
    assert payload["type"] == "message"
    assert payload["text"] == "agent reply"
    assert payload["conversation"]["id"] == "conv-100"
    assert payload["replyToId"] == "activity-2"


@pytest.mark.asyncio
async def test_teams_send_records_formatted_payload() -> None:
    channel = TeamsChannel(_config(), MessageBus())
    outbound = OutboundMessage(channel="teams", chat_id="conv-55", content="ok")
    await channel.send(outbound)

    assert len(channel.sent_payloads) == 1
    assert channel.sent_payloads[0]["conversation"]["id"] == "conv-55"


@pytest.mark.asyncio
async def test_teams_send_payload_buffer_is_bounded() -> None:
    channel = TeamsChannel(_config(), MessageBus())

    for i in range(channel._MAX_SENT_PAYLOADS + 5):
        await channel.send(
            OutboundMessage(channel="teams", chat_id=f"conv-{i}", content=f"msg-{i}")
        )

    assert len(channel.sent_payloads) == channel._MAX_SENT_PAYLOADS
    # Oldest entries should be dropped once maxlen is reached.
    assert channel.sent_payloads[0]["conversation"]["id"] == "conv-5"


@pytest.mark.asyncio
async def test_teams_live_mode_without_credentials_does_not_run() -> None:
    channel = TeamsChannel(_config(mode="botframework_webhook"), MessageBus())

    await channel.start()

    assert channel.is_running is False


@pytest.mark.asyncio
async def test_teams_live_send_posts_activity_with_token(monkeypatch) -> None:
    config = _config(mode="botframework_webhook")
    config.app_id = "app-id"
    config.app_password = "app-secret"
    channel = TeamsChannel(config, MessageBus())

    captured: dict[str, object] = {}

    async def fake_get_token() -> str:
        return "token-123"

    async def fake_post_activity(
        service_url: str,
        conversation_id: str,
        payload: dict[str, object],
        access_token: str,
    ) -> None:
        captured["service_url"] = service_url
        captured["conversation_id"] = conversation_id
        captured["payload"] = payload
        captured["access_token"] = access_token

    monkeypatch.setattr(channel, "_get_bot_access_token", fake_get_token)
    monkeypatch.setattr(channel, "_post_activity", fake_post_activity)

    await channel.send(
        OutboundMessage(
            channel="teams",
            chat_id="conv-live",
            content="hello",
            metadata={
                "teams": {
                    "service_url": "https://smba.trafficmanager.net/emea/",
                    "activity_id": "act-7",
                }
            },
        )
    )

    assert captured["service_url"] == "https://smba.trafficmanager.net/emea"
    assert captured["conversation_id"] == "conv-live"
    assert captured["access_token"] == "token-123"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["text"] == "hello"
    assert payload["replyToId"] == "act-7"


@pytest.mark.asyncio
async def test_teams_live_send_blocks_untrusted_service_url(monkeypatch) -> None:
    config = _config(mode="botframework_webhook")
    config.app_id = "app-id"
    config.app_password = "app-secret"
    channel = TeamsChannel(config, MessageBus())

    called = False

    async def fake_get_token() -> str:
        return "token-123"

    async def fake_post_activity(*args, **kwargs) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(channel, "_get_bot_access_token", fake_get_token)
    monkeypatch.setattr(channel, "_post_activity", fake_post_activity)

    await channel.send(
        OutboundMessage(
            channel="teams",
            chat_id="conv-live",
            content="hello",
            metadata={"teams": {"service_url": "https://evil.example", "activity_id": "act-7"}},
        )
    )

    assert called is False


def test_teams_bearer_auth_helper() -> None:
    assert TeamsChannel._has_bearer_auth(None) is False
    assert TeamsChannel._has_bearer_auth("") is False
    assert TeamsChannel._has_bearer_auth("Basic abc") is False
    assert TeamsChannel._has_bearer_auth("Bearer") is False
    assert TeamsChannel._has_bearer_auth("Bearer token-123") is True
