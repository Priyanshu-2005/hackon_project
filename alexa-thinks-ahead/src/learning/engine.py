"""Learning engine orchestrator for the continuous learning system.

Orchestrates: feedback collection → Bayesian update → seasonal model update.
Tracks personalization index per member with 90-day rolling window for
observation decay.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.learning.bayesian import BayesianUpdater
from src.learning.feedback import FeedbackCollector
from src.learning.seasonal import SeasonalModel
from src.models.learning import FeedbackEvent, PreferenceDistribution
from src.utils.config import get_config
from src.utils.constants import FAMILY_MEMBERS
from src.utils.time_utils import get_current_season


class LearningEngine:
    """Continuously refines predictions from feedback signals.

    Orchestrates: feedback collection → Bayesian update → seasonal model update.
    Tracks personalization index per member.

    The engine maintains preference distributions keyed by "{member}#{feedback_type}"
    and uses a 90-day rolling window for observation decay. Observations older than
    90 days are decayed by increasing variance (reducing their influence on predictions).
    """

    # Number of samples considered "fully personalized"
    FULL_PERSONALIZATION_SAMPLES: int = 100

    # Rolling window in days for observation relevance
    ROLLING_WINDOW_DAYS: int = 90

    def __init__(
        self,
        feedback_collector: Optional[FeedbackCollector] = None,
        bayesian_updater: Optional[BayesianUpdater] = None,
        seasonal_model: Optional[SeasonalModel] = None,
    ):
        """Initialize the LearningEngine.

        Args:
            feedback_collector: Optional FeedbackCollector instance for gathering feedback.
            bayesian_updater: Optional BayesianUpdater for preference updates.
            seasonal_model: Optional SeasonalModel for seasonal tracking.
        """
        self._config = get_config()
        self._updater = bayesian_updater or BayesianUpdater()
        self._seasonal = seasonal_model or SeasonalModel()
        self._feedback = feedback_collector

        # Overall preference distributions: {key -> PreferenceDistribution}
        self._preferences: Dict[str, PreferenceDistribution] = {}

        # Observation timestamps for rolling window decay: {key -> List[datetime]}
        self._observation_timestamps: Dict[str, List[datetime]] = {}

        # Personalization index per member: {member -> float 0.0..1.0}
        self._personalization_index: Dict[str, float] = {
            m: 0.0 for m in FAMILY_MEMBERS
        }

    def process_feedback(self, event: FeedbackEvent) -> None:
        """Process a feedback event through the learning pipeline.

        Pipeline:
            1. Update overall preference distribution via Bayesian inference
            2. Update seasonal model for current season
            3. Apply 90-day rolling window decay
            4. Update personalization index for the member

        Args:
            event: A FeedbackEvent with member, feedback_type, and signal_value.
        """
        key = f"{event.member.lower()}#{event.feedback_type}"

        # Get or create distribution
        if key not in self._preferences:
            self._preferences[key] = PreferenceDistribution(
                key=key,
                mean=0.0,
                variance=10.0,
                sample_count=0,
                last_updated=datetime.now(timezone.utc),
            )
            self._observation_timestamps[key] = []

        # 1. Bayesian update
        self._preferences[key] = self._updater.update_distribution(
            self._preferences[key], event.signal_value
        )

        # Record observation timestamp for rolling window
        timestamp = getattr(event, "timestamp", None) or datetime.now(timezone.utc)
        if key not in self._observation_timestamps:
            self._observation_timestamps[key] = []
        self._observation_timestamps[key].append(timestamp)

        # 2. Seasonal update
        self._seasonal.record(key, event.signal_value)

        # 3. Apply rolling window decay
        self._apply_rolling_window_decay(key)

        # 4. Update personalization index
        self._update_personalization(event.member.lower())

    def predict_preference(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Generate predictions blending all learning layers.

        Blends overall preference distribution mean with seasonal model
        predictions for the current season.

        Args:
            context: Context dictionary (currently unused but provided for
                     future extensibility with contextual predictions).

        Returns:
            Dict of preference_key -> predicted_value.
        """
        predictions: Dict[str, float] = {}
        season = get_current_season()

        for key, dist in self._preferences.items():
            blended = self._seasonal.blend_prediction(key, dist.mean, season)
            predictions[key] = blended

        return predictions

    def get_preference(
        self, key: str, season: Optional[str] = None
    ) -> Optional[PreferenceDistribution]:
        """Get the preference distribution for a key.

        Args:
            key: Preference key (e.g., "rajesh#explicit_rating").
            season: Optional season to get seasonal distribution instead.

        Returns:
            The PreferenceDistribution, or None if not found.
        """
        if season:
            return self._seasonal.get_distribution(key, season)
        return self._preferences.get(key)

    def get_personalization_index(self, member: str) -> float:
        """Get the personalization index for a member (0.0 to 1.0).

        Higher values indicate more personalized predictions due to
        more feedback data.

        Args:
            member: Family member name (case-insensitive).

        Returns:
            Float between 0.0 and 1.0.
        """
        return self._personalization_index.get(member.lower(), 0.0)

    def get_seasonal_model(self, season: str) -> Dict[str, Any]:
        """Get seasonal model info for a given season.

        Args:
            season: One of 'summer', 'monsoon', 'autumn', 'winter'.

        Returns:
            Dict with seasonal predictions for all tracked keys.
        """
        results: Dict[str, Any] = {}
        for key in self._preferences:
            dist = self._seasonal.get_distribution(key, season)
            if dist:
                results[key] = {
                    "mean": dist.mean,
                    "variance": dist.variance,
                    "sample_count": dist.sample_count,
                }
        return results

    def _apply_rolling_window_decay(self, key: str) -> None:
        """Apply 90-day rolling window decay to a preference distribution.

        Observations older than 90 days are pruned from the timestamp list.
        The distribution's effective sample count is adjusted based on how
        many observations fall within the window. Variance is increased
        proportionally to reflect reduced certainty from expired data.
        """
        if key not in self._observation_timestamps:
            return

        cutoff = datetime.now(timezone.utc) - timedelta(
            days=self.ROLLING_WINDOW_DAYS
        )

        # Filter observations within rolling window
        timestamps = self._observation_timestamps[key]
        valid_timestamps = [ts for ts in timestamps if ts >= cutoff]
        expired_count = len(timestamps) - len(valid_timestamps)

        self._observation_timestamps[key] = valid_timestamps

        # If observations expired, increase variance to reflect reduced certainty
        if expired_count > 0 and key in self._preferences:
            dist = self._preferences[key]
            # Each expired observation adds back a fraction of uncertainty
            decay_factor = 1.0 + (expired_count * 0.01)
            new_variance = min(dist.variance * decay_factor, 10.0)  # Cap at prior
            self._preferences[key] = PreferenceDistribution(
                key=dist.key,
                mean=dist.mean,
                variance=new_variance,
                sample_count=len(valid_timestamps),
                last_updated=dist.last_updated,
                seasonal_bias=dist.seasonal_bias,
            )

    def _update_personalization(self, member: str) -> None:
        """Update personalization index based on data density.

        The index reflects how much feedback data we have for a member.
        More feedback = higher personalization (capped at 1.0).
        100 total samples across all preference keys = fully personalized.

        Args:
            member: Lowercase family member name.
        """
        # Count preferences related to this member
        member_prefs = [
            k for k in self._preferences if k.startswith(f"{member}#")
        ]

        # Sum sample counts across all member preferences
        sample_counts = sum(
            self._preferences[k].sample_count for k in member_prefs
        )

        # Normalize: 100 samples = fully personalized (cap at 1.0)
        index = min(sample_counts / float(self.FULL_PERSONALIZATION_SAMPLES), 1.0)
        self._personalization_index[member] = index
