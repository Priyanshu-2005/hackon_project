"""Property-based tests for tier logic.

Validates:
- Property 2: Tier Monotonicity with Score
- Property 9: Tier Permission Consistency
- Property 10: De-escalation Immediacy on Override

Validates: Requirements 5.2, 5.5, 5.7
"""

from hypothesis import given, settings
from hypothesis.strategies import floats, integers

from src.autonomy.tiers import TierManager
from src.autonomy.trust import TrustScoreManager
from src.devices.registry import DeviceRegistry
from src.models.device import DeviceCommand


class TestTierProperties:
    """Property-based tests for tier determination and permission logic."""

    @given(
        score_a=floats(min_value=0.0, max_value=100.0, allow_nan=False),
        score_b=floats(min_value=0.0, max_value=100.0, allow_nan=False),
    )
    @settings(max_examples=200)
    def test_tier_monotonicity(self, score_a, score_b):
        """Property 2: Tier Monotonicity with Score - higher score never maps to lower tier.

        If score_a <= score_b then determine_tier(score_a) <= determine_tier(score_b).

        Validates: Requirements 5.2
        """
        trust = TrustScoreManager()
        tm = TierManager(trust_manager=trust, device_registry=DeviceRegistry())
        tier_a = tm.determine_tier(score_a)
        tier_b = tm.determine_tier(score_b)
        if score_a <= score_b:
            assert tier_a <= tier_b, (
                f"Monotonicity violated: score_a={score_a} -> tier {tier_a}, "
                f"score_b={score_b} -> tier {tier_b}"
            )

    @given(
        score=floats(min_value=0.0, max_value=100.0, allow_nan=False),
        tier_required=integers(min_value=1, max_value=5),
    )
    @settings(max_examples=200)
    def test_permission_consistency(self, score, tier_required):
        """Property 9: Tier Permission Consistency - permitted iff member_tier >= required_tier.

        For any score and tier_required, the permission decision must be
        exactly (determine_tier(score) >= tier_required).

        Validates: Requirements 5.5
        """
        trust = TrustScoreManager()
        trust._scores[("rajesh", "climate")] = score
        tm = TierManager(trust_manager=trust, device_registry=DeviceRegistry())

        action = DeviceCommand(
            command_id="test",
            device_id="living_room_ac",
            action="test",
            parameters={},
            source="autonomy",
            tier_required=tier_required,
            reversible=True,
        )
        decision = tm.check_permission("rajesh", action)
        current_tier = tm.determine_tier(score)

        assert decision.permitted == (current_tier >= tier_required), (
            f"Permission inconsistency: score={score}, current_tier={current_tier}, "
            f"tier_required={tier_required}, permitted={decision.permitted}"
        )

    @given(score=floats(min_value=0.0, max_value=100.0, allow_nan=False))
    @settings(max_examples=200)
    def test_de_escalation_on_override(self, score):
        """Property 10: De-escalation Immediacy on Override - tier never increases on override.

        After recording an override, the new tier must be <= the tier before the override.

        Validates: Requirements 5.7
        """
        trust = TrustScoreManager()
        trust._scores[("rajesh", "climate")] = score
        tm = TierManager(trust_manager=trust, device_registry=DeviceRegistry())

        tier_before = tm.determine_tier(score)
        trust.record_override("rajesh", "climate")
        new_score = trust.get_score("rajesh", "climate")
        tier_after = tm.determine_tier(new_score)

        assert tier_after <= tier_before, (
            f"De-escalation violated: score={score} -> tier_before={tier_before}, "
            f"new_score={new_score} -> tier_after={tier_after}"
        )
