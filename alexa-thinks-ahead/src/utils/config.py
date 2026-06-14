"""System-wide configuration constants and settings."""

from dataclasses import dataclass
from typing import Optional

_config_instance: Optional["SystemConfig"] = None


@dataclass
class SystemConfig:
    """Central configuration for the Alexa Thinks Ahead system.

    Contains all tunable parameters for the cognitive pipeline,
    reasoning engine, autonomy tiers, and learning subsystems.
    """

    # Sensor pipeline
    sensor_poll_interval_seconds: int = 30
    max_staleness_seconds: int = 3600
    context_history_hours: int = 24

    # Bedrock reasoning
    bedrock_model_id: str = "anthropic.claude-3-sonnet"
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

    # TTL
    device_state_ttl_days: int = 30
    context_snapshot_ttl_days: int = 7


def get_config() -> SystemConfig:
    """Return a singleton SystemConfig instance.

    Creates the instance on first call and returns the same
    instance on subsequent calls.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = SystemConfig()
    return _config_instance
