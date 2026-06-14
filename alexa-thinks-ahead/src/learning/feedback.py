"""Feedback collector for continuous learning engine.

Collects feedback from multiple channels (explicit ratings, overrides,
acceptances, adjustments) and normalizes signals to [-1.0, 1.0] range.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key

from src.models.learning import FeedbackEvent
from src.utils.config import get_config
from src.utils.dynamo_utils import serialize_for_dynamo, calculate_ttl


class FeedbackCollector:
    """Collects and normalizes feedback from multiple channels.

    Feedback types and normalization:
        - explicit_rating (1-5): (rating - 3) / 2 → maps 1→-1.0, 3→0.0, 5→1.0
        - override: always -1.0
        - acceptance: always +1.0
        - adjustment: partial signal passed as-is (already in [-1, 1])

    Stores FeedbackEvent objects in DynamoDB for later retrieval.
    """

    VALID_FEEDBACK_TYPES = ("explicit_rating", "override", "acceptance", "adjustment")

    def __init__(self, table_name: Optional[str] = None, dynamodb_resource=None):
        """Initialize FeedbackCollector.

        Args:
            table_name: DynamoDB table name for storing feedback events.
                        Defaults to preference_table from config.
            dynamodb_resource: Optional boto3 DynamoDB resource for testing.
        """
        config = get_config()
        self._table_name = table_name or config.preference_table
        self._dynamodb = dynamodb_resource
        self._table = None

    @property
    def table(self):
        """Lazy-load DynamoDB table."""
        if self._table is None:
            if self._dynamodb is None:
                self._dynamodb = boto3.resource("dynamodb")
            self._table = self._dynamodb.Table(self._table_name)
        return self._table

    def normalize_signal(self, feedback_type: str, raw_value: float = 0.0) -> float:
        """Normalize a feedback signal to [-1.0, 1.0] range.

        Args:
            feedback_type: One of 'explicit_rating', 'override', 'acceptance', 'adjustment'
            raw_value: Raw signal value. For explicit_rating, this is 1-5.
                       For adjustment, this is already in [-1, 1].
                       Ignored for override and acceptance.

        Returns:
            Normalized signal in [-1.0, 1.0]

        Raises:
            ValueError: If feedback_type is invalid or raw_value is out of bounds.
        """
        if feedback_type not in self.VALID_FEEDBACK_TYPES:
            raise ValueError(
                f"Invalid feedback_type '{feedback_type}'. "
                f"Must be one of {self.VALID_FEEDBACK_TYPES}"
            )

        if feedback_type == "explicit_rating":
            if raw_value < 1 or raw_value > 5:
                raise ValueError(
                    f"explicit_rating must be between 1 and 5, got {raw_value}"
                )
            return (raw_value - 3) / 2.0

        elif feedback_type == "override":
            return -1.0

        elif feedback_type == "acceptance":
            return 1.0

        elif feedback_type == "adjustment":
            if raw_value < -1.0 or raw_value > 1.0:
                raise ValueError(
                    f"adjustment signal must be between -1.0 and 1.0, got {raw_value}"
                )
            return float(raw_value)

    def collect_feedback(
        self,
        member: str,
        feedback_type: str,
        context: Dict[str, Any],
        raw_value: float = 0.0,
        store: bool = True,
    ) -> FeedbackEvent:
        """Collect feedback and create a FeedbackEvent.

        Normalizes the signal and optionally stores it in DynamoDB.

        Args:
            member: Family member name (e.g., "rajesh", "priya")
            feedback_type: One of 'explicit_rating', 'override', 'acceptance', 'adjustment'
            context: Context dict describing what the feedback is about
            raw_value: Raw signal value (interpretation depends on feedback_type)
            store: Whether to persist the event in DynamoDB

        Returns:
            FeedbackEvent with normalized signal_value

        Raises:
            ValueError: If feedback_type or raw_value is invalid.
        """
        signal_value = self.normalize_signal(feedback_type, raw_value)

        event = FeedbackEvent(
            event_id=str(uuid.uuid4()),
            member=member,
            feedback_type=feedback_type,
            context=context,
            signal_value=signal_value,
            timestamp=datetime.now(timezone.utc),
        )

        if store:
            self._store_event(event)

        return event

    def _store_event(self, event: FeedbackEvent) -> None:
        """Store a FeedbackEvent in DynamoDB.

        Uses member as partition key and timestamp as sort key.
        """
        config = get_config()
        item = {
            "member": event.member,
            "timestamp": event.timestamp.isoformat(),
            "event_id": event.event_id,
            "feedback_type": event.feedback_type,
            "context": event.context,
            "signal_value": event.signal_value,
            "ttl": calculate_ttl(config.feedback_rolling_window_days),
        }
        self.table.put_item(Item=serialize_for_dynamo(item))

    def get_recent_feedback(
        self, member: str, limit: int = 50
    ) -> List[FeedbackEvent]:
        """Retrieve recent feedback events for a family member.

        Args:
            member: Family member name
            limit: Maximum number of events to return

        Returns:
            List of FeedbackEvent objects, most recent first.
        """
        response = self.table.query(
            KeyConditionExpression=Key("member").eq(member),
            ScanIndexForward=False,  # Most recent first
            Limit=limit,
        )

        events = []
        for item in response.get("Items", []):
            event = FeedbackEvent(
                event_id=item.get("event_id", ""),
                member=item.get("member", member),
                feedback_type=item.get("feedback_type", ""),
                context=item.get("context", {}),
                signal_value=float(item.get("signal_value", 0.0)),
                timestamp=datetime.fromisoformat(item["timestamp"])
                if "timestamp" in item
                else datetime.now(timezone.utc),
            )
            events.append(event)

        return events
