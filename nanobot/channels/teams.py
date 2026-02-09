"""Microsoft Teams channel feasibility adapter (stub mode)."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import TeamsConfig


class TeamsChannel(BaseChannel):
    """
    Teams channel feasibility adapter.

    This implementation intentionally uses stub transport behavior:
    it validates payload mapping and bus wiring without live Graph/Bot
    credentials, which keeps the spike deterministic and testable.
    """

    name = "teams"
    _MAX_SENT_PAYLOADS = 50

    def __init__(self, config: TeamsConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: TeamsConfig = config
        # Keep a bounded buffer for test/debug visibility without unbounded growth.
        self.sent_payloads: deque[dict[str, Any]] = deque(maxlen=self._MAX_SENT_PAYLOADS)

    async def start(self) -> None:
        """Start the Teams channel loop in stub mode."""
        self._running = True
        logger.info("Teams channel started in feasibility stub mode")
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop the Teams channel loop."""
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        """Format and record outbound payload for Teams transport."""
        payload = self._format_outbound_payload(msg)
        self.sent_payloads.append(payload)
        logger.info(f"Teams outbound payload prepared for chat {msg.chat_id}")

    async def ingest_activity(self, activity: dict[str, Any]) -> bool:
        """
        Ingest a simulated Teams inbound payload and publish to bus.

        Returns:
            True when payload is accepted and forwarded, else False.
        """
        parsed = self._parse_inbound_activity(activity)
        if parsed is None:
            return False
        await self._handle_message(
            sender_id=parsed["sender_id"],
            chat_id=parsed["chat_id"],
            content=parsed["content"],
            metadata=parsed["metadata"],
        )
        return True

    def _parse_inbound_activity(self, activity: dict[str, Any]) -> dict[str, Any] | None:
        """Parse a Teams activity payload into message-bus fields."""
        if activity.get("type") != "message":
            return None
        sender_id = str(activity.get("from", {}).get("id", "")).strip()
        chat_id = str(activity.get("conversation", {}).get("id", "")).strip()
        content = str(activity.get("text", "")).strip()
        if not sender_id or not chat_id or not content:
            return None
        return {
            "sender_id": sender_id,
            "chat_id": chat_id,
            "content": content,
            "metadata": {
                "activity_id": activity.get("id"),
                "service_url": activity.get("serviceUrl"),
                "tenant_id": activity.get("conversation", {}).get("tenantId"),
            },
        }

    def _format_outbound_payload(self, msg: OutboundMessage) -> dict[str, Any]:
        """Format an outbound bus message as a Teams-compatible activity payload."""
        payload: dict[str, Any] = {
            "type": "message",
            "text": msg.content,
            "conversation": {"id": msg.chat_id},
            "from": {"id": "nanobot"},
        }
        if msg.reply_to:
            payload["replyToId"] = msg.reply_to
        return payload
