"""Unit tests for TrustScoreManager.

Tests:
- Initial scores are 0
- Acceptance increases score
- Override decreases score
- Score never exceeds 100
- Score never goes below 0
- DynamoDB persistence with member_category partition key
"""

import pytest
from unittest.mock import MagicMock, patch

from src.autonomy.trust import TrustScoreManager
from src.utils.constants import FAMILY_MEMBERS, DEVICE_CATEGORIES


class TestTrustScoreManagerInitialization:
    """Tests for initial state of TrustScoreManager."""

    def test_all_scores_initialized_at_zero(self):
        """All member-category pairs should start at 0."""
        manager = TrustScoreManager()
        for member in FAMILY_MEMBERS:
            for category in DEVICE_CATEGORIES:
                assert manager.get_score(member, category) == 0.0

    def test_correct_number_of_pairs_initialized(self):
        """Should have 6 members × 8 categories = 48 pairs."""
        manager = TrustScoreManager()
        assert len(manager._scores) == 6 * 8

    def test_get_score_case_insensitive(self):
        """Member lookup should be case-insensitive."""
        manager = TrustScoreManager()
        assert manager.get_score("Rajesh", "climate") == 0.0
        assert manager.get_score("RAJESH", "climate") == 0.0
        assert manager.get_score("rajesh", "climate") == 0.0


class TestRecordAcceptance:
    """Tests for record_acceptance method."""

    def test_acceptance_increases_score(self):
        """Acceptance should increase the trust score."""
        manager = TrustScoreManager()
        new_score = manager.record_acceptance("rajesh", "climate")
        assert new_score == 5.0

    def test_acceptance_increases_by_5(self):
        """Default acceptance delta is 5 points."""
        manager = TrustScoreManager()
        manager.record_acceptance("rajesh", "climate")
        assert manager.get_score("rajesh", "climate") == 5.0

    def test_multiple_acceptances_accumulate(self):
        """Multiple acceptances should accumulate."""
        manager = TrustScoreManager()
        manager.record_acceptance("rajesh", "climate")
        manager.record_acceptance("rajesh", "climate")
        manager.record_acceptance("rajesh", "climate")
        assert manager.get_score("rajesh", "climate") == 15.0

    def test_acceptance_never_exceeds_100(self):
        """Score should never exceed 100 after acceptance."""
        manager = TrustScoreManager()
        # Manually set score to 98
        manager._scores[("rajesh", "climate")] = 98.0
        new_score = manager.record_acceptance("rajesh", "climate")
        assert new_score == 100.0

    def test_acceptance_at_100_stays_at_100(self):
        """Score at 100 should not change on acceptance."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 100.0
        new_score = manager.record_acceptance("rajesh", "climate")
        assert new_score == 100.0

    def test_acceptance_case_insensitive_member(self):
        """Acceptance should work with any case for member name."""
        manager = TrustScoreManager()
        manager.record_acceptance("Rajesh", "climate")
        assert manager.get_score("rajesh", "climate") == 5.0

    def test_acceptance_does_not_affect_other_pairs(self):
        """Acceptance for one pair should not affect others."""
        manager = TrustScoreManager()
        manager.record_acceptance("rajesh", "climate")
        assert manager.get_score("rajesh", "lighting") == 0.0
        assert manager.get_score("priya", "climate") == 0.0


class TestRecordOverride:
    """Tests for record_override method."""

    def test_override_decreases_score(self):
        """Override should decrease the trust score."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 50.0
        new_score = manager.record_override("rajesh", "climate")
        assert new_score == 35.0

    def test_override_decreases_by_15(self):
        """Default override penalty is 15 points."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 50.0
        manager.record_override("rajesh", "climate")
        assert manager.get_score("rajesh", "climate") == 35.0

    def test_override_never_goes_below_zero(self):
        """Score should never go below 0 after override."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 10.0
        new_score = manager.record_override("rajesh", "climate")
        assert new_score == 0.0

    def test_override_at_zero_stays_at_zero(self):
        """Score at 0 should stay at 0 on override."""
        manager = TrustScoreManager()
        new_score = manager.record_override("rajesh", "climate")
        assert new_score == 0.0

    def test_override_from_small_value_floors_at_zero(self):
        """Score below penalty amount should floor at 0."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 5.0
        new_score = manager.record_override("rajesh", "climate")
        assert new_score == 0.0

    def test_override_case_insensitive_member(self):
        """Override should work with any case for member name."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 50.0
        manager.record_override("Rajesh", "climate")
        assert manager.get_score("rajesh", "climate") == 35.0

    def test_override_does_not_affect_other_pairs(self):
        """Override for one pair should not affect others."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 50.0
        manager._scores[("rajesh", "lighting")] = 50.0
        manager.record_override("rajesh", "climate")
        assert manager.get_score("rajesh", "lighting") == 50.0


class TestGetTrustScore:
    """Tests for get_trust_score method returning TrustScore objects."""

    def test_returns_trust_score_object(self):
        """Should return a TrustScore dataclass."""
        manager = TrustScoreManager()
        ts = manager.get_trust_score("rajesh", "climate")
        assert ts.member == "rajesh"
        assert ts.category.value == "climate"
        assert ts.score == 0.0
        assert ts.current_tier == 1

    def test_tier_calculation_tier_1(self):
        """Score 0-20 should map to Tier 1."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 15.0
        ts = manager.get_trust_score("rajesh", "climate")
        assert ts.current_tier == 1

    def test_tier_calculation_tier_2(self):
        """Score 21-45 should map to Tier 2."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 30.0
        ts = manager.get_trust_score("rajesh", "climate")
        assert ts.current_tier == 2

    def test_tier_calculation_tier_3(self):
        """Score 46-70 should map to Tier 3."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 60.0
        ts = manager.get_trust_score("rajesh", "climate")
        assert ts.current_tier == 3

    def test_tier_calculation_tier_4(self):
        """Score 71-90 should map to Tier 4."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 80.0
        ts = manager.get_trust_score("rajesh", "climate")
        assert ts.current_tier == 4

    def test_tier_calculation_tier_5(self):
        """Score 91-100 should map to Tier 5."""
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = 95.0
        ts = manager.get_trust_score("rajesh", "climate")
        assert ts.current_tier == 5


class TestDynamoDBPersistence:
    """Tests for DynamoDB persistence."""

    def test_persist_on_acceptance(self):
        """Acceptance should persist the score to DynamoDB."""
        mock_table = MagicMock()
        manager = TrustScoreManager(table=mock_table)
        manager.record_acceptance("rajesh", "climate")
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args[1]["Item"]
        assert item["member_category"] == "rajesh#climate"
        assert float(item["score"]) == 5.0

    def test_persist_on_override(self):
        """Override should persist the score to DynamoDB."""
        mock_table = MagicMock()
        manager = TrustScoreManager(table=mock_table)
        manager._scores[("rajesh", "climate")] = 50.0
        manager.record_override("rajesh", "climate")
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args
        item = call_args[1]["Item"]
        assert item["member_category"] == "rajesh#climate"
        assert float(item["score"]) == 35.0

    def test_no_persist_without_table(self):
        """Without a table, operations should still work (no-op persist)."""
        manager = TrustScoreManager(table=None)
        # Should not raise
        new_score = manager.record_acceptance("rajesh", "climate")
        assert new_score == 5.0

    def test_persist_failure_does_not_crash(self):
        """DynamoDB errors should be logged but not crash the system."""
        mock_table = MagicMock()
        mock_table.put_item.side_effect = Exception("DynamoDB throttle")
        manager = TrustScoreManager(table=mock_table)
        # Should not raise
        new_score = manager.record_acceptance("rajesh", "climate")
        assert new_score == 5.0

    def test_load_scores_from_dynamo(self):
        """Should load scores from DynamoDB scan."""
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "Items": [
                {
                    "member": "rajesh",
                    "category": "climate",
                    "score": "42.0",
                    "member_category": "rajesh#climate",
                }
            ]
        }
        manager = TrustScoreManager(table=mock_table)
        manager.load_scores_from_dynamo()
        assert manager.get_score("rajesh", "climate") == 42.0
