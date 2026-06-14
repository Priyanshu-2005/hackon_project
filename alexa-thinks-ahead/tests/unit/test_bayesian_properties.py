"""Property-based tests for Bayesian preference updater.

Uses hypothesis to verify that posterior variance is always less than
prior variance for any valid prior and observation inputs.

**Validates: Requirement 6.2**
"""

from hypothesis import given, settings
from hypothesis.strategies import floats

from src.learning.bayesian import BayesianUpdater


class TestBayesianProperties:
    """Property 5: Bayesian Update Variance Reduction."""

    @given(
        prior_mean=floats(
            min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False
        ),
        prior_variance=floats(
            min_value=0.001, max_value=1000, allow_nan=False, allow_infinity=False
        ),
        observation=floats(
            min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=200)
    def test_posterior_variance_always_less_than_prior(
        self, prior_mean, prior_variance, observation
    ):
        """Property 5: posterior variance < prior variance for any valid inputs.

        **Validates: Requirements 6.2**
        """
        updater = BayesianUpdater(observation_noise=1.0)
        _, posterior_variance = updater.update(prior_mean, prior_variance, observation)
        assert posterior_variance < prior_variance
        assert posterior_variance > 0
