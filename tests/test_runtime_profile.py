import pytest

from nanobot.config.profile import ProfileValidationError, validate_runtime_profile
from nanobot.config.schema import Config


def _enterprise_config() -> Config:
    config = Config()
    config.runtime_profile = "enterprise_minimal"
    config.providers.openai.api_key = "test-key"
    config.agents.defaults.model = "openai/gpt-4o-mini"
    return config


def test_enterprise_minimal_allows_cli_agent_mode_with_openai() -> None:
    config = _enterprise_config()
    validate_runtime_profile(config, mode="agent")


def test_enterprise_minimal_rejects_non_openai_provider() -> None:
    config = _enterprise_config()
    config.providers.anthropic.api_key = "anthropic-key"
    config.agents.defaults.model = "anthropic/claude-3-5-sonnet"

    with pytest.raises(ProfileValidationError, match="requires OpenAI provider routing"):
        validate_runtime_profile(config, mode="agent")


def test_enterprise_minimal_rejects_non_openai_model_even_with_openai_provider() -> None:
    config = _enterprise_config()
    config.agents.defaults.model = "anthropic/claude-3-5-sonnet"

    with pytest.raises(ProfileValidationError, match="requires explicit OpenAI model prefix"):
        validate_runtime_profile(config, mode="agent")


def test_enterprise_minimal_rejects_disallowed_gateway_channels() -> None:
    config = _enterprise_config()
    config.channels.telegram.enabled = True

    with pytest.raises(ProfileValidationError, match="blocks non-approved channels"):
        validate_runtime_profile(config, mode="gateway")


def test_enterprise_minimal_rejects_gateway_when_no_channels_explicitly_approved() -> None:
    config = _enterprise_config()

    with pytest.raises(ProfileValidationError, match="CLI-first"):
        validate_runtime_profile(config, mode="gateway")


def test_enterprise_minimal_rejects_unsupported_allowed_channel_config() -> None:
    config = _enterprise_config()
    config.enterprise_allowed_channels = ["telegram"]

    with pytest.raises(ProfileValidationError, match="allows only optional enterprise channels"):
        validate_runtime_profile(config, mode="agent")


def test_enterprise_minimal_allows_codex_cli_route_without_openai_api_key() -> None:
    config = Config()
    config.runtime_profile = "enterprise_minimal"
    config.providers.openai.api_key = ""
    config.providers.openai.use_codex_cli = True
    config.agents.defaults.model = "openai/gpt-5.3-codex"

    validate_runtime_profile(config, mode="agent")
