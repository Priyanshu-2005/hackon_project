"""Unit tests for escalation and decay logic.

Tests requirements:
- 5.6: Require 7-day window + 80% acceptance for escalation
- 5.7: De-escalation is immediate on override
- 5.8: Apply trust decay during inactivity
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.autonomy.escalation import EscalationManager
from src.autonomy.tiers import TierManager
from src.autonomy.trust import TrustScoreManager
from src.devices.registry import DeviceRegistry


@pytest.fixture
def trust_manager():
    """Create a TrustScoreManager for testing."""
    return TrustScoreManager(table=None)


@pytest.fixture
def tier_manager(trust_manager):
    """Create a TierManager for testing."""
    registry = DeviceRegistry()
    return TierManager(trust_manager=trust_manager, device_registry=registry)


@pytest.fixture
def escalation_manager(trust_manager, tier_manager):
    """Create an EscalationManager for testing."""
    return EscalationManager(trust_manager=trust_manager, tier_manager=tier_manager)


class TestCheckEscalation:
    """Tests for check_escalation() logic."""

    def test_escalation_denied_when_score_below_threshold(self, escalation_manager, trust_manager):
        """Escalation denied when trust score is 0 (hasn't earned any tier advancement)."""
        # Score 0 -> Tier 1, threshold for tier 1 is 0, so score meets it.
        # But with no history it should be denied.
        trust_manager._scores[("rajesh", "climate")] = 0.0

        result = escalation_manager.check_escalation("rajesh", "climate")

        assert result is None

    def test_escalation_denied_when_acceptance_rate_below_80(self, escalation_manager, trust_manager):
        """Escalation denied when acceptance rate is below 80%."""
        trust_manager._scores[("rajesh", "climate")] = 25.0

        # Add interactions over 7+ days with only 50% acceptance
        key = ("rajesh", "climate")
        now = datetime.now(timezone.utc)
        escalation_manager._interaction_history[key] = [
            {"timestamp": now - timedelta(days=10), "accepted": True},
            {"timestamp": now - timedelta(days=9), "accepted": False},
            {"timestamp": now - timedelta(days=8), "accepted": True},
            {"timestamp": now - timedelta(days=7), "accepted": False},
            {"timestamp": now - timedelta(days=6), "accepted": False},
            {"timestamp": now - timedelta(days=5), "accepted": False},
            {"timestamp": now - timedelta(days=4), "accepted": True},
            {"timestamp": now - timedelta(days=3), "accepted": False},
        ]

        result = escalation_manager.check_escalation("rajesh", "climate")

        assert result is None

    def test_escalation_denied_when_window_too_short(self, escalation_manager, trust_manager):
        """Escalation denied when interaction history doesn't span 7 days."""
        trust_manager._scores[("rajesh", "climate")] = 25.0

        # Add interactions only spanning 3 days (all accepted)
        key = ("rajesh", "climate")
        now = datetime.now(timezone.utc)
        escalation_manager._interaction_history[key] = [
            {"timestamp": now - timedelta(days=3), "accepted": True},
            {"timestamp": now - timedelta(days=2), "accepted": True},
            {"timestamp": now - timedelta(days=1), "accepted": True},
        ]

        result = escalation_manager.check_escalation("rajesh", "climate")

        assert result is None

    def test_escalation_denied_when_already_at_tier_5(self, escalation_manager, trust_manager):
        """Escalation denied when member is already at max tier (5)."""
        trust_manager._scores[("rajesh", "climate")] = 95.0

        result = escalation_manager.check_escalation("rajesh", "climate")

        assert result is None

    def test_escalation_denied_when_no_history(self, escalation_manager, trust_manager):
        """Escalation denied when there's no interaction history."""
        trust_manager._scores[("rajesh", "climate")] = 50.0

        result = escalation_manager.check_escalation("rajesh", "climate")

        assert result is None

    def test_escalation_approved_when_all_criteria_met(self, escalation_manager, trust_manager):
        """Escalation approved when score, window, and acceptance rate all meet criteria."""
        # Score 50 -> Tier 3. With 7+ days history and 90% acceptance, should escalate to tier 4.
        trust_manager._scores[("rajesh", "climate")] = 50.0

        key = ("rajesh", "climate")
        now = datetime.now(timezone.utc)
        escalation_manager._interaction_history[key] = [
            {"timestamp": now - timedelta(days=9), "accepted": True},
            {"timestamp": now - timedelta(days=8), "accepted": True},
            {"timestamp": now - timedelta(days=7), "accepted": True},
            {"timestamp": now - timedelta(days=6), "accepted": True},
            {"timestamp": now - timedelta(days=5), "accepted": True},
            {"timestamp": now - timedelta(days=4), "accepted": True},
            {"timestamp": now - timedelta(days=3), "accepted": True},
            {"timestamp": now - timedelta(days=2), "accepted": True},
            {"timestamp": now - timedelta(days=1), "accepted": True},
            {"timestamp": now - timedelta(hours=12), "accepted": False},
        ]

        result = escalation_manager.check_escalation("rajesh", "climate")

        assert result is not None
        assert result["member"] == "rajesh"
        assert result["category"] == "climate"
        assert result["from_tier"] == 3
        assert result["to_tier"] == 4
        assert result["score"] == 50.0
        assert result["acceptance_rate"] == 0.9

    def test_escalation_case_insensitive_member(self, escalation_manager, trust_manager):
        """Escalation check is case-insensitive for member name."""
        trust_manager._scores[("rajesh", "climate")] = 50.0

        key = ("rajesh", "climate")
        now = datetime.now(timezone.utc)
        escalation_manager._interaction_history[key] = [
            {"timestamp": now - timedelta(days=10), "accepted": True},
            {"timestamp": now - timedelta(days=8), "accepted": True},
            {"timestamp": now - timedelta(days=6), "accepted": True},
            {"timestamp": now - timedelta(days=4), "accepted": True},
            {"timestamp": now - timedelta(days=2), "accepted": True},
        ]

        # Check with uppercase - should still work
        result = escalation_manager.check_escalation("Rajesh", "climate")

        assert result is not None
        assert result["from_tier"] == 3
        assert result["to_tier"] == 4


class TestApplyDecay:
    """Tests for apply_decay() logic."""

    def test_decay_reduces_scores(self, escalation_manager, trust_manager):
        """Decay reduces trust scores by the configured amount."""
        trust_manager._scores[("rajesh", "climate")] = 50.0
        trust_manager._scores[("priya", "lighting")] = 30.0

        decayed = escalation_manager.apply_decay()

        assert "rajesh#climate" in decayed
        assert "priya#lighting" in decayed
        # Default decay is 0.5 per day
        assert decayed["rajesh#climate"] == 49.5
        assert decayed["priya#lighting"] == 29.5

    def test_decay_does_not_go_below_zero(self, escalation_manager, trust_manager):
        """Decay never makes a score go below 0."""
        trust_manager._scores[("rajesh", "climate")] = 0.2

        decayed = escalation_manager.apply_decay()

        # 0.2 - 0.5 = -0.3, but floored at 0
        assert decayed["rajesh#climate"] == 0.0
        assert trust_manager.get_score("rajesh", "climate") == 0.0

    def test_decay_skips_zero_scores(self, escalation_manager, trust_manager):
        """Decay does not affect scores already at 0."""
        # All scores start at 0 by default
        decayed = escalation_manager.apply_decay()

        assert decayed == {}

    def test_decay_returns_only_changed_scores(self, escalation_manager, trust_manager):
        """Decay returns only pairs whose scores actually changed."""
        trust_manager._scores[("rajesh", "climate")] = 10.0
        # All other scores are 0, they shouldn't appear in result

        decayed = escalation_manager.apply_decay()

        assert len(decayed) == 1
        assert "rajesh#climate" in decayed


class TestRecordInteraction:
    """Tests for record_interaction()."""

    def test_record_interaction_stores_accepted(self, escalation_manager):
        """Recording an accepted interaction stores it correctly."""
        escalation_manager.record_interaction("rajesh", "climate", accepted=True)

        key = ("rajesh", "climate")
        assert len(escalation_manager._interaction_history[key]) == 1
        assert escalation_manager._interaction_history[key][0]["accepted"] is True

    def test_record_interaction_stores_rejected(self, escalation_manager):
        """Recording a rejected interaction stores it correctly."""
        escalation_manager.record_interaction("rajesh", "climate", accepted=False)

        key = ("rajesh", "climate")
        assert len(escalation_manager._interaction_history[key]) == 1
        assert escalation_manager._interaction_history[key][0]["accepted"] is False

    def test_record_interaction_case_insensitive(self, escalation_manager):
        """Member name is stored in lowercase."""
        escalation_manager.record_interaction("Rajesh", "climate", accepted=True)

        key = ("rajesh", "climate")
        assert key in escalation_manager._interaction_history
        assert len(escalation_manager._interaction_history[key]) == 1

    def test_record_multiple_interactions(self, escalation_manager):
        """Multiple interactions accumulate for the same pair."""
        escalation_manager.record_interaction("rajesh", "climate", accepted=True)
        escalation_manager.record_interaction("rajesh", "climate", accepted=False)
        escalation_manager.record_interaction("rajesh", "climate", accepted=True)

        key = ("rajesh", "climate")
        assert len(escalation_manager._interaction_history[key]) == 3


class TestImmediateDeescalation:
    """Tests for immediate_deescalation()."""

    def test_deescalation_reports_current_state(self, escalation_manager, trust_manager):
        """De-escalation reports the current tier and score after override."""
        trust_manager._scores[("rajesh", "climate")] = 35.0

        result = escalation_manager.immediate_deescalation("rajesh", "climate")

        assert result["member"] == "rajesh"
        assert result["category"] == "climate"
        assert result["current_tier"] == 2  # 35 -> Tier 2
        assert result["score"] == 35.0
        assert result["reason"] == "immediate_deescalation_on_override"

    def test_deescalation_after_override_from_tier_3(self, escalation_manager, trust_manager):
        """Override that drops from tier 3 boundary reports correctly."""
        # Score was at 46 (tier 3 boundary), override reduces by 15 -> 31 (tier 2)
        trust_manager._scores[("priya", "security")] = 31.0

        result = escalation_manager.immediate_deescalation("priya", "security")

        assert result["current_tier"] == 2
        assert result["score"] == 31.0
