"""Property-based tests for conflict resolution priority ordering.

Property 11: Conflict Resolution Priority Ordering
- Safety always wins over any lower priority on the same device.

**Validates: Requirements 3.4, 12.4**

Uses hypothesis to verify the invariant holds across all valid inputs
regardless of command order.
"""

from hypothesis import given, settings
from hypothesis.strategies import sampled_from

from src.context.conflicts import ConflictResolver


class TestConflictResolutionPriorityOrdering:
    """Property 11: Conflict Resolution Priority Ordering.

    For any two conflicting command dicts targeting the same device where one has
    "safety" priority_category and the other has any lower priority
    (elder_comfort, child_needs, efficiency), the safety-priority command SHALL
    always be selected.

    **Validates: Requirements 3.4, 12.4**
    """

    @given(
        lower_priority=sampled_from(["elder_comfort", "child_needs", "efficiency"]),
        action_safety=sampled_from(["lock", "arm", "alert"]),
        action_lower=sampled_from(["unlock", "disarm", "set_temp"]),
    )
    @settings(max_examples=100)
    def test_safety_always_wins_over_lower_priority(
        self, lower_priority, action_safety, action_lower
    ):
        """Safety command always wins when listed first (safety, then lower)."""
        resolver = ConflictResolver()
        commands = [
            {
                "device_id": "shared_device",
                "action": action_safety,
                "parameters": {},
                "priority_category": "safety",
            },
            {
                "device_id": "shared_device",
                "action": action_lower,
                "parameters": {},
                "priority_category": lower_priority,
            },
        ]
        result = resolver.resolve_command_conflicts(commands)
        assert len(result) == 1
        assert result[0]["priority_category"] == "safety"
        assert result[0]["action"] == action_safety

    @given(
        lower_priority=sampled_from(["elder_comfort", "child_needs", "efficiency"]),
        action_safety=sampled_from(["lock", "arm", "alert"]),
        action_lower=sampled_from(["unlock", "disarm", "set_temp"]),
    )
    @settings(max_examples=100)
    def test_safety_wins_regardless_of_input_order(
        self, lower_priority, action_safety, action_lower
    ):
        """Safety command wins even when lower-priority command is listed first (order independence)."""
        resolver = ConflictResolver()
        commands = [
            {
                "device_id": "shared_device",
                "action": action_lower,
                "parameters": {},
                "priority_category": lower_priority,
            },
            {
                "device_id": "shared_device",
                "action": action_safety,
                "parameters": {},
                "priority_category": "safety",
            },
        ]
        result = resolver.resolve_command_conflicts(commands)
        assert len(result) == 1
        assert result[0]["priority_category"] == "safety"
        assert result[0]["action"] == action_safety
