"""Security policy helpers for tool access control."""

from __future__ import annotations


class ToolPolicy:
    """Simple allow/block policy for agent tools."""

    def __init__(
        self,
        blocked_tools: list[str] | None = None,
        allowed_tools: list[str] | None = None,
    ):
        self._blocked = {t.strip() for t in (blocked_tools or []) if t and t.strip()}
        self._allowed = {t.strip() for t in (allowed_tools or []) if t and t.strip()}

    def is_allowed(self, tool_name: str, context: dict[str, str] | None = None) -> bool:
        _ = context  # reserved for future contextual policy checks
        name = (tool_name or "").strip()
        if not name:
            return False
        if self._allowed and name not in self._allowed:
            return False
        if name in self._blocked:
            return False
        return True

    def rejection_reason(self, tool_name: str) -> str:
        return f"tool '{tool_name}' blocked by security policy"

