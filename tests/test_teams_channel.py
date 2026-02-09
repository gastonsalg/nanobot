import asyncio

import pytest

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.teams import TeamsChannel
from nanobot.config.schema import TeamsConfig


def _config(allow_unlisted: bool = True) -> TeamsConfig:
    return TeamsConfig(
        enabled=True,
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
