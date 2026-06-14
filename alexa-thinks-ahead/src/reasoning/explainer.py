"""Explanation generator for proactive smart home actions.

Generates natural language explanations from reasoning chains and action
results, tailored per family member role and routed to appropriate Echo devices.

Requirements:
    10.1: Every action accompanied by a natural language explanation
    10.2: Include triggering event, reasoning summary, and expected benefit
    10.3: Tailor messages per family member (role-appropriate language)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.models.family import FamilyMember, FamilyProfile, SHARMA_FAMILY
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Explanation:
    """A generated explanation with audience targeting."""

    message: str
    target_member: str
    target_device: str
    event_summary: str
    reasoning_summary: str
    expected_benefit: str


class ExplanationGenerator:
    """Generates natural language explanations from reasoning chains.

    Takes action results and reasoning chains and produces human-readable
    messages tailored per family member role. Routes announcements to
    the appropriate Echo device for each member.

    Attributes:
        _family: The family profile used for role-based tailoring.
    """

    def __init__(self, family_profile: Optional[FamilyProfile] = None):
        """Initialize with a family profile.

        Args:
            family_profile: Family profile for member lookups. Defaults to SHARMA_FAMILY.
        """
        self._family = family_profile or SHARMA_FAMILY

    def generate_explanation(
        self,
        event: Dict[str, Any],
        actions: List[Dict[str, Any]],
        reasoning_chain: str,
        target_members: Optional[List[str]] = None,
    ) -> List[Explanation]:
        """Generate explanations for actions taken in response to an event.

        Produces a tailored explanation for each target family member,
        including the triggering event, reasoning summary, and expected benefit.

        Args:
            event: The triggering event dict with 'event_type' and optional details.
            actions: List of action dicts describing what was done.
            reasoning_chain: The reasoning chain from the AI engine.
            target_members: Optional list of member names to notify.
                           If None, notifies all members.

        Returns:
            List of Explanation objects, one per target member.
        """
        event_type = event.get("event_type", "unknown")
        event_summary = self._summarize_event(event)
        reasoning_summary = self._summarize_reasoning(reasoning_chain)
        expected_benefit = self._extract_benefit(actions, reasoning_chain)

        # Determine target audience
        members = self._resolve_target_members(target_members)

        explanations: List[Explanation] = []
        for member in members:
            message = self._tailor_message(
                member=member,
                event_summary=event_summary,
                actions=actions,
                reasoning_summary=reasoning_summary,
                expected_benefit=expected_benefit,
            )
            explanation = Explanation(
                message=message,
                target_member=member.name,
                target_device=member.preferred_echo,
                event_summary=event_summary,
                reasoning_summary=reasoning_summary,
                expected_benefit=expected_benefit,
            )
            explanations.append(explanation)

        logger.info(
            f"Generated {len(explanations)} explanations for event '{event_type}'"
        )
        return explanations

    def generate_single_explanation(
        self,
        event: Dict[str, Any],
        actions: List[Dict[str, Any]],
        reasoning_chain: str,
    ) -> str:
        """Generate a single household-wide explanation message.

        Useful for broadcasting a single announcement to all Echo devices.

        Args:
            event: The triggering event dict.
            actions: List of action dicts.
            reasoning_chain: The reasoning chain string.

        Returns:
            A single human-readable explanation string.
        """
        event_summary = self._summarize_event(event)
        reasoning_summary = self._summarize_reasoning(reasoning_chain)
        expected_benefit = self._extract_benefit(actions, reasoning_chain)
        action_summary = self._summarize_actions(actions)

        parts = []
        if event_summary:
            parts.append(event_summary)
        if action_summary:
            parts.append(action_summary)
        if expected_benefit:
            parts.append(expected_benefit)

        return " ".join(parts) if parts else "No explanation available."

    def route_announcements(
        self, explanations: List[Explanation]
    ) -> List[Dict[str, str]]:
        """Route explanation announcements to appropriate Echo devices.

        Maps each explanation to its target Echo device for delivery.

        Args:
            explanations: List of Explanation objects to route.

        Returns:
            List of dicts with 'device', 'member', and 'message' keys.
        """
        announcements: List[Dict[str, str]] = []
        for explanation in explanations:
            announcements.append({
                "device": explanation.target_device,
                "member": explanation.target_member,
                "message": explanation.message,
            })
        return announcements

    def _summarize_event(self, event: Dict[str, Any]) -> str:
        """Create a brief human-readable summary of the triggering event.

        Args:
            event: Event dict with event_type and optional details.

        Returns:
            A short sentence describing the event.
        """
        event_type = event.get("event_type", "unknown")
        source = event.get("source", "")

        # Map event types to friendly descriptions
        event_descriptions = {
            "power_cut": "Power cut detected.",
            "security_breach": "Security alert triggered.",
            "device_failure": "A device has stopped responding.",
            "fire_alarm": "Fire alarm activated.",
            "temperature_change": "Temperature change detected.",
            "motion_detected": "Motion detected.",
            "door_opened": "Door opened.",
            "schedule_trigger": "Scheduled activity started.",
        }

        description = event_descriptions.get(
            event_type,
            f"Event detected: {event_type.replace('_', ' ')}.",
        )

        if source:
            description = f"{description} Source: {source.replace('_', ' ')}."

        return description

    def _summarize_reasoning(self, reasoning_chain: str) -> str:
        """Condense the reasoning chain into a brief summary.

        Args:
            reasoning_chain: Full reasoning chain from the AI.

        Returns:
            A short summary of the reasoning (max ~50 words).
        """
        if not reasoning_chain:
            return "Based on current conditions and household patterns."

        # Take the first meaningful sentence/segment as summary
        sentences = reasoning_chain.split(".")
        summary_parts = []
        word_count = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            words = sentence.split()
            if word_count + len(words) > 50:
                break
            summary_parts.append(sentence)
            word_count += len(words)

        if summary_parts:
            return ". ".join(summary_parts) + "."
        return "Based on current conditions and household patterns."

    def _extract_benefit(
        self, actions: List[Dict[str, Any]], reasoning_chain: str
    ) -> str:
        """Extract the expected benefit from actions and reasoning.

        Args:
            actions: List of action dicts.
            reasoning_chain: The reasoning chain string.

        Returns:
            A sentence describing the expected benefit.
        """
        if not actions:
            return ""

        # Try to find benefit-related keywords in reasoning
        benefit_keywords = [
            "comfort", "safety", "energy", "efficiency",
            "continuity", "convenience", "security", "protection",
        ]

        reasoning_lower = reasoning_chain.lower() if reasoning_chain else ""
        found_benefits = [
            kw for kw in benefit_keywords if kw in reasoning_lower
        ]

        if found_benefits:
            benefit = found_benefits[0]
            return f"This helps maintain {benefit} for your household."

        # Generic benefit based on action count
        count = len(actions)
        if count == 1:
            return "This adjustment optimizes your home environment."
        return f"These {count} adjustments optimize your home environment."

    def _summarize_actions(self, actions: List[Dict[str, Any]]) -> str:
        """Create a brief summary of actions taken.

        Args:
            actions: List of action dicts with strategy, target_devices, etc.

        Returns:
            A human-readable summary of what was done.
        """
        if not actions:
            return "No actions taken."

        summaries = []
        for action in actions[:3]:  # Limit to 3 for brevity
            strategy = action.get("strategy", "adjustment")
            targets = action.get("target_devices", [])
            if targets:
                device_names = ", ".join(
                    t.replace("_", " ") for t in targets[:2]
                )
                summaries.append(f"{strategy.replace('_', ' ')} on {device_names}")
            else:
                summaries.append(strategy.replace("_", " "))

        action_text = "; ".join(summaries)
        remaining = len(actions) - 3
        if remaining > 0:
            action_text += f" and {remaining} more adjustment{'s' if remaining > 1 else ''}"

        return f"Actions taken: {action_text}."

    def _tailor_message(
        self,
        member: FamilyMember,
        event_summary: str,
        actions: List[Dict[str, Any]],
        reasoning_summary: str,
        expected_benefit: str,
    ) -> str:
        """Tailor the explanation message for a specific family member.

        Adjusts language complexity and detail level based on the
        member's role (parent, child, elder).

        Args:
            member: The target family member.
            event_summary: Brief event description.
            actions: List of action dicts.
            reasoning_summary: Brief reasoning summary.
            expected_benefit: Expected benefit sentence.

        Returns:
            A role-appropriate explanation message.
        """
        if member.role == "elder":
            return self._format_elder_message(
                event_summary, actions, expected_benefit
            )
        elif member.role == "child":
            return self._format_child_message(
                event_summary, actions, expected_benefit
            )
        else:  # parent
            return self._format_parent_message(
                event_summary, actions, reasoning_summary, expected_benefit
            )

    def _format_parent_message(
        self,
        event_summary: str,
        actions: List[Dict[str, Any]],
        reasoning_summary: str,
        expected_benefit: str,
    ) -> str:
        """Format message for parents with full detail.

        Parents get the complete picture: event, reasoning, actions, benefit.
        """
        action_summary = self._summarize_actions(actions)
        parts = [event_summary, reasoning_summary, action_summary]
        if expected_benefit:
            parts.append(expected_benefit)
        return " ".join(parts)

    def _format_elder_message(
        self,
        event_summary: str,
        actions: List[Dict[str, Any]],
        expected_benefit: str,
    ) -> str:
        """Format message for elders with simple, reassuring language.

        Elders get a simple explanation focused on what happened and
        that everything is taken care of.
        """
        action_count = len(actions)
        if action_count == 0:
            return f"{event_summary} Everything is fine, no changes needed."

        return (
            f"{event_summary} I've made some adjustments to keep things comfortable. "
            f"{expected_benefit}" if expected_benefit
            else f"{event_summary} I've made some adjustments to keep things comfortable."
        )

    def _format_child_message(
        self,
        event_summary: str,
        actions: List[Dict[str, Any]],
        expected_benefit: str,
    ) -> str:
        """Format message for children with brief, friendly language.

        Children get a short, easy-to-understand explanation.
        """
        if not actions:
            return f"{event_summary} Nothing to worry about!"

        return f"{event_summary} I've taken care of a few things so everything keeps working smoothly."

    def _resolve_target_members(
        self, target_names: Optional[List[str]] = None
    ) -> List[FamilyMember]:
        """Resolve target member names to FamilyMember objects.

        Args:
            target_names: Optional list of member names. If None, returns all members.

        Returns:
            List of FamilyMember objects to notify.
        """
        if target_names is None:
            return self._family.members

        members = []
        for name in target_names:
            member = next(
                (m for m in self._family.members if m.name == name), None
            )
            if member:
                members.append(member)
            else:
                logger.warning(f"Member '{name}' not found in family profile")

        return members if members else self._family.members
