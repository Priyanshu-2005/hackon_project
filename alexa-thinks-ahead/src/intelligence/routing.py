"""Confidence-based action routing for proactive predictions.

Routes predictions to appropriate action types based on confidence scores:
- >= 0.85 → AUTO_EXECUTE
- >= 0.60 → RECOMMEND
- >= 0.40 → INFORM
- < 0.40  → discard (None)
"""

from typing import List, Optional

from src.models.autonomy import ActionType
from src.models.intelligence import Prediction
from src.utils.config import get_config


def route_action(confidence: float) -> Optional[ActionType]:
    """Route a prediction to the appropriate action type based on confidence.

    Args:
        confidence: Confidence score between 0.0 and 1.0

    Returns:
        ActionType.AUTO_EXECUTE if >= 0.85
        ActionType.RECOMMEND if >= 0.60
        ActionType.INFORM if >= 0.40
        None if < 0.40 (discard)
    """
    config = get_config()

    if confidence >= config.action_threshold:
        return ActionType.AUTO_EXECUTE
    elif confidence >= config.recommend_threshold:
        return ActionType.RECOMMEND
    elif confidence >= config.inform_threshold:
        return ActionType.INFORM
    else:
        return None  # Discard


def route_action_plan(predictions: List[Prediction]) -> List[Prediction]:
    """Apply action routing to each prediction in a plan.

    Sets the action_type field on each prediction based on its confidence.
    Discards predictions below the inform threshold.

    Args:
        predictions: List of Prediction objects with confidence scores.

    Returns:
        List of predictions that were not discarded, with action_type set.
    """
    routed: List[Prediction] = []
    for prediction in predictions:
        action_type = route_action(prediction.confidence)
        if action_type is not None:
            prediction.action_type = action_type
            routed.append(prediction)
    return routed
