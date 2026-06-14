"""Tier determination and permission checks for the autonomy engine.

Requirements:
- 5.2: Map trust scores to tiers: [0-20]=1, [21-45]=2, [46-70]=3, [71-90]=4, [91-100]=5
- 5.5: Permit action iff current_tier >= action.tier_required
"""

from src.autonomy.trust import TrustScoreManager
from src.devices.registry import DeviceRegistry
from src.models.autonomy import TierDecision
from src.models.device import DeviceCommand
from src.utils.constants import TIER_THRESHOLDS, TIER_NAMES
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TierManager:
    """Manages tier determination from trust scores and permission checks.

    Uses TrustScoreManager to retrieve scores and maps them to tiers 1-5.
    Checks whether a member's current tier permits a given action.
    """

    def __init__(
        self,
        trust_manager: TrustScoreManager,
        device_registry: DeviceRegistry,
    ):
        """Initialize TierManager.

        Args:
            trust_manager: TrustScoreManager for retrieving trust scores.
            device_registry: DeviceRegistry for mapping device_id to category.
        """
        self._trust_manager = trust_manager
        self._device_registry = device_registry

    def determine_tier(self, score: float) -> int:
        """Map a trust score (0-100) to an autonomy tier (1-5).

        Tier thresholds:
            [0-20]  -> Tier 1 (Inform)
            [21-45] -> Tier 2 (Suggest)
            [46-70] -> Tier 3 (Auto-Act Reversible)
            [71-90] -> Tier 4 (Auto-Act Irreversible)
            [91-100] -> Tier 5 (Full Autonomy)

        Args:
            score: Trust score in range [0, 100].

        Returns:
            Tier number (1 to 5).
        """
        tier = 1
        for i, threshold in enumerate(TIER_THRESHOLDS):
            if score >= threshold:
                tier = i + 1
        return tier

    def get_device_category(self, device_id: str) -> str:
        """Look up the category for a device_id via the device registry.

        Args:
            device_id: The unique device identifier.

        Returns:
            Category string (e.g. "climate", "security").

        Raises:
            ValueError: If device_id is not found in the registry.
        """
        device_config = self._device_registry.get_device(device_id)
        if device_config is None:
            raise ValueError(
                f"Device '{device_id}' not found in device registry"
            )
        return device_config["category"]

    def check_permission(self, member: str, action: DeviceCommand) -> TierDecision:
        """Check whether a member's tier permits the given action.

        Gets the member's trust score for the action's device category,
        determines the current tier, and compares it to the action's
        required tier.

        Args:
            member: Family member name (case-insensitive).
            action: DeviceCommand with device_id and tier_required.

        Returns:
            TierDecision with permitted flag, tiers, and reason.
        """
        category = self.get_device_category(action.device_id)
        score = self._trust_manager.get_score(member, category)
        current_tier = self.determine_tier(score)
        required_tier = action.tier_required
        permitted = current_tier >= required_tier

        if permitted:
            reason = (
                f"Action permitted: {member}'s tier {current_tier} "
                f"({TIER_NAMES.get(current_tier, 'Unknown')}) "
                f">= required tier {required_tier} "
                f"({TIER_NAMES.get(required_tier, 'Unknown')}) "
                f"for {category} category (score: {score:.1f})"
            )
        else:
            reason = (
                f"Action denied: {member}'s tier {current_tier} "
                f"({TIER_NAMES.get(current_tier, 'Unknown')}) "
                f"< required tier {required_tier} "
                f"({TIER_NAMES.get(required_tier, 'Unknown')}) "
                f"for {category} category (score: {score:.1f})"
            )

        # Requires confirmation if at tier boundary (tier 4 actions)
        requires_confirmation = (
            permitted and required_tier >= 4 and current_tier == required_tier
        )

        decision = TierDecision(
            action=action,
            permitted=permitted,
            current_tier=current_tier,
            required_tier=required_tier,
            requires_confirmation=requires_confirmation,
            reason=reason,
        )

        logger.info(
            f"Permission check: member={member}, device={action.device_id}, "
            f"category={category}, score={score:.1f}, "
            f"tier={current_tier}, required={required_tier}, "
            f"permitted={permitted}"
        )

        return decision
