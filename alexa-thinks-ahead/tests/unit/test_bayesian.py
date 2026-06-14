"""Unit tests for Bayesian preference updater."""

from datetime import datetime, timezone

import pytest

from src.learning.bayesian import BayesianUpdater
from src.models.learning import PreferenceDistribution


class TestBayesianUpdater:
    """Tests for BayesianUpdater class."""

    def setup_method(self):
        """Set up a BayesianUpdater with known observation noise."""
        self.updater = BayesianUpdater(observation_noise=1.0)

    def test_posterior_variance_less_than_prior_variance(self):
        """Posterior variance must always be less than prior variance."""
        prior_mean = 22.0
        prior_variance = 4.0
        observation = 24.0

        _, posterior_variance = self.updater.update(
            prior_mean, prior_variance, observation
        )

        assert posterior_variance < prior_variance

    def test_posterior_variance_less_than_prior_with_large_prior(self):
        """Posterior variance < prior variance even with very large prior variance."""
        prior_mean = 10.0
        prior_variance = 100.0
        observation = 15.0

        _, posterior_variance = self.updater.update(
            prior_mean, prior_variance, observation
        )

        assert posterior_variance < prior_variance

    def test_posterior_variance_less_than_prior_with_small_prior(self):
        """Posterior variance < prior variance even with small prior variance."""
        prior_mean = 5.0
        prior_variance = 0.5
        observation = 6.0

        _, posterior_variance = self.updater.update(
            prior_mean, prior_variance, observation
        )

        assert posterior_variance < prior_variance

    def test_posterior_mean_between_prior_and_observation(self):
        """Posterior mean should be between prior mean and observation."""
        prior_mean = 20.0
        prior_variance = 2.0
        observation = 26.0

        posterior_mean, _ = self.updater.update(
            prior_mean, prior_variance, observation
        )

        assert min(prior_mean, observation) <= posterior_mean <= max(
            prior_mean, observation
        )

    def test_posterior_mean_between_when_observation_less_than_prior(self):
        """Posterior mean between prior and observation when obs < prior."""
        prior_mean = 25.0
        prior_variance = 3.0
        observation = 18.0

        posterior_mean, _ = self.updater.update(
            prior_mean, prior_variance, observation
        )

        assert min(prior_mean, observation) <= posterior_mean <= max(
            prior_mean, observation
        )

    def test_multiple_updates_reduce_variance(self):
        """Multiple observations should continuously reduce variance."""
        prior_mean = 22.0
        prior_variance = 5.0
        observations = [23.0, 22.5, 23.5, 22.0, 24.0]

        current_mean = prior_mean
        current_variance = prior_variance

        for obs in observations:
            new_mean, new_variance = self.updater.update(
                current_mean, current_variance, obs
            )
            assert new_variance < current_variance
            current_mean = new_mean
            current_variance = new_variance

    def test_update_distribution_returns_updated_preference(self):
        """update_distribution should return a new PreferenceDistribution."""
        dist = PreferenceDistribution(
            key="rajesh#climate#temperature",
            mean=24.0,
            variance=3.0,
            sample_count=5,
            last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
            seasonal_bias={"summer": 0.5},
        )
        observation = 26.0

        result = self.updater.update_distribution(dist, observation)

        assert isinstance(result, PreferenceDistribution)
        assert result.key == dist.key
        assert result.variance < dist.variance
        assert result.sample_count == dist.sample_count + 1
        assert result.last_updated > dist.last_updated
        assert result.seasonal_bias == dist.seasonal_bias
        assert min(dist.mean, observation) <= result.mean <= max(
            dist.mean, observation
        )

    def test_update_distribution_preserves_key(self):
        """update_distribution should preserve the preference key."""
        dist = PreferenceDistribution(
            key="priya#lighting#brightness",
            mean=70.0,
            variance=10.0,
            sample_count=3,
            last_updated=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )

        result = self.updater.update_distribution(dist, 75.0)

        assert result.key == "priya#lighting#brightness"

    def test_posterior_variance_always_positive(self):
        """Posterior variance must always remain positive."""
        prior_mean = 0.0
        prior_variance = 0.01  # very small prior variance
        observation = 100.0

        _, posterior_variance = self.updater.update(
            prior_mean, prior_variance, observation
        )

        assert posterior_variance > 0

    def test_equal_prior_and_observation_same_mean(self):
        """When observation equals prior mean, posterior mean is unchanged."""
        prior_mean = 22.0
        prior_variance = 2.0
        observation = 22.0

        posterior_mean, _ = self.updater.update(
            prior_mean, prior_variance, observation
        )

        assert posterior_mean == pytest.approx(prior_mean)

    def test_custom_observation_noise(self):
        """Updater with different observation noise produces valid results."""
        updater_high_noise = BayesianUpdater(observation_noise=10.0)
        updater_low_noise = BayesianUpdater(observation_noise=0.1)

        prior_mean = 20.0
        prior_variance = 5.0
        observation = 30.0

        mean_high, var_high = updater_high_noise.update(
            prior_mean, prior_variance, observation
        )
        mean_low, var_low = updater_low_noise.update(
            prior_mean, prior_variance, observation
        )

        # Both should have reduced variance
        assert var_high < prior_variance
        assert var_low < prior_variance

        # Low noise should pull mean closer to observation
        assert abs(mean_low - observation) < abs(mean_high - observation)
