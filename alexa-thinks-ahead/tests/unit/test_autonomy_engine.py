"""Unit tests for the AutonomyEngine orchestrator.

Tests that the engine correctly delegates to TrustScoreManager,
TierManager, and EscalationManager, and provides a unified interface
for permission checks, acceptance/override recording, and tier config.
"""

import pytest

from src.autonomy.engine import AutonomyEngine
from src.devices.registry import DeviceRegistry
from src.models.device import DeviceCommand
from src.utils.constants import DEVICE_CATEGORIES, FAMILY_MEMBERS


@pytest.fixture
def engine():
    """Create an AutonomyEngine with default device registry."""
    return AutonomyEngine(table=None, device_registry=DeviceRegistry())


class TestCheckPermission:
    """Test check_permission delegates correctly to TierManager."""

    def test_permission_denied_at_tier_1(self, engine):
        """At initial trust (tier 1), actions requiring tier 2+ are denied."""
        action = DeviceCommand(
            command_id="cmd_1",
            device_id="living_room_ac",
            action="set_temperature",
            parameters={"target_temp": 24},
            source="autonomy",
            tier_required=2,
            reversible=True,
        )
        decision = engine.check_permission("rajesh", action)
        assert decision.permitted is False
        assert decision.current_tier == 1
        assert decision.required_tier == 2

    def test_permission_granted_at_tier_1_for_tier_1_action(self, engine):
        """At initial trust (tier 1), tier 1 actions are permitted."""
        action = DeviceCommand(
            command_id="cmd_2",
            device_id="smart_lights",
            action="set_brightness",
            parameters={"brightness": 80},
            source="autonomy",
            tier_required=1,
            reversible=True,
        )
        decision = engine.check_permission("priya", action)
        assert decision.permitted is True
        assert decision.current_tier == 1
        assert decision.required_tier == 1

    def test_permission_granted_after_trust_increase(self, engine):
        """After enough acceptances, member reaches tier 2 and can act."""
        # Increase trust to reach tier 2 (need score >= 21, each acceptance gives +5)
        for _ in range(5):  # 5 * 5 = 25 -> tier 2
            engine.record_acceptance("rajesh", "climate")

        action = DeviceCommand(
            command_id="cmd_3",
            device_id="living_room_ac",
            action="set_temperature",
            parameters={"target_temp": 22},
            source="autonomy",
            tier_required=2,
            reversible=True,
        )
        decision = engine.check_permission("rajesh", action)
        assert decision.permitted is True
        assert decision.current_tier == 2


class TestRecordAcceptance:
    """Test record_acceptance increases trust and tracks interactions."""

    def test_acceptance_increases_trust(self, engine):
        """Recording acceptance increases the trust score."""
        initial_score = engine.trust_manager.get_score("rajesh", "climate")
        engine.record_acceptance("rajesh", "climate")
        new_score = engine.trust_manager.get_score("rajesh", "climate")
        assert new_score > initial_score

    def test_acceptance_logged_in_interaction_log(self, engine):
        """Recording acceptance adds entry to interaction log."""
        engine.record_acceptance("priya", "lighting")
        log = engine.get_interaction_log()
        assert len(log) == 1
        assert log[0]["member"] == "priya"
        assert log[0]["category"] == "lighting"
        assert log[0]["accepted"] is True

    def test_multiple_acceptances_accumulate(self, engine):
        """Multiple acceptances increase trust incrementally."""
        engine.record_acceptance("arjun", "entertainment")
        engine.record_acceptance("arjun", "entertainment")
        engine.record_acceptance("arjun", "entertainment")
        score = engine.trust_manager.get_score("arjun", "entertainment")
        assert score == 15.0  # 3 * 5


class TestRecordOverride:
    """Test record_override decreases trust and tracks interactions."""

    def test_override_decreases_trust(self, engine):
        """Recording override decreases the trust score."""
        # First give some trust
        for _ in range(5):
            engine.record_acceptance("rajesh", "climate")
        score_before = engine.trust_manager.get_score("rajesh", "climate")

        engine.record_override("rajesh", "climate")
        score_after = engine.trust_manager.get_score("rajesh", "climate")
        assert score_after < score_before

    def test_override_logged_in_interaction_log(self, engine):
        """Recording override adds entry to interaction log."""
        engine.record_override("dadaji", "climate")
        log = engine.get_interaction_log()
        assert len(log) == 1
        assert log[0]["member"] == "dadaji"
        assert log[0]["category"] == "climate"
        assert log[0]["accepted"] is False

    def test_override_floors_at_zero(self, engine):
        """Override at score 0 keeps score at 0."""
        engine.record_override("ananya", "lighting")
        score = engine.trust_manager.get_score("ananya", "lighting")
        assert score == 0.0


class TestGetTierConfig:
    """Test get_tier_config returns all member-category pairs."""

    def test_returns_all_pairs(self, engine):
        """Tier config contains all 48 member-category combinations."""
        config = engine.get_tier_config()
        expected_count = len(FAMILY_MEMBERS) * len(DEVICE_CATEGORIES)
        assert len(config) == expected_count

    def test_all_pairs_have_valid_keys(self, engine):
        """Every key in tier config follows 'member_category' format."""
        config = engine.get_tier_config()
        for member in FAMILY_MEMBERS:
            for category in DEVICE_CATEGORIES:
                key = f"{member}_{category}"
                assert key in config, f"Missing key: {key}"

    def test_initial_tiers_are_all_one(self, engine):
        """At initialization, all tiers should be 1 (score 0)."""
        config = engine.get_tier_config()
        for key, tier in config.items():
            assert tier == 1, f"Expected tier 1 for {key}, got {tier}"

    def test_tier_updates_after_acceptance(self, engine):
        """Tier config reflects trust changes after acceptances."""
        # Push rajesh climate to tier 2 (need score >= 21)
        for _ in range(5):  # 5 * 5 = 25
            engine.record_acceptance("rajesh", "climate")

        config = engine.get_tier_config()
        assert config["rajesh_climate"] == 2
        # Other pairs should remain at tier 1
        assert config["priya_climate"] == 1


class TestApplyDailyDecay:
    """Test apply_daily_decay delegates to EscalationManager."""

    def test_decay_on_zero_scores_returns_empty(self, engine):
        """Decay on all-zero scores should not reduce anything."""
        decayed = engine.apply_daily_decay()
        assert decayed == {}

    def test_decay_reduces_nonzero_scores(self, engine):
        """Decay reduces scores that are above 0."""
        engine.record_acceptance("rajesh", "climate")
        score_before = engine.trust_manager.get_score("rajesh", "climate")
        assert score_before > 0

        decayed = engine.apply_daily_decay()
        score_after = engine.trust_manager.get_score("rajesh", "climate")
        assert score_after < score_before
        assert "rajesh#climate" in decayed


class TestInteractionTracking:
    """Test that all interactions are tracked for learning engine."""

    def test_mixed_interactions_tracked(self, engine):
        """Both acceptances and overrides appear in interaction log."""
        engine.record_acceptance("rajesh", "climate")
        engine.record_override("priya", "security")
        engine.record_acceptance("arjun", "entertainment")

        log = engine.get_interaction_log()
        assert len(log) == 3
        assert log[0]["accepted"] is True
        assert log[1]["accepted"] is False
        assert log[2]["accepted"] is True

    def test_interaction_log_has_timestamps(self, engine):
        """Each interaction record includes a timestamp."""
        engine.record_acceptance("dadaji", "climate")
        log = engine.get_interaction_log()
        assert "timestamp" in log[0]
