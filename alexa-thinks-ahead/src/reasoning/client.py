"""Bedrock Claude Sonnet reasoning client.

Interfaces with Amazon Bedrock Claude Sonnet for contextual reasoning
about smart home device orchestration. Implements exponential backoff
on failures and falls back to cached predictions on persistent timeouts.

Requirements:
    4.1: Invoke Bedrock Claude Sonnet with structured context
    4.6: 3-second timeout, fall back to cached predictions
    4.7: Discard malformed responses and don't execute actions
    12.1: Fall back to cached predictions on timeout
"""

import json
import time
from typing import Any, Dict, List, Optional

from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, ReadTimeoutError

import boto3

from src.models.intelligence import ReasoningRequest, ReasoningResponse
from src.utils.config import get_config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BedrockReasoningClient:
    """Interfaces with Amazon Bedrock Claude Sonnet for contextual reasoning.

    Builds structured prompts from ContextSnapshot, preferences, and autonomy
    configuration. Invokes the model with a 3-second timeout and retries with
    exponential backoff (1s, 2s, 4s) on transient failures. Discards malformed
    responses and returns an empty plan.
    """

    def __init__(self, client=None):
        config = get_config()
        self._config = config
        self._model_id = config.bedrock_model_id

        boto_config = BotoConfig(
            read_timeout=config.bedrock_timeout_seconds,
            retries={"max_attempts": 0},  # We handle retries ourselves
        )

        self._client = client or boto3.client(
            "bedrock-runtime",
            region_name=config.bedrock_region,
            config=boto_config,
        )

        self._cached_response: Optional[ReasoningResponse] = None

    def invoke_reasoning(self, request: ReasoningRequest) -> ReasoningResponse:
        """Invoke Claude Sonnet with a reasoning request.

        Implements exponential backoff on failures (1s, 2s, 4s).
        Falls back to cached response or empty plan on persistent failures.

        Args:
            request: The reasoning request containing context, preferences,
                     and autonomy configuration.

        Returns:
            A ReasoningResponse with actions and reasoning chain, or an
            empty response if all retries are exhausted.
        """
        prompt = self.build_prompt(request)

        for attempt in range(self._config.bedrock_max_retries):
            try:
                response = self._invoke_model(prompt)
                parsed = self._parse_response(response)
                if parsed is not None:
                    self._cached_response = parsed
                    return parsed
                # Malformed response — discard and return empty plan (Req 4.7)
                logger.warning("Malformed Bedrock response, discarding")
                return self._empty_response()
            except (ReadTimeoutError, ClientError) as e:
                wait = self._config.bedrock_backoff_base_seconds * (2 ** attempt)
                logger.warning(
                    f"Bedrock attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {wait}s"
                )
                time.sleep(wait)
            except Exception as e:
                logger.error(f"Unexpected error invoking Bedrock: {e}")
                break

        # All retries exhausted — fall back to cached or empty (Req 12.1)
        if self._cached_response:
            logger.info("Falling back to cached Bedrock response")
            return self._cached_response
        return self._empty_response()

    def build_prompt(self, request: ReasoningRequest) -> str:
        """Build a structured prompt for Claude Sonnet.

        Includes device states, active activities, patterns, preferences,
        and autonomy constraints so the model can reason contextually.

        Args:
            request: The reasoning request payload.

        Returns:
            A non-empty prompt string suitable for model invocation.
        """
        sections: List[str] = []

        # System context
        sections.append(
            "You are a proactive smart home AI managing 10 devices for the "
            "Sharma family. Analyze the current context and generate an action "
            "plan as JSON with keys: actions (list), reasoning_chain (str), "
            "confidence (float 0-1), explanation (str)."
        )

        # Current device states
        context = request.context
        if context.device_states:
            device_lines = []
            for device_id, state in context.device_states.items():
                device_lines.append(
                    f"  - {device_id}: status={state.status}, "
                    f"properties={state.properties}"
                )
            sections.append(
                "Current Device States:\n" + "\n".join(device_lines)
            )

        # Active activities
        if context.active_activities:
            activity_lines = []
            for activity in context.active_activities:
                activity_lines.append(
                    f"  - {activity.member_name}: {activity.activity} "
                    f"in {activity.location}"
                )
            sections.append(
                "Active Activities:\n" + "\n".join(activity_lines)
            )

        # Detected patterns
        if context.detected_patterns:
            pattern_lines = []
            for pattern in context.detected_patterns:
                pattern_lines.append(
                    f"  - {pattern.pattern_type} pattern "
                    f"(confidence={pattern.confidence:.2f}): "
                    f"devices={pattern.devices_involved}"
                )
            sections.append(
                "Detected Patterns:\n" + "\n".join(pattern_lines)
            )

        # Resource levels
        if context.resource_levels:
            sections.append(
                f"Resource Levels: {json.dumps(context.resource_levels)}"
            )

        # Environmental data
        if context.environmental:
            sections.append(
                f"Environmental: {json.dumps(context.environmental)}"
            )

        # Preferences
        if request.preferences:
            sections.append(
                f"Family Preferences: {json.dumps(request.preferences)}"
            )

        # Autonomy configuration
        if request.autonomy_config:
            sections.append(
                f"Autonomy Tier Limits: {json.dumps(request.autonomy_config)}"
            )

        # Event (if triggered by a specific event)
        if request.event:
            sections.append(
                f"Triggering Event: {json.dumps(request.event)}"
            )

        # Query type instruction
        sections.append(
            f"Query Type: {request.query_type}. "
            "Respond ONLY with valid JSON matching the schema above."
        )

        return "\n\n".join(sections)

    def generate_explanation(self, actions: List[Dict], reasoning: str) -> str:
        """Generate a natural language explanation for actions taken.

        Args:
            actions: List of action dictionaries that were executed.
            reasoning: The reasoning chain from the model.

        Returns:
            A human-readable explanation string.
        """
        if not actions:
            return "No actions were taken at this time."

        prompt = (
            "Generate a brief, friendly explanation for a family about "
            "the following smart home actions. Keep it under 2 sentences.\n\n"
            f"Actions: {json.dumps(actions)}\n"
            f"Reasoning: {reasoning}\n\n"
            "Explanation:"
        )

        try:
            response = self._invoke_model(prompt)
            content = response.get("content", [])
            if content:
                return content[0].get("text", reasoning)
        except Exception as e:
            logger.warning(f"Failed to generate explanation: {e}")

        # Fallback to the raw reasoning chain
        return reasoning

    def _invoke_model(self, prompt: str) -> Dict[str, Any]:
        """Call Bedrock invoke_model API.

        Args:
            prompt: The prompt string to send to Claude Sonnet.

        Returns:
            The parsed response body from Bedrock.

        Raises:
            ReadTimeoutError: If the request times out (3s).
            ClientError: If Bedrock returns an error.
        """
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            }
        )

        response = self._client.invoke_model(
            modelId=self._model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        return response_body

    def _parse_response(
        self, response: Dict[str, Any]
    ) -> Optional[ReasoningResponse]:
        """Parse Bedrock response into a ReasoningResponse.

        Returns None if the response is malformed (Req 4.7).

        Args:
            response: The raw response dict from Bedrock.

        Returns:
            A ReasoningResponse if parsing succeeds, None otherwise.
        """
        try:
            content = response.get("content", [])
            if not content:
                return None

            text = content[0].get("text", "")
            if not text:
                return None

            # Try to parse as structured JSON
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # Natural language response — wrap it
                data = {
                    "actions": [],
                    "reasoning_chain": text,
                    "confidence": 0.7,
                    "explanation": text,
                }

            return ReasoningResponse(
                actions=data.get("actions", []),
                reasoning_chain=data.get("reasoning_chain", ""),
                confidence=float(data.get("confidence", 0.5)),
                explanation=data.get("explanation", ""),
                latency_ms=0,
            )
        except Exception:
            return None

    def _empty_response(self) -> ReasoningResponse:
        """Return an empty response with no actions.

        Used as fallback when Bedrock is unreachable or returns
        malformed data.
        """
        return ReasoningResponse(
            actions=[],
            reasoning_chain="No reasoning available",
            confidence=0.0,
            explanation="Unable to generate reasoning at this time.",
            latency_ms=0,
        )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry point for the Reasoning Proxy function.

    Referenced by ``ReasoningProxyFunction`` in template.yaml
    (``src/reasoning/client.lambda_handler``). This is a thin proxy that
    lets you validate live Bedrock connectivity once deployed, without
    wiring the full context pipeline.

    Supported invocation payloads (``event``):
      * ``{"prompt": "<text>"}`` -> sends the raw prompt to Claude and
        returns the model's text.
      * Anything else -> returns a 400 describing the expected shape.

    Returns an API-Gateway-style dict so it can sit behind a proxy route
    or be invoked directly via the AWS CLI / console.

    Args:
        event: Invocation payload. May be a raw dict or an API Gateway
            event whose JSON body holds the payload.
        context: Lambda context (unused).

    Returns:
        ``{"statusCode": int, "body": <json string>}``.
    """
    # Accept either a direct dict or an API Gateway event with a JSON body.
    payload = event
    if isinstance(event, dict) and "body" in event and isinstance(event["body"], str):
        try:
            payload = json.loads(event["body"]) if event["body"] else {}
        except json.JSONDecodeError:
            payload = {}

    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    if not prompt:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"error": "Expected a JSON payload with a non-empty 'prompt' field."}
            ),
        }

    try:
        client = BedrockReasoningClient()
        model_response = client._invoke_model(prompt)
        content = model_response.get("content", [])
        text = content[0].get("text", "") if content else ""
        return {
            "statusCode": 200,
            "body": json.dumps(
                {"model_id": client._model_id, "text": text}
            ),
        }
    except Exception as e:  # pragma: no cover - exercised only against live AWS
        logger.error(f"Reasoning proxy invocation failed: {e}")
        return {
            "statusCode": 502,
            "body": json.dumps({"error": "Bedrock invocation failed"}),
        }
