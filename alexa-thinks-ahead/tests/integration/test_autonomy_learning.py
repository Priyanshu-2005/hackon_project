"""Integration tests for autonomy + learning loop.

Tests the interaction between the autonomy engine (trust scoring, tier management)
and the learning engine (Bayesian updates, personalization).

Requirements: 5.3, 5.4, 5.6, 6.2
"""

from datetime import datetime, timezone

import pytest

from src.autonomy.engine import AutonomyEngine
from src.autonomy.trust import TrustScoreManager
from src.learning.bayesian import BayesianUpdater
from src.learning.engine import LearningEngine
from src.learning.feedback import FeedbackCollector
from src.models.learning import FeedbackEvent


class TestAutonomyTrustEscalation:
    """Test acceptance → trust increase → tier escalation flow."""

    def test_acceptance_increases_trust(self):
        """Repeated acceptances increase trust score."""
        engine = AutonomyEngine()
        member = "rajesh"
        category = "climate"

        initial_score = engine.trust_manager.get_score(member, category)
        assert initial_score == 0.0

        # Record 5 acceptances
        for _ in range(5):
            engine.record_acceptance(member, category)

        new_score = engine.trust_manager.get_score(member, category)
        assert new_score > initial_score
        assert new_score == 25.0  # 5 acceptances × 5 points each

    def test_trust_increase_leads_to_tier_escalation(self):
        """Sufficient trust increases lead to higher tier."""
        engine = AutonomyEngine()
        member = "priya"
        category = "lighting"

        # Initially at tier 1 (score = 0)
        initial_tier = engine.tier_manager.determine_tier(
            engine.trust_manager.get_score(member, category)
        )
        assert initial_tier == 1

        # Record enough acceptances to reach tier 2 (score > 20)
        for _ in range(5):
            engine.record_acceptance(member, category)

        score = engine.trust_manager.get_score(member, category)
        tier = engine.tier_manager.determine_tier(score)
        assert score == 25.0
        assert tier == 2

    def test_sustained_acceptance_reaches_tier_3(self):
        """Continued acceptances escalate to tier 3."""
        engine = AutonomyEngine()
        member = "rajesh"
        category = "climate"

        # Need score > 45 for tier 3: 10 acceptances = 50
        for _ in range(10):
            engine.record_acceptance(member, category)

        score = engine.trust_manager.get_score(member, category)
        tier = engine.tier_manager.determine_tier(score)
        assert score == 50.0
        assert tier == 3

    def test_tier_config_reflects_all_members(self):
        """get_tier_config returns tiers for all member-category pairs."""
        engine = AutonomyEngine()
        engine.record_acceptance("rajesh", "climate")

        config = engine.get_tier_config()
        assert "rajesh_climate" in config
        # All other pairs should be at tier 1 (score 0)
        assert config.get("priya_lighting") == 1


class TestAutonomyTrustDeescalation:
    """Test override → trust decrease → tier de-escalation flow."""

    def test_override_decreases_trust(self):
        """A single override decreases trust by 15 points."""
        engine = AutonomyEngine()
        member = "rajesh"
        category = "climate"

        # First build up some trust
        for _ in range(8):
            engine.record_acceptance(member, category)

        score_before = engine.trust_manager.get_score(member, category)
        assert score_before == 40.0

        # Override drops 15 points
        engine.record_override(member, category)
        score_after = engine.trust_manager.get_score(member, category)
        assert score_after == 25.0

    def test_override_causes_tier_drop(self):
        """Override can cause immediate tier de-escalation."""
        engine = AutonomyEngine()
        member = "priya"
        category = "security"

        # Build to tier 2 (score=25)
        for _ in range(5):
            engine.record_acceptance(member, category)

        tier_before = engine.tier_manager.determine_tier(
            engine.trust_manager.get_score(member, category)
        )
        assert tier_before == 2

        # Override drops to 10 → tier 1
        engine.record_override(member, category)
        score = engine.trust_manager.get_score(member, category)
        tier_after = engine.tier_manager.determine_tier(score)
        assert score == 10.0
        assert tier_after == 1

    def test_override_at_zero_stays_at_zero(self):
        """Override on zero trust stays at floor (0)."""
        engine = AutonomyEngine()
        engine.record_override("arjun", "entertainment")

        score = engine.trust_manager.get_score("arjun", "entertainment")
        assert score == 0.0

    def test_multiple_overrides_compound(self):
        """Multiple overrides compound the trust decrease."""
        engine = AutonomyEngine()
        member = "rajesh"
        category = "climate"

        # Build to 50
        for _ in range(10):
            engine.record_acceptance(member, category)

        # Two overrides: 50 → 35 → 20
        engine.record_override(member, category)
        engine.record_override(member, category)

        score = engine.trust_manager.get_score(member, category)
        assert score == 20.0
        tier = engine.tier_manager.determine_tier(score)
        assert tier == 1  # 0-20 = tier 1


class TestAutonomyInteractionLog:
    """Test that interaction log is maintained for learning engine."""

    def test_interactions_logged(self):
        """Acceptances and overrides are recorded in interaction log."""
        engine = AutonomyEngine()

        engine.record_acceptance("rajesh", "climate")
        engine.record_override("priya", "lighting")
        engine.record_acceptance("arjun", "entertainment")

        log = engine.get_interaction_log()
        assert len(log) == 3
        assert log[0]["member"] == "rajesh"
        assert log[0]["accepted"] is True
        assert log[1]["member"] == "priya"
        assert log[1]["accepted"] is False


class TestLearningFeedbackLoop:
    """Test feedback → Bayesian update → improved prediction flow."""

    def test_feedback_updates_preference_distribution(self):
        """Processing feedback updates the preference distribution."""
        learning = LearningEngine()

        feedback = FeedbackEvent(
            event_id="fb_001",
            member="rajesh",
            feedback_type="explicit_rating",
            context={"category": "climate"},
            signal_value=0.8,
            timestamp=datetime.now(timezone.utc),
        )

        learning.process_feedback(feedback)

        pref = learning.get_preference("rajesh#explicit_rating")
        assert pref is not None
        assert pref.sample_count == 1
        # After one positive observation, mean should shift toward positive
        assert pref.mean > 0.0

    def test_multiple_feedback_reduces_variance(self):
        """Multiple feedback events reduce variance (more certainty)."""
        learning = LearningEngine()

        for i in range(5):
            feedback = FeedbackEvent(
                event_id=f"fb_{i:03d}",
                member="priya",
                feedback_type="explicit_rating",
                context={},
                signal_value=0.7,
                timestamp=datetime.now(timezone.utc),
            )
            learning.process_feedback(feedback)

        pref = learning.get_preference("priya#explicit_rating")
        assert pref is not None
        assert pref.sample_count == 5
        # Variance should be less than initial (10.0)
        assert pref.variance < 10.0

    def test_personalization_index_increases(self):
        """Personalization index increases with more feedback."""
        learning = LearningEngine()

        initial_index = learning.get_personalization_index("rajesh")
        assert initial_index == 0.0

        # Process multiple feedback events
        for i in range(10):
            feedback = FeedbackEvent(
                event_id=f"fb_{i:03d}",
                member="rajesh",
                feedback_type="override",
                context={},
                signal_value=-0.5,
                timestamp=datetime.now(timezone.utc),
            )
            learning.process_feedback(feedback)

        new_index = learning.get_personalization_index("rajesh")
        assert new_index > initial_index
        assert new_index == pytest.approx(0.1, abs=0.01)  # 10/100

    def test_predict_preference_returns_predictions(self):
        """After feedback, predict_preference returns meaningful predictions."""
        learning = LearningEngine()

        # Build up some preferences
        for val in [0.8, 0.7, 0.9, 0.75, 0.85]:
            feedback = FeedbackEvent(
                event_id=f"fb_{val}",
                member="rajesh",
                feedback_type="temperature_pref",
                context={},
                signal_value=val,
                timestamp=datetime.now(timezone.utc),
            )
            learning.process_feedback(feedback)

        predictions = learning.predict_preference(context={})
        assert "rajesh#temperature_pref" in predictions
        # Prediction should be in the vicinity of the feedback values
        pred_val = predictions["rajesh#temperature_pref"]
        assert 0.5 < pred_val < 1.0

    def test_bayesian_update_correctness(self):
        """Verify Bayesian update reduces variance monotonically."""
        updater = BayesianUpdater()
        from src.models.learning import PreferenceDistribution

        dist = PreferenceDistribution(
            key="test",
            mean=0.0,
            variance=10.0,
            sample_count=0,
            last_updated=datetime.now(timezone.utc),
        )

        prev_variance = dist.variance
        for obs in [0.5, 0.6, 0.4, 0.55, 0.5]:
            dist = updater.update_distribution(dist, obs)
            assert dist.variance < prev_variance
            prev_variance = dist.variance

        # After 5 observations, variance should be significantly less
        assert dist.variance < 5.0
