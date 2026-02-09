"""Runtime profile validation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from nanobot.config.schema import Config


class ProfileValidationError(ValueError):
    """Raised when runtime profile constraints are violated."""


ENTERPRISE_MINIMAL = "enterprise_minimal"
OPENAI_PROVIDER = "openai"
ENTERPRISE_OPTIONAL_CHANNELS = {"teams"}
OPENAI_MODEL_PREFIX = "openai/"


@dataclass(frozen=True)
class ProfileValidationResult:
    """Profile validation context for logging/reporting."""

    profile: str
    mode: str


def validate_runtime_profile(config: Config, mode: str) -> ProfileValidationResult:
    """Validate profile restrictions for the given command mode."""
    profile = (config.runtime_profile or "default").strip().lower()
    current_mode = (mode or "").strip().lower()
    if profile != ENTERPRISE_MINIMAL:
        return ProfileValidationResult(profile=profile, mode=current_mode)

    provider_name = (config.get_provider_name() or "").strip().lower()
    if provider_name != OPENAI_PROVIDER:
        detected = provider_name or "none"
        raise ProfileValidationError(
            "enterprise_minimal requires OpenAI provider routing; "
            f"detected provider '{detected}'."
        )
    model_name = (config.agents.defaults.model or "").strip().lower()
    if not model_name.startswith(OPENAI_MODEL_PREFIX):
        raise ProfileValidationError(
            "enterprise_minimal requires explicit OpenAI model prefix "
            f"('{OPENAI_MODEL_PREFIX}...'); got '{config.agents.defaults.model}'."
        )

    configured_allowed_channels = {
        channel.strip().lower()
        for channel in config.enterprise_allowed_channels
        if channel and channel.strip()
    }
    unsupported_allowed_channels = configured_allowed_channels - ENTERPRISE_OPTIONAL_CHANNELS
    if unsupported_allowed_channels:
        unsupported = ", ".join(sorted(unsupported_allowed_channels))
        raise ProfileValidationError(
            "enterprise_minimal allows only optional enterprise channels "
            f"{sorted(ENTERPRISE_OPTIONAL_CHANNELS)}; got {unsupported}."
        )

    if current_mode == "gateway":
        enabled_channels = _enabled_channels(config)
        disallowed_enabled = enabled_channels - configured_allowed_channels
        if disallowed_enabled:
            disallowed = ", ".join(sorted(disallowed_enabled))
            raise ProfileValidationError(
                "enterprise_minimal blocks non-approved channels in gateway mode: "
                f"{disallowed}."
            )
        if not enabled_channels:
            raise ProfileValidationError(
                "enterprise_minimal is CLI-first. Gateway mode requires explicitly "
                "approved enterprise channels (for example, 'teams' when available)."
            )

    return ProfileValidationResult(profile=profile, mode=current_mode)


def _enabled_channels(config: Config) -> set[str]:
    """Return channel names that are enabled in config."""
    enabled: set[str] = set()
    for name, channel_cfg in config.channels.model_dump().items():
        if isinstance(channel_cfg, dict) and channel_cfg.get("enabled"):
            enabled.add(name)
    return enabled
