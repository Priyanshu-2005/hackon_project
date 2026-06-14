"""Bayesian preference updater using conjugate Gaussian update."""

from datetime import datetime, timezone
from typing import Tuple

from src.models.learning import PreferenceDistribution
from src.utils.config import get_config


class BayesianUpdater:
    """Bayesian preference updater using conjugate Gaussian update.

    Given a prior (mean, variance) and a new observation,
    computes the posterior distribution. Variance always decreases
    with more observations (becomes more certain).
    """

    def __init__(self, observation_noise: float = None):
        config = get_config()
        self.observation_noise = observation_noise or config.bayesian_observation_noise

    def update(
        self, prior_mean: float, prior_variance: float, observation: float
    ) -> Tuple[float, float]:
        """Perform Bayesian update.

        Uses conjugate Gaussian update:
            posterior_precision = prior_precision + observation_precision
            posterior_mean = (prior_precision * prior_mean + obs_precision * observation) / posterior_precision

        Preconditions:
            - prior_variance > 0
            - observation_noise > 0

        Postconditions:
            - posterior_variance < prior_variance
            - posterior_mean is between prior_mean and observation (weighted average)
            - posterior_variance > 0

        Returns:
            Tuple of (posterior_mean, posterior_variance)
        """
        precision_prior = 1.0 / prior_variance if prior_variance > 0 else 1.0
        precision_obs = 1.0 / self.observation_noise

        posterior_precision = precision_prior + precision_obs
        posterior_variance = 1.0 / posterior_precision
        posterior_mean = (
            precision_prior * prior_mean + precision_obs * observation
        ) / posterior_precision

        return posterior_mean, posterior_variance

    def update_distribution(
        self, dist: PreferenceDistribution, observation: float
    ) -> PreferenceDistribution:
        """Update a PreferenceDistribution with a new observation.

        Returns a new PreferenceDistribution with updated mean and variance.
        The sample_count is incremented and last_updated is set to now.
        """
        new_mean, new_variance = self.update(dist.mean, dist.variance, observation)

        return PreferenceDistribution(
            key=dist.key,
            mean=new_mean,
            variance=new_variance,
            sample_count=dist.sample_count + 1,
            last_updated=datetime.now(timezone.utc),
            seasonal_bias=dist.seasonal_bias,
        )
