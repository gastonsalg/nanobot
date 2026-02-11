"""Microsoft Teams channel with Bot Framework webhook support."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any
from urllib.parse import urlparse

import httpx
from aiohttp import web
from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import TeamsConfig

BOTFRAMEWORK_TOKEN_URL = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
BOTFRAMEWORK_SCOPE = "https://api.botframework.com/.default"


class TeamsChannel(BaseChannel):
    """
    Teams channel implementation.

    Supports two modes:
    - ``stub``: deterministic local mode for tests/feasibility.
    - ``botframework_webhook``: live inbound webhook + outbound replies.
    """

    name = "teams"
    _MAX_SENT_PAYLOADS = 50

    def __init__(
        self,
        config: TeamsConfig,
        bus: MessageBus,
        gateway_host: str = "0.0.0.0",
        gateway_port: int = 18790,
    ):
        super().__init__(config, bus)
        self.config: TeamsConfig = config
        self.gateway_host = gateway_host
        self.gateway_port = gateway_port

        # Bounded payload buffer for debug/tests.
        self.sent_payloads: deque[dict[str, Any]] = deque(maxlen=self._MAX_SENT_PAYLOADS)

        # Live webhook runtime state.
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._http_client: httpx.AsyncClient | None = None

        # Bot Framework token cache.
        self._bot_token: str | None = None
        self._bot_token_expires_at: float = 0.0

    async def start(self) -> None:
        """Start channel runtime in configured mode."""
        self._running = True
        if not self._is_live_mode():
            logger.info("Teams channel started in stub mode")
            while self._running:
                await asyncio.sleep(1)
            return

        if not self._has_live_credentials():
            logger.error(
                "Teams channel live mode requires app_id and app_password "
                "(set channels.teams.appId and channels.teams.appPassword)."
            )
            self._running = False
            return

        await self._start_webhook_server()
        endpoint = f"http://{self.gateway_host}:{self.gateway_port}{self.config.webhook_path}"
        logger.info(f"Teams channel started in live mode at {endpoint}")

        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop channel runtime and release network resources."""
        self._running = False

        if self._site is not None:
            await self._site.stop()
            self._site = None
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def send(self, msg: OutboundMessage) -> None:
        """Send an outbound message to Teams when live metadata is available."""
        payload = self._format_outbound_payload(msg)
        self.sent_payloads.append(payload)

        if not self._is_live_mode():
            logger.debug(f"Teams outbound payload buffered in stub mode for chat {msg.chat_id}")
            return

        service_url = self._resolve_service_url(msg.metadata)
        if not service_url:
            logger.warning(
                "Teams outbound send skipped: missing service_url in metadata "
                "(usually available only when replying to a Teams inbound activity)."
            )
            return

        access_token = await self._get_bot_access_token()
        if not access_token:
            logger.error("Teams outbound send failed: unable to obtain Bot Framework access token")
            return

        if not payload.get("replyToId"):
            reply_to = (
                (msg.metadata.get("teams", {}) if isinstance(msg.metadata, dict) else {}).get("activity_id")
                or (msg.metadata.get("activity_id") if isinstance(msg.metadata, dict) else None)
            )
            if reply_to:
                payload["replyToId"] = str(reply_to)

        await self._post_activity(
            service_url=service_url,
            conversation_id=msg.chat_id,
            payload=payload,
            access_token=access_token,
        )

    async def ingest_activity(self, activity: dict[str, Any]) -> bool:
        """
        Ingest a Teams inbound payload and publish to bus.

        Returns:
            True when payload is parseable and handled, else False.
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

    async def _start_webhook_server(self) -> None:
        app = web.Application()
        app.router.add_post(self.config.webhook_path, self._handle_webhook_request)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self.gateway_host, self.gateway_port)
        await self._site.start()

    async def _handle_webhook_request(self, request: web.Request) -> web.Response:
        if self._is_live_mode() and self.config.require_auth_header:
            if not self._has_bearer_auth(request.headers.get("Authorization")):
                return web.json_response({"error": "unauthorized"}, status=401)

        try:
            activity = await request.json()
        except Exception:
            return web.json_response({"error": "invalid JSON payload"}, status=400)

        accepted = await self.ingest_activity(activity)
        return web.json_response({"accepted": bool(accepted)})

    def _parse_inbound_activity(self, activity: dict[str, Any]) -> dict[str, Any] | None:
        """Parse Teams/Bot Framework activity payload into bus fields."""
        if activity.get("type") != "message":
            return None

        from_obj = activity.get("from", {}) if isinstance(activity.get("from"), dict) else {}
        conversation = (
            activity.get("conversation", {})
            if isinstance(activity.get("conversation"), dict)
            else {}
        )
        channel_data = (
            activity.get("channelData", {})
            if isinstance(activity.get("channelData"), dict)
            else {}
        )

        sender_id_raw = str(from_obj.get("id", "")).strip()
        aad_object_id = str(from_obj.get("aadObjectId", "")).strip()
        sender_id = f"{aad_object_id}|{sender_id_raw}" if aad_object_id and sender_id_raw else (aad_object_id or sender_id_raw)
        chat_id = str(conversation.get("id", "")).strip()
        content = str(activity.get("text", "")).strip()
        if not sender_id or not chat_id or not content:
            return None

        tenant_id = str(conversation.get("tenantId", "")).strip()
        if not tenant_id:
            tenant = channel_data.get("tenant")
            if isinstance(tenant, dict):
                tenant_id = str(tenant.get("id", "")).strip()

        service_url = str(activity.get("serviceUrl", "")).strip()
        metadata = {
            "activity_id": activity.get("id"),
            "service_url": service_url,
            "tenant_id": tenant_id,
            "teams": {
                "activity_id": activity.get("id"),
                "service_url": service_url,
                "tenant_id": tenant_id,
                "conversation_type": conversation.get("conversationType"),
            },
        }
        return {
            "sender_id": sender_id,
            "chat_id": chat_id,
            "content": content,
            "metadata": metadata,
        }

    def _format_outbound_payload(self, msg: OutboundMessage) -> dict[str, Any]:
        """Format an outbound bus message as Bot Framework activity payload."""
        payload: dict[str, Any] = {
            "type": "message",
            "text": msg.content,
            "conversation": {"id": msg.chat_id},
            "from": {"id": self.config.app_id or "goodbot"},
        }
        if msg.reply_to:
            payload["replyToId"] = msg.reply_to
        return payload

    def _is_live_mode(self) -> bool:
        return self.config.mode == "botframework_webhook"

    def _has_live_credentials(self) -> bool:
        return bool(self.config.app_id and self.config.app_password)

    def _resolve_service_url(self, metadata: dict[str, Any] | None) -> str:
        if not metadata:
            return ""
        teams_meta = metadata.get("teams")
        if isinstance(teams_meta, dict):
            service_url = str(teams_meta.get("service_url", "")).strip()
            if service_url and self._is_allowed_service_url(service_url):
                return service_url.rstrip("/")
        service_url = str(metadata.get("service_url", "")).strip()
        if service_url and self._is_allowed_service_url(service_url):
            return service_url.rstrip("/")
        return ""

    async def _get_bot_access_token(self) -> str:
        now = time.time()
        if self._bot_token and now < self._bot_token_expires_at:
            return self._bot_token
        if not self._has_live_credentials():
            return ""

        client = self._get_http_client()
        try:
            resp = await client.post(
                BOTFRAMEWORK_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.app_id,
                    "client_secret": self.config.app_password,
                    "scope": BOTFRAMEWORK_SCOPE,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            payload = resp.json()
            token = str(payload.get("access_token", "")).strip()
            expires_in = int(payload.get("expires_in", 3600))
            if not token:
                return ""
            self._bot_token = token
            self._bot_token_expires_at = now + max(expires_in - 60, 60)
            return token
        except Exception as e:
            logger.error(f"Teams token acquisition failed: {e}")
            return ""

    async def _post_activity(
        self,
        service_url: str,
        conversation_id: str,
        payload: dict[str, Any],
        access_token: str,
    ) -> None:
        endpoint = f"{service_url}/v3/conversations/{conversation_id}/activities"
        client = self._get_http_client()
        try:
            resp = await client.post(
                endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            logger.info(f"Teams outbound message sent to conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Teams outbound send failed: {e}")

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=15.0)
        return self._http_client

    @staticmethod
    def _has_bearer_auth(auth_header: str | None) -> bool:
        if not auth_header:
            return False
        parts = auth_header.strip().split(maxsplit=1)
        if len(parts) != 2:
            return False
        scheme, token = parts
        return scheme.lower() == "bearer" and bool(token.strip())

    def _is_allowed_service_url(self, service_url: str) -> bool:
        try:
            parsed = urlparse(service_url)
        except Exception:
            return False
        if parsed.scheme.lower() != "https":
            return False
        host = (parsed.hostname or "").lower().strip(".")
        if not host:
            return False
        if parsed.username or parsed.password:
            return False

        allowed_hosts = [h.lower().strip(".") for h in self.config.allowed_service_url_hosts if h]
        return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)
