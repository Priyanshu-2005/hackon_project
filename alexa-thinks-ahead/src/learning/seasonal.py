"""Seasonal preference models for the continuous learning engine.

Maintains separate preference distributions per Indian season
(summer, monsoon, autumn, winter) and blends seasonal predictions
with overall preferences for more accurate personalization.
"""

from datetime import datetime, timezone
from typing import Dict, Optional

from src.learning.bayesian import BayesianUpdater
from src.models.learning import PreferenceDistribution
from src.utils.constants import SEASONS
from src.utils.time_utils import get_current_season


class SeasonalModel:
    """Maintains seasonal preference distributions.

    Each preference key has a separate distribution per season.
    Blends seasonal and overall preferences for predictions.
    """

    def __init__(self):
        self._updater = BayesianUpdater()
        # {season -> {preference_key -> PreferenceDistribution}}
        self._seasonal_prefs: Dict[str, Dict[str, PreferenceDistribution]] = {
            season: {} for season in SEASONS.keys()
        }

    def record(self, preference_key: str, value: float, season: Optional[str] = None) -> None:
        """Record an observation for the current (or specified) season.

        Args:
            preference_key: The preference identifier (e.g., 'ac_temperature').
            value: The observed value.
            season: Optional season override. Uses current season if not provided.
        """
        season = season or get_current_season()
        if preference_key not in self._seasonal_prefs[season]:
            self._seasonal_prefs[season][preference_key] = PreferenceDistribution(
                key=preference_key,
                mean=value,
                variance=10.0,
                sample_count=1,
                last_updated=datetime.now(timezone.utc),
            )
        else:
            dist = self._seasonal_prefs[season][preference_key]
            self._seasonal_prefs[season][preference_key] = self._updater.update_distribution(
                dist, value
            )

    def predict(self, preference_key: str, season: Optional[str] = None) -> Optional[float]:
        """Predict the preference value for the current season.

        Args:
            preference_key: The preference identifier.
            season: Optional season override. Uses current season if not provided.

        Returns:
            The predicted mean value, or None if no seasonal data exists.
        """
        season = season or get_current_season()
        dist = self._seasonal_prefs.get(season, {}).get(preference_key)
        if dist:
            return dist.mean
        return None

    def get_distribution(
        self, preference_key: str, season: Optional[str] = None
    ) -> Optional[PreferenceDistribution]:
        """Get the full distribution for a preference in a season.

        Args:
            preference_key: The preference identifier.
            season: Optional season override. Uses current season if not provided.

        Returns:
            The PreferenceDistribution, or None if no data exists for this key/season.
        """
        season = season or get_current_season()
        return self._seasonal_prefs.get(season, {}).get(preference_key)

    def blend_prediction(
        self, preference_key: str, overall_mean: float, season: Optional[str] = None
    ) -> float:
        """Blend seasonal prediction with overall preference.

        Uses 70% seasonal + 30% overall weighting when seasonal data exists.
        Falls back to overall when no seasonal data is available.

        Args:
            preference_key: The preference identifier.
            overall_mean: The overall (non-seasonal) mean preference value.
            season: Optional season override. Uses current season if not provided.

        Returns:
            The blended prediction value.
        """
        seasonal_pred = self.predict(preference_key, season)
        if seasonal_pred is None:
            return overall_mean
        return 0.7 * seasonal_pred + 0.3 * overall_mean
