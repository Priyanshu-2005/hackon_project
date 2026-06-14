"""Autonomy engine orchestrator combining trust, tiers, escalation, and decay.

Requirements:
- 5.1: Trust scores per member per category
- 5.2: Map trust scores to tiers
- 5.5: Permit action iff member tier >= required tier
- 5.6: Escalation requires sustained trust over configurable window
"""

from typing import Dict, List, Optional

from src.autonomy.escalation import EscalationManager
from src.autonomy.tiers import TierManager
from src.autonomy.trust import TrustScoreManager
from src.devices.registry import DeviceRegistry
from src.models.autonomy import TierDecision
from src.models.device import DeviceCommand
from src.utils.constants import DEVICE_CATEGORIES, FAMILY_MEMBERS
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AutonomyEngine:
    """Orchestrates trust scoring, tier management, escalation, and decay.

    Provides a unified interface for the rest of the system to:
    - Check permissions for device actions
    - Record user acceptances and overrides
    - Retrieve tier configuration for the reasoning client
    - Apply daily trust decay
    - Track interactions for the learning engine feedback loop
    """

    def __init__(self, table=None, device_registry: DeviceRegistry = None):
        """Initialize the AutonomyEngine with all sub-components.

        Args:
            table: Optional DynamoDB table resource for trust score persistence.
            device_registry: Optional DeviceRegistry instance. Defaults to a new one.
        """
        registry = device_registry or DeviceRegistry()
        self._trust = TrustScoreManager(table=table)
        self._tiers = TierManager(trust_manager=self._trust, device_registry=registry)
        self._escalation = EscalationManager(
            trust_manager=self._trust, tier_manager=self._tiers
        )
        # Track all interactions for learning engine feedback
        self._interaction_log: List[Dict] = []

    @property
    def trust_manager(self) -> TrustScoreManager:
        """Expose trust manager for external inspection."""
        return self._trust

    @property
    def tier_manager(self) -> TierManager:
        """Expose tier manager for external inspection."""
        return self._tiers

    @property
    def escalation_manager(self) -> EscalationManager:
        """Expose escalation manager for external inspection."""
        return self._escalation

    def check_permission(self, member: str, action: DeviceCommand) -> TierDecision:
        """Check if a member has permission to perform an action.

        Delegates to TierManager which compares the member's current tier
        (derived from trust score) against the action's required tier.

        Args:
            member: Family member name (case-insensitive).
            action: DeviceCommand with device_id and tier_required.

        Returns:
            TierDecision with permitted flag, tiers, and reason.
        """
        decision = self._tiers.check_permission(member, action)
        logger.info(
            f"Permission check: member={member}, device={action.device_id}, "
            f"permitted={decision.permitted}"
        )
        return decision

    def record_acceptance(self, member: str, category: str) -> None:
        """Record that a user accepted a system action.

        Increases trust score and records the interaction for escalation
        tracking and learning engine feedback.

        Args:
            member: Family member name (case-insensitive).
            category: Device category string.
        """
        self._trust.record_acceptance(member, category)
        self._escalation.record_interaction(member, category, accepted=True)
        self._log_interaction(member, category, accepted=True)
        logger.info(f"Acceptance recorded: {member}/{category}")

    def record_override(self, member: str, category: str) -> None:
        """Record that a user overrode a system action.

        Decreases trust score immediately and records the interaction
        for escalation tracking and learning engine feedback.

        Args:
            member: Family member name (case-insensitive).
            category: Device category string.
        """
        self._trust.record_override(member, category)
        self._escalation.record_interaction(member, category, accepted=False)
        self._log_interaction(member, category, accepted=False)
        logger.info(f"Override recorded: {member}/{category}")

    def get_tier_config(self) -> Dict[str, int]:
        """Get current tier for all member-category pairs.

        Returns a dictionary mapping "member_category" strings to tier numbers.
        This is consumed by the reasoning client to factor autonomy levels
        into its decision-making.

        Returns:
            Dict like {"rajesh_climate": 3, "priya_lighting": 2, ...}
        """
        config = {}
        for member in FAMILY_MEMBERS:
            for category in DEVICE_CATEGORIES:
                score = self._trust.get_score(member, category)
                tier = self._tiers.determine_tier(score)
                config[f"{member}_{category}"] = tier
        return config

    def apply_daily_decay(self) -> Dict[str, float]:
        """Apply daily trust decay across all member-category pairs.

        Delegates to EscalationManager which reduces scores for inactive
        pairs by a configurable decay amount.

        Returns:
            Dict mapping "member#category" to new score for pairs that decayed.
        """
        decayed = self._escalation.apply_decay()
        if decayed:
            logger.info(f"Daily decay applied to {len(decayed)} pairs")
        return decayed

    def check_escalation(self, member: str, category: str) -> Optional[Dict]:
        """Check if a member-category pair qualifies for tier escalation.

        Args:
            member: Family member name (case-insensitive).
            category: Device category string.

        Returns:
            Dict with escalation info if eligible, None otherwise.
        """
        return self._escalation.check_escalation(member, category)

    def get_interaction_log(self) -> List[Dict]:
        """Retrieve the interaction log for learning engine consumption.

        Returns:
            List of interaction records with member, category, and accepted flag.
        """
        return list(self._interaction_log)

    def _log_interaction(self, member: str, category: str, accepted: bool) -> None:
        """Record an interaction in the internal log for learning feedback.

        Args:
            member: Family member name.
            category: Device category string.
            accepted: Whether the user accepted (True) or overrode (False).
        """
        from datetime import datetime, timezone

        self._interaction_log.append(
            {
                "member": member.lower(),
                "category": category,
                "accepted": accepted,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
