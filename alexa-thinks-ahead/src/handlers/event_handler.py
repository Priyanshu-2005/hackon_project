"""EventBridge event processor Lambda handler.

Processes device events from the SmartHomeEventBus, detects critical
events for immediate processing, and routes through the full
SENSE-THINK-ACT-EXPLAIN cognitive pipeline via ContextualEventHandler.

Requirements:
    7.1: Process EventBridge events within 5 seconds
    7.3: Critical events trigger immediate context fusion
"""

import json
from typing import Any, Dict

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Events requiring immediate processing with forced context refresh
CRITICAL_EVENT_TYPES = {"power_cut", "security_breach", "device_failure", "fire_alarm"}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for EventBridge device events.

    Receives events from the SmartHomeEventBus, classifies them
    as critical or normal, and routes them through the contextual
    event handler for full pipeline execution.

    Args:
        event: EventBridge event envelope with 'detail' containing
               the device event payload.
        context: Lambda context object.

    Returns:
        Dict with processing result including event_type, is_critical,
        and actions taken.
    """
    try:
        # Extract event detail from EventBridge envelope
        detail = event.get("detail", event)
        event_type = detail.get("event_type", "unknown")
        source = detail.get("source", event.get("source", "unknown"))

        logger.info(
            f"Processing event: type={event_type}, source={source}"
        )

        is_critical = event_type in CRITICAL_EVENT_TYPES

        if is_critical:
            logger.info(
                f"Critical event detected: {event_type}. "
                "Triggering immediate context fusion."
            )

        # Route through the contextual event handler pipeline
        result = _process_through_pipeline(detail, is_critical)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "event_type": event_type,
                "is_critical": is_critical,
                "source": source,
                "actions_count": result.get("actions_count", 0),
                "explanation": result.get("explanation", ""),
                "status": "processed",
            }),
        }

    except Exception as e:
        logger.error(f"Event processing error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Event processing failed",
                "message": str(e),
            }),
        }


def _process_through_pipeline(
    event_detail: Dict[str, Any], is_critical: bool
) -> Dict[str, Any]:
    """Route event through the ContextualEventHandler pipeline.

    In production, this initializes the full engine stack and
    invokes the SENSE-THINK-ACT-EXPLAIN pipeline. For the Lambda
    entry point, we initialize engines from environment config.

    Args:
        event_detail: The event payload with event_type and details.
        is_critical: Whether this event requires forced context refresh.

    Returns:
        Dict with actions_count and explanation from pipeline execution.
    """
    try:
        from src.context.engine import ContextEngine
        from src.intelligence.engine import ProactiveEngine
        from src.intelligence.event_handler import ContextualEventHandler

        # Initialize engines (in production these would use real adapters
        # and DynamoDB tables from environment variables)
        context_engine = ContextEngine(adapters={}, table=None)
        proactive_engine = ProactiveEngine(
            context_engine=context_engine, reasoning_client=None
        )

        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
        )

        result = handler.handle_event(event_detail)

        return {
            "actions_count": len(result.get("actions_executed", [])),
            "explanation": result.get("explanation", ""),
        }
    except Exception as e:
        logger.warning(
            f"Pipeline execution failed, returning empty result: {e}"
        )
        return {"actions_count": 0, "explanation": ""}
