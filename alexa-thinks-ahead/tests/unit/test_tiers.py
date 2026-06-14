"""Unit tests for tier determination and permission checks.

Tests:
- Tier determination at boundaries
- Permission granted when tier >= required
- Permission denied when tier < required
"""

import pytest

from src.autonomy.tiers import TierManager
from src.autonomy.trust import TrustScoreManager
from src.devices.registry import DeviceRegistry
from src.models.device import DeviceCommand


@pytest.fixture
def device_registry():
    """Create a DeviceRegistry with default configs."""
    return DeviceRegistry()


@pytest.fixture
def trust_manager():
    """Create a TrustScoreManager without DynamoDB."""
    return TrustScoreManager(table=None)


@pytest.fixture
def tier_manager(trust_manager, device_registry):
    """Create a TierManager with trust manager and device registry."""
    return TierManager(
        trust_manager=trust_manager,
        device_registry=device_registry,
    )


def make_command(device_id: str, tier_required: int) -> DeviceCommand:
    """Helper to create a DeviceCommand for testing."""
    return DeviceCommand(
        command_id="test_cmd_1",
        device_id=device_id,
        action="set_temperature",
        parameters={"target_temp": 24},
        source="autonomy",
        tier_required=tier_required,
        reversible=True,
    )


class TestDetermineTier:
    """Test tier determination from trust scores."""

    def test_tier_1_at_score_0(self, tier_manager):
        """Score 0 maps to tier 1."""
        assert tier_manager.determine_tier(0.0) == 1

    def test_tier_1_at_score_20(self, tier_manager):
        """Score 20 maps to tier 1 (boundary: 0-20)."""
        assert tier_manager.determine_tier(20.0) == 1

    def test_tier_2_at_score_21(self, tier_manager):
        """Score 21 maps to tier 2 (boundary: 21-45)."""
        assert tier_manager.determine_tier(21.0) == 2

    def test_tier_2_at_score_45(self, tier_manager):
        """Score 45 maps to tier 2."""
        assert tier_manager.determine_tier(45.0) == 2

    def test_tier_3_at_score_46(self, tier_manager):
        """Score 46 maps to tier 3 (boundary: 46-70)."""
        assert tier_manager.determine_tier(46.0) == 3

    def test_tier_3_at_score_70(self, tier_manager):
        """Score 70 maps to tier 3."""
        assert tier_manager.determine_tier(70.0) == 3

    def test_tier_4_at_score_71(self, tier_manager):
        """Score 71 maps to tier 4 (boundary: 71-90)."""
        assert tier_manager.determine_tier(71.0) == 4

    def test_tier_4_at_score_90(self, tier_manager):
        """Score 90 maps to tier 4."""
        assert tier_manager.determine_tier(90.0) == 4

    def test_tier_5_at_score_91(self, tier_manager):
        """Score 91 maps to tier 5 (boundary: 91-100)."""
        assert tier_manager.determine_tier(91.0) == 5

    def test_tier_5_at_score_100(self, tier_manager):
        """Score 100 maps to tier 5."""
        assert tier_manager.determine_tier(100.0) == 5

    def test_tier_mid_range_score_50(self, tier_manager):
        """Score 50 maps to tier 3."""
        assert tier_manager.determine_tier(50.0) == 3

    def test_tier_mid_range_score_80(self, tier_manager):
        """Score 80 maps to tier 4."""
        assert tier_manager.determine_tier(80.0) == 4


class TestCheckPermissionGranted:
    """Test permission is granted when member tier >= required tier."""

    def test_permission_granted_tier_equals_required(self, tier_manager, trust_manager):
        """Permission granted when member tier == required tier."""
        # Set trust score to 50 -> tier 3
        trust_manager._scores[("rajesh", "climate")] = 50.0

        action = make_command("living_room_ac", tier_required=3)
        decision = tier_manager.check_permission("rajesh", action)

        assert decision.permitted is True
        assert decision.current_tier == 3
        assert decision.required_tier == 3

    def test_permission_granted_tier_above_required(self, tier_manager, trust_manager):
        """Permission granted when member tier > required tier."""
        # Set trust score to 95 -> tier 5
        trust_manager._scores[("priya", "lighting")] = 95.0

        action = make_command("smart_lights", tier_required=2)
        decision = tier_manager.check_permission("priya", action)

        assert decision.permitted is True
        assert decision.current_tier == 5
        assert decision.required_tier == 2

    def test_permission_granted_tier_1_action(self, tier_manager):
        """Permission granted for tier 1 action (everyone has at least tier 1)."""
        # Default score is 0 -> tier 1
        action = make_command("living_room_ac", tier_required=1)
        decision = tier_manager.check_permission("arjun", action)

        assert decision.permitted is True
        assert decision.current_tier == 1
        assert decision.required_tier == 1


class TestCheckPermissionDenied:
    """Test permission is denied when member tier < required tier."""

    def test_permission_denied_tier_below_required(self, tier_manager):
        """Permission denied when member tier < required tier."""
        # Default score is 0 -> tier 1, action requires tier 3
        action = make_command("living_room_ac", tier_required=3)
        decision = tier_manager.check_permission("rajesh", action)

        assert decision.permitted is False
        assert decision.current_tier == 1
        assert decision.required_tier == 3

    def test_permission_denied_high_tier_required(self, tier_manager, trust_manager):
        """Permission denied when tier 5 required but member at tier 4."""
        # Set score to 80 -> tier 4
        trust_manager._scores[("rajesh", "security")] = 80.0

        action = make_command("smart_lock", tier_required=5)
        decision = tier_manager.check_permission("rajesh", action)

        assert decision.permitted is False
        assert decision.current_tier == 4
        assert decision.required_tier == 5

    def test_permission_denied_tier_2_required_with_low_score(
        self, tier_manager
    ):
        """Permission denied when tier 2 required but member at tier 1."""
        # Default score is 0 -> tier 1
        action = make_command("smart_lights", tier_required=2)
        decision = tier_manager.check_permission("ananya", action)

        assert decision.permitted is False
        assert decision.current_tier == 1
        assert decision.required_tier == 2


class TestTierDecisionDetails:
    """Test TierDecision contains correct metadata."""

    def test_decision_contains_action(self, tier_manager):
        """TierDecision should contain the original action."""
        action = make_command("living_room_ac", tier_required=1)
        decision = tier_manager.check_permission("rajesh", action)

        assert decision.action is action

    def test_decision_reason_not_empty(self, tier_manager):
        """TierDecision reason should be non-empty."""
        action = make_command("living_room_ac", tier_required=1)
        decision = tier_manager.check_permission("rajesh", action)

        assert decision.reason
        assert len(decision.reason) > 0

    def test_requires_confirmation_for_tier_4_boundary(
        self, tier_manager, trust_manager
    ):
        """Requires confirmation when at tier 4 boundary for tier 4 action."""
        # Set score to 75 -> tier 4
        trust_manager._scores[("rajesh", "climate")] = 75.0

        action = make_command("living_room_ac", tier_required=4)
        decision = tier_manager.check_permission("rajesh", action)

        assert decision.permitted is True
        assert decision.requires_confirmation is True

    def test_no_confirmation_when_above_required(self, tier_manager, trust_manager):
        """No confirmation needed when tier is well above required."""
        # Set score to 95 -> tier 5
        trust_manager._scores[("rajesh", "climate")] = 95.0

        action = make_command("living_room_ac", tier_required=3)
        decision = tier_manager.check_permission("rajesh", action)

        assert decision.permitted is True
        assert decision.requires_confirmation is False


class TestGetDeviceCategory:
    """Test device category lookup."""

    def test_known_device_returns_category(self, tier_manager):
        """Known device ID returns correct category."""
        assert tier_manager.get_device_category("living_room_ac") == "climate"
        assert tier_manager.get_device_category("smart_lights") == "lighting"
        assert tier_manager.get_device_category("smart_lock") == "security"

    def test_unknown_device_raises_error(self, tier_manager):
        """Unknown device ID raises ValueError."""
        with pytest.raises(ValueError, match="not found in device registry"):
            tier_manager.get_device_category("nonexistent_device")
