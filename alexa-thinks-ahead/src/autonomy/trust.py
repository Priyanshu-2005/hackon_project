"""Trust score management for the autonomy tier engine.

Requirements:
- 5.1: Trust scores per member per category, range 0-100
- 5.3: Acceptance increases trust by up to 5 points without exceeding 100
- 5.4: Override decreases trust by 15 without going below 0
"""

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from src.models.autonomy import TrustScore
from src.models.device import DeviceCategory
from src.utils.config import get_config
from src.utils.constants import FAMILY_MEMBERS, DEVICE_CATEGORIES, TIER_THRESHOLDS
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TrustScoreManager:
    """Manages trust scores per family member per device category.

    Scores range from 0 to 100 inclusive.
    Acceptance: increase by min(5, 100 - current)
    Override: decrease by 15, floor at 0

    Stores scores in DynamoDB with member_category as partition key.
    """

    def __init__(self, table=None):
        self._config = get_config()
        self._table = table
        # In-memory cache of trust scores
        self._scores: Dict[Tuple[str, str], float] = {}
        # Initialize all member-category pairs at 0
        for member in FAMILY_MEMBERS:
            for category in DEVICE_CATEGORIES:
                self._scores[(member, category)] = 0.0

    def get_score(self, member: str, category: str) -> float:
        """Get the current trust score for a member-category pair.

        Args:
            member: Family member name (case-insensitive).
            category: Device category string.

        Returns:
            Current trust score (0.0 to 100.0).
        """
        return self._scores.get((member.lower(), category), 0.0)

    def record_acceptance(self, member: str, category: str) -> float:
        """Record that a user accepted a system action.

        Increases trust by min(5, 100 - current) so the score
        never exceeds 100.

        Args:
            member: Family member name (case-insensitive).
            category: Device category string.

        Returns:
            New trust score after the increase.
        """
        key = (member.lower(), category)
        current = self._scores.get(key, 0.0)
        delta = min(self._config.trust_acceptance_delta, 100.0 - current)
        new_score = current + delta
        self._scores[key] = new_score
        self._persist_score(key, new_score)
        logger.info(
            f"Trust acceptance: {key} {current:.1f} -> {new_score:.1f} (+{delta:.1f})"
        )
        return new_score

    def record_override(self, member: str, category: str) -> float:
        """Record that a user overrode a system action.

        Decreases trust by 15, floor at 0.

        Args:
            member: Family member name (case-insensitive).
            category: Device category string.

        Returns:
            New trust score after the decrease.
        """
        key = (member.lower(), category)
        current = self._scores.get(key, 0.0)
        new_score = max(0.0, current - self._config.trust_override_penalty)
        self._scores[key] = new_score
        self._persist_score(key, new_score)
        logger.info(
            f"Trust override: {key} {current:.1f} -> {new_score:.1f} (-{self._config.trust_override_penalty:.1f})"
        )
        return new_score

    def get_trust_score(self, member: str, category: str) -> TrustScore:
        """Get a full TrustScore object for a member-category pair.

        Args:
            member: Family member name (case-insensitive).
            category: Device category string.

        Returns:
            TrustScore dataclass with score, tier, and metadata.
        """
        score = self.get_score(member, category)
        tier = self._calculate_tier(score)

        return TrustScore(
            member=member.lower(),
            category=DeviceCategory(category),
            score=score,
            current_tier=tier,
            last_interaction=datetime.now(timezone.utc),
        )

    def _calculate_tier(self, score: float) -> int:
        """Map score to tier (1-5).

        Tier thresholds: [0, 21, 46, 71, 91]
        - 0-20: Tier 1 (Inform)
        - 21-45: Tier 2 (Suggest)
        - 46-70: Tier 3 (Auto-Reversible)
        - 71-90: Tier 4 (Auto-Irreversible)
        - 91-100: Tier 5 (Full Autonomy)
        """
        tier = 1
        for i, threshold in enumerate(TIER_THRESHOLDS):
            if score >= threshold:
                tier = i + 1
        return tier

    def _persist_score(self, key: Tuple[str, str], score: float) -> None:
        """Persist a trust score to DynamoDB.

        Args:
            key: Tuple of (member, category).
            score: The trust score to persist.
        """
        if self._table is None:
            return

        member, category = key
        partition_key = f"{member}#{category}"
        tier = self._calculate_tier(score)
        now = datetime.now(timezone.utc).isoformat()

        try:
            self._table.put_item(
                Item={
                    "member_category": partition_key,
                    "updated_at": now,
                    "score": str(score),
                    "current_tier": tier,
                    "member": member,
                    "category": category,
                }
            )
        except Exception as e:
            logger.error(f"Failed to persist trust score for {partition_key}: {e}")

    def load_scores_from_dynamo(self) -> None:
        """Load all trust scores from DynamoDB into the in-memory cache."""
        if self._table is None:
            return

        try:
            response = self._table.scan()
            items = response.get("Items", [])
            for item in items:
                member = item["member"]
                category = item["category"]
                score = float(item["score"])
                self._scores[(member, category)] = score
            logger.info(f"Loaded {len(items)} trust scores from DynamoDB")
        except Exception as e:
            logger.error(f"Failed to load trust scores from DynamoDB: {e}")
