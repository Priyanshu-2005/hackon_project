"""Proactive intelligence engine — generates anticipatory actions via Claude Sonnet reasoning.

Evaluates context against intelligence strategies and produces prioritized
action plans without hardcoded scenario logic. All decisions flow through
Amazon Bedrock Claude Sonnet reasoning.

Requirements:
    4.1: Invoke Bedrock with structured context
    13.2: No hardcoded scenario logic
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from src.context.engine import ContextEngine
from src.intelligence.routing import route_action_plan
from src.models.autonomy import ActionType
from src.models.context import ContextSnapshot
from src.models.intelligence import ActionPlan, Prediction, ReasoningRequest, ReasoningResponse
from src.reasoning.client import BedrockReasoningClient
from src.utils.config import get_config
from src.utils.constants import INTELLIGENCE_STRATEGIES
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ProactiveEngine:
    """Generates anticipatory actions via Claude Sonnet reasoning.

    Evaluates context against intelligence strategies and produces
    prioritized action plans without hardcoded scenario logic.
    """

    def __init__(self, context_engine: ContextEngine, reasoning_client: BedrockReasoningClient):
        self._context = context_engine
        self._reasoner = reasoning_client
        self._config = get_config()

    def evaluate_context(self, snapshot: Optional[ContextSnapshot] = None) -> ActionPlan:
        """Evaluate current context and generate an action plan.

        Builds a fresh context snapshot (or uses provided one),
        invokes Bedrock reasoning, and routes predictions by confidence.

        Args:
            snapshot: Optional pre-built context snapshot. If None, builds fresh.

        Returns:
            ActionPlan with prioritized predictions.
        """
        if snapshot is None:
            snapshot = self._context.build_snapshot()

        # Build reasoning request
        request = ReasoningRequest(
            context=snapshot,
            event=None,
            preferences={},  # Will be filled by learning engine
            autonomy_config={},  # Will be filled by autonomy engine
            query_type="action_plan",
        )

        # Invoke reasoning
        response = self._reasoner.invoke_reasoning(request)

        # Convert response into predictions
        predictions = self._response_to_predictions(response)

        # Route predictions by confidence (sets action_type, filters discards)
        routed = route_action_plan(predictions)

        # Sort by confidence (highest first)
        routed.sort(key=lambda p: p.confidence, reverse=True)

        return ActionPlan(
            plan_id=str(uuid4()),
            event_id=None,
            predictions=routed,
            reasoning_chain=response.reasoning_chain,
            context_snapshot_id=snapshot.snapshot_id,
            created_at=datetime.now(timezone.utc),
        )

    def handle_event(self, event: Dict, snapshot: Optional[ContextSnapshot] = None) -> ActionPlan:
        """Handle a specific event through contextual reasoning.

        Similar to evaluate_context but includes the event in the reasoning
        request so Claude can factor it into its decision-making.

        Args:
            event: Event dictionary with at minimum an "event_id" key.
            snapshot: Optional pre-built context snapshot. If None, builds fresh
                      with force_refresh=True.

        Returns:
            ActionPlan with prioritized predictions for the event.
        """
        if snapshot is None:
            snapshot = self._context.build_snapshot(force_refresh=True)

        request = ReasoningRequest(
            context=snapshot,
            event=event,
            preferences={},
            autonomy_config={},
            query_type="action_plan",
        )

        response = self._reasoner.invoke_reasoning(request)
        predictions = self._response_to_predictions(response)
        routed = route_action_plan(predictions)
        routed.sort(key=lambda p: p.confidence, reverse=True)

        return ActionPlan(
            plan_id=str(uuid4()),
            event_id=event.get("event_id", str(uuid4())),
            predictions=routed,
            reasoning_chain=response.reasoning_chain,
            context_snapshot_id=snapshot.snapshot_id,
            created_at=datetime.now(timezone.utc),
        )

    def _response_to_predictions(self, response: ReasoningResponse) -> List[Prediction]:
        """Convert a ReasoningResponse into a list of Prediction objects.

        Each action in the response becomes a Prediction with confidence,
        strategy, and target devices extracted from the model output.

        Args:
            response: The parsed response from Bedrock reasoning.

        Returns:
            List of Prediction objects (unrouted — action_type defaults to INFORM).
        """
        predictions: List[Prediction] = []

        for action in response.actions:
            strategy = action.get(
                "strategy",
                INTELLIGENCE_STRATEGIES[0] if INTELLIGENCE_STRATEGIES else "unknown",
            )
            confidence = float(action.get("confidence", response.confidence))

            prediction = Prediction(
                prediction_id=str(uuid4()),
                strategy=strategy,
                target_devices=action.get("target_devices", action.get("devices", [])),
                actions=[],  # Device commands will be built by the action dispatcher
                confidence=confidence,
                action_type=ActionType.INFORM,  # Will be set by route_action_plan
                reasoning=action.get("reasoning", response.reasoning_chain),
                estimated_benefit=action.get("benefit", "Improved comfort and efficiency"),
            )
            predictions.append(prediction)

        return predictions
