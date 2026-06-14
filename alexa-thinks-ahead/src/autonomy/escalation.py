"""Escalation and decay logic for the autonomy tier engine.

Requirements:
- 5.6: Require 7-day window + 80% acceptance for escalation
- 5.7: De-escalation is immediate on override
- 5.8: Apply trust decay during inactivity
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from src.autonomy.tiers import TierManager
from src.autonomy.trust import TrustScoreManager
from src.utils.config import get_config
from src.utils.constants import DEVICE_CATEGORIES, FAMILY_MEMBERS, TIER_THRESHOLDS
from src.utils.logging import get_logger

logger = get_logger(__name__)


class EscalationManager:
    """Manages tier escalation checks and trust decay.

    Escalation: Requires sustained trust over 7 days with 80%+ acceptance rate
    and the score meeting the next tier threshold.

    Decay: Reduces trust gradually during periods of inactivity by a
    configurable amount per inactive day.

    De-escalation: Immediate on explicit override (handled by TrustScoreManager).
    """

    def __init__(self, trust_manager: TrustScoreManager, tier_manager: TierManager):
        """Initialize EscalationManager.

        Args:
            trust_manager: TrustScoreManager for reading/writing trust scores.
            tier_manager: TierManager for determining tiers from scores.
        """
        self._trust = trust_manager
        self._tiers = tier_manager
        self._config = get_config()
        # Track acceptance history for escalation checks
        # Key: (member, category) -> list of interaction records
        self._interaction_history: Dict[tuple, List[Dict]] = {}

    def record_interaction(self, member: str, category: str, accepted: bool) -> None:
        """Record an interaction for escalation tracking.

        Args:
            member: Family member name (case-insensitive).
            category: Device category string.
            accepted: Whether the user accepted (True) or overrode (False).
        """
        key = (member.lower(), category)
        if key not in self._interaction_history:
            self._interaction_history[key] = []
        self._interaction_history[key].append({
            "timestamp": datetime.now(timezone.utc),
            "accepted": accepted,
        })

    def check_escalation(self, member: str, category: str) -> Optional[Dict]:
        """Check if a member-category pair qualifies for tier escalation.

        Escalation is a gate mechanism: even when a score qualifies for a
        higher tier, the system requires sustained positive history before
        confirming the escalation.

        Requirements (all must be met):
        1. Not already at tier 5
        2. Current score meets the threshold for the current tier
           (confirming the member deserves their current level)
        3. At least 7 days of interaction history
        4. 80%+ acceptance rate within the window

        When all criteria are met, the member is eligible to move up one tier.

        Args:
            member: Family member name (case-insensitive).
            category: Device category string.

        Returns:
            Dict with escalation info if eligible, None otherwise.
        """
        score = self._trust.get_score(member, category)
        current_tier = self._tiers.determine_tier(score)

        # Already at max tier
        if current_tier >= 5:
            return None

        # Score must meet the current tier's threshold (baseline qualification)
        current_threshold = TIER_THRESHOLDS[current_tier - 1]
        if score < current_threshold:
            return None

        # Check interaction history
        key = (member.lower(), category)
        history = self._interaction_history.get(key, [])

        if not history:
            return None

        # Requirement: history must span at least escalation_window_days
        window_days = self._config.escalation_window_days
        earliest = min(h["timestamp"] for h in history)
        span_days = (datetime.now(timezone.utc) - earliest).days
        if span_days < window_days:
            return None

        # Use all interactions for acceptance rate calculation
        accepted_count = sum(1 for h in history if h["accepted"])
        acceptance_rate = accepted_count / len(history)

        if acceptance_rate < self._config.escalation_min_acceptance_rate:
            return None

        return {
            "member": member,
            "category": category,
            "from_tier": current_tier,
            "to_tier": current_tier + 1,
            "score": score,
            "acceptance_rate": acceptance_rate,
            "interactions_in_window": len(history),
        }

    def apply_decay(self) -> Dict[str, float]:
        """Apply trust decay to all member-category pairs.

        Reduces score by trust_decay_per_day for each pair that currently
        has a score above 0. Decay represents gradual trust reduction
        during periods of inactivity.

        Returns:
            Dict mapping "member#category" to new score for all pairs
            that were actually reduced.
        """
        decayed = {}
        decay_amount = self._config.trust_decay_per_day

        for member in FAMILY_MEMBERS:
            for category in DEVICE_CATEGORIES:
                current = self._trust.get_score(member, category)
                if current > 0:
                    new_score = max(0.0, current - decay_amount)
                    if new_score != current:
                        self._trust._scores[(member, category)] = new_score
                        decayed[f"{member}#{category}"] = new_score

        if decayed:
            logger.info(
                f"Trust decay applied to {len(decayed)} pairs "
                f"(decay_amount={decay_amount})"
            )

        return decayed

    def immediate_deescalation(self, member: str, category: str) -> Dict:
        """Handle immediate de-escalation on override.

        This is called when a user overrides an action. The trust score
        decrease is handled by TrustScoreManager.record_override(),
        and this method reports the resulting tier change.

        Args:
            member: Family member name (case-insensitive).
            category: Device category string.

        Returns:
            Dict with de-escalation details.
        """
        score = self._trust.get_score(member, category)
        current_tier = self._tiers.determine_tier(score)

        return {
            "member": member,
            "category": category,
            "current_tier": current_tier,
            "score": score,
            "reason": "immediate_deescalation_on_override",
        }
