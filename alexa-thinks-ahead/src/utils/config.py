"""System-wide configuration constants and settings.

Configuration is environment-aware: every field falls back to a sensible
local-development default, but can be overridden by an environment variable.
This lets the exact same code run:

  * Locally (no env vars set) -> uses the dataclass defaults.
  * On AWS Lambda            -> uses the env vars injected by the SAM template
                                 (DEVICE_STATE_TABLE, BEDROCK_MODEL_ID, etc.).

See AWS_INTEGRATION.md for the full list of variables and how they are wired.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

_config_instance: Optional["SystemConfig"] = None


def _env_str(name: str, default: str) -> str:
    """Read a string env var, falling back to default when unset/empty."""
    value = os.environ.get(name)
    return value if value else default


def _env_int(name: str, default: int) -> int:
    """Read an integer env var, falling back to default on unset/invalid."""
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Read a float env var, falling back to default on unset/invalid."""
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass
class SystemConfig:
    """Central configuration for the Alexa Thinks Ahead system.

    Contains all tunable parameters for the cognitive pipeline,
    reasoning engine, autonomy tiers, and learning subsystems.

    Instantiate via :func:`get_config` (or :meth:`SystemConfig.from_env`) so
    that environment overrides are applied. Direct ``SystemConfig()`` still
    works and yields the pure local-development defaults.
    """

    # Sensor pipeline
    sensor_poll_interval_seconds: int = 30
    max_staleness_seconds: int = 3600
    context_history_hours: int = 24

    # Bedrock reasoning
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_region: str = "ap-south-1"
    bedrock_timeout_seconds: int = 3
    bedrock_max_retries: int = 3
    bedrock_backoff_base_seconds: float = 1.0

    # Confidence thresholds
    action_threshold: float = 0.85
    recommend_threshold: float = 0.60
    inform_threshold: float = 0.40
    pattern_confidence_threshold: float = 0.75

    # Trust/Autonomy
    trust_acceptance_delta: float = 5.0
    trust_override_penalty: float = 15.0
    trust_decay_per_day: float = 0.5
    escalation_window_days: int = 7
    escalation_min_acceptance_rate: float = 0.80

    # Learning
    feedback_rolling_window_days: int = 90
    bayesian_observation_noise: float = 1.0

    # DynamoDB table names
    device_state_table: str = "alexa-thinks-ahead-device-states"
    context_snapshot_table: str = "alexa-thinks-ahead-context-snapshots"
    trust_score_table: str = "alexa-thinks-ahead-trust-scores"
    preference_table: str = "alexa-thinks-ahead-preferences"

    # EventBridge
    event_bus_name: str = "alexa-thinks-ahead-events"

    # TTL
    device_state_ttl_days: int = 30
    context_snapshot_ttl_days: int = 7

    # Deployment metadata
    stage: str = "local"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Build a config, overriding defaults with environment variables.

        Only the AWS-facing fields (table names, region, model id, event bus,
        stage, log level) are wired to env vars, since those are the values
        the SAM template injects at deploy time. Tuning knobs keep their
        code defaults unless you add an explicit override here.
        """
        defaults = cls()
        return cls(
            # Bedrock
            bedrock_model_id=_env_str("BEDROCK_MODEL_ID", defaults.bedrock_model_id),
            bedrock_region=_env_str(
                "BEDROCK_REGION",
                _env_str("AWS_DEFAULT_REGION", defaults.bedrock_region),
            ),
            bedrock_timeout_seconds=_env_int(
                "BEDROCK_TIMEOUT_SECONDS", defaults.bedrock_timeout_seconds
            ),
            bedrock_max_retries=_env_int(
                "BEDROCK_MAX_RETRIES", defaults.bedrock_max_retries
            ),
            # DynamoDB tables (SAM injects the stage-suffixed names)
            device_state_table=_env_str(
                "DEVICE_STATE_TABLE", defaults.device_state_table
            ),
            context_snapshot_table=_env_str(
                "CONTEXT_SNAPSHOT_TABLE", defaults.context_snapshot_table
            ),
            trust_score_table=_env_str(
                "TRUST_SCORE_TABLE", defaults.trust_score_table
            ),
            preference_table=_env_str(
                "PREFERENCE_TABLE", defaults.preference_table
            ),
            # EventBridge
            event_bus_name=_env_str("EVENT_BUS_NAME", defaults.event_bus_name),
            # Deployment metadata
            stage=_env_str("STAGE", defaults.stage),
            log_level=_env_str("LOG_LEVEL", defaults.log_level),
        )


def get_config() -> SystemConfig:
    """Return a singleton SystemConfig instance.

    Builds the instance from the environment on first call (so AWS env vars
    take effect) and returns the same instance on subsequent calls.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = SystemConfig.from_env()
    return _config_instance


def reset_config() -> None:
    """Clear the cached config singleton.

    Useful in tests that set environment variables and want the next
    ``get_config()`` call to re-read them.
    """
    global _config_instance
    _config_instance = None
