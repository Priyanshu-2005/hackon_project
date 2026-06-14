"""Unit tests for the SeasonalModel class."""

import pytest
from unittest.mock import patch

from src.learning.seasonal import SeasonalModel


class TestSeasonalModelRecordAndPredict:
    """Test recording observations and predicting within a season."""

    def test_predict_returns_none_for_unknown_key(self):
        """Predict returns None when no data has been recorded."""
        model = SeasonalModel()
        result = model.predict("ac_temperature", season="summer")
        assert result is None

    def test_record_first_observation_sets_mean(self):
        """First recorded value becomes the mean for that season."""
        model = SeasonalModel()
        model.record("ac_temperature", 24.0, season="summer")
        prediction = model.predict("ac_temperature", season="summer")
        assert prediction == 24.0

    def test_record_multiple_observations_updates_mean(self):
        """Multiple observations move the mean toward observed values."""
        model = SeasonalModel()
        model.record("ac_temperature", 24.0, season="summer")
        model.record("ac_temperature", 26.0, season="summer")
        prediction = model.predict("ac_temperature", season="summer")
        # Mean should shift toward 26 but not reach it fully
        assert 24.0 < prediction < 26.0

    def test_get_distribution_returns_full_object(self):
        """get_distribution returns the PreferenceDistribution dataclass."""
        model = SeasonalModel()
        model.record("brightness", 80.0, season="winter")
        dist = model.get_distribution("brightness", season="winter")
        assert dist is not None
        assert dist.key == "brightness"
        assert dist.mean == 80.0
        assert dist.sample_count == 1
        assert dist.variance == 10.0

    def test_get_distribution_returns_none_when_no_data(self):
        """get_distribution returns None for missing key/season combination."""
        model = SeasonalModel()
        dist = model.get_distribution("nonexistent", season="monsoon")
        assert dist is None


class TestSeasonalModelSeparateDistributions:
    """Test that different seasons maintain separate distributions."""

    def test_different_seasons_are_independent(self):
        """Recording in one season does not affect another."""
        model = SeasonalModel()
        model.record("ac_temperature", 24.0, season="summer")
        model.record("ac_temperature", 18.0, season="winter")

        summer_pred = model.predict("ac_temperature", season="summer")
        winter_pred = model.predict("ac_temperature", season="winter")

        assert summer_pred == 24.0
        assert winter_pred == 18.0

    def test_all_four_seasons_isolated(self):
        """Each of the four seasons maintains its own data."""
        model = SeasonalModel()
        values = {
            "summer": 26.0,
            "monsoon": 25.0,
            "autumn": 22.0,
            "winter": 18.0,
        }
        for season, value in values.items():
            model.record("ac_temperature", value, season=season)

        for season, expected in values.items():
            assert model.predict("ac_temperature", season=season) == expected

    def test_recording_does_not_create_data_in_other_seasons(self):
        """Recording in summer leaves monsoon/autumn/winter empty."""
        model = SeasonalModel()
        model.record("brightness", 90.0, season="summer")

        assert model.predict("brightness", season="monsoon") is None
        assert model.predict("brightness", season="autumn") is None
        assert model.predict("brightness", season="winter") is None


class TestSeasonalModelBlendPrediction:
    """Test blend_prediction with and without seasonal data."""

    def test_blend_falls_back_to_overall_when_no_seasonal_data(self):
        """Without seasonal data, returns overall_mean unchanged."""
        model = SeasonalModel()
        result = model.blend_prediction("ac_temperature", overall_mean=22.0, season="summer")
        assert result == 22.0

    def test_blend_uses_seventy_thirty_weighting(self):
        """With seasonal data, uses 70% seasonal + 30% overall."""
        model = SeasonalModel()
        model.record("ac_temperature", 26.0, season="summer")

        overall_mean = 22.0
        result = model.blend_prediction("ac_temperature", overall_mean, season="summer")

        expected = 0.7 * 26.0 + 0.3 * 22.0  # 18.2 + 6.6 = 24.8
        assert result == pytest.approx(expected)

    def test_blend_with_equal_seasonal_and_overall(self):
        """When seasonal and overall are the same, blend equals both."""
        model = SeasonalModel()
        model.record("ac_temperature", 24.0, season="monsoon")

        result = model.blend_prediction("ac_temperature", 24.0, season="monsoon")
        assert result == pytest.approx(24.0)

    @patch("src.learning.seasonal.get_current_season", return_value="winter")
    def test_uses_current_season_when_not_specified(self, mock_season):
        """When season is not passed, defaults to current season."""
        model = SeasonalModel()
        model.record("geyser_temp", 55.0, season="winter")

        # No season argument - should use current (winter via mock)
        result = model.predict("geyser_temp")
        assert result == 55.0

    @patch("src.learning.seasonal.get_current_season", return_value="summer")
    def test_blend_uses_current_season_by_default(self, mock_season):
        """blend_prediction uses current season when not specified."""
        model = SeasonalModel()
        model.record("ac_temperature", 26.0, season="summer")

        result = model.blend_prediction("ac_temperature", 22.0)
        expected = 0.7 * 26.0 + 0.3 * 22.0
        assert result == pytest.approx(expected)
