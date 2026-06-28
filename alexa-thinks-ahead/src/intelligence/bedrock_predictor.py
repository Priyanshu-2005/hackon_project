"""Bedrock Claude Sonnet powered CSV prediction.

Enhances the statistical CSV predictor by sending the computed predictions
and a summary of the household's weekly patterns to Amazon Bedrock Claude
Sonnet for:
  * Richer, context-aware reasoning for each proactive action
  * Confidence adjustments based on the AI's judgement
  * Additional proactive action suggestions the stats might miss

Falls back gracefully to the pure statistical derivation when Bedrock is
unavailable (no credentials, model access not granted, timeout, etc.).

This is the key integration point between the CSV learning feature and
Amazon Bedrock — making it visible that Alexa's intelligence is powered
by Claude Sonnet, not just rule-based code.
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from src.utils.config import get_config
from src.utils.logging import get_logger

logger = get_logger(__name__)

# In-memory cache of successful AI predictions, keyed by a hash of the routine
# predictions. Lets the presenter "warm up" once (the slow first call) and get
# instant results on every re-run / re-deploy during the demo.
_CACHE: Dict[str, Dict[str, Any]] = {}

# The valid action types the frontend can render. Claude must pick from these.
VALID_ACTION_TYPES = [
    "geyser_preheat",
    "security_arm",
    "ac_precool",
    "comfort_lighting",
    "energy_optimization",
]

# Device IDs the frontend scene knows about.
VALID_DEVICES = [
    "smart_geyser",
    "smart_lock",
    "security_camera",
    "living_room_ac",
    "smart_lights",
    "inverter_ups",
    "echo_devices",
    "kitchen_hub",
    "water_purifier",
    "smart_tv",
]

SYSTEM_PROMPT = """You are Alexa's proactive intelligence engine, powered by Amazon Bedrock Claude Sonnet.

Given a household's recurring daily routines (detected from their last week's activity log), generate a list of anticipatory proactive actions that Alexa should take TODAY.

Rules:
1. Each action ANTICIPATES a routine — it fires BEFORE the routine occurs (e.g. pre-heat water before wake-up, pre-cool before arrival).
2. Use ONLY these actionTypes: {action_types}
3. Use ONLY these targetDevices: {devices}
4. triggerTime is in MINUTES SINCE MIDNIGHT (e.g. 06:15 = 375).
5. Provide warm, family-friendly reasoning explaining WHY Alexa is acting proactively.
6. Confidence should reflect how reliably the routine recurs (0.0 to 1.0).
7. Keep each "reasoning" to ONE short sentence. Return AT MOST 6 actions. Output ONLY the JSON, no prose before or after.

Respond with ONLY valid JSON matching this schema:
{{
  "actions": [
    {{
      "name": "string (human-readable action name)",
      "actionType": "one of the valid types above",
      "triggerTime": integer (minutes since midnight),
      "targetDevice": "one of the valid devices above",
      "category": "string (climate|lighting|security|utility|power|entertainment|assistant)",
      "room": "string",
      "confidence": float 0-1,
      "reasoning": "string (family-friendly explanation of why Alexa is doing this)",
      "announcement": {{
        "elder": "optional message for elderly family members",
        "parent": "optional message for parents",
        "child": "optional message for children"
      }}
    }}
  ],
  "model_reasoning": "Brief explanation of your overall analysis approach"
}}"""


def _build_prompt(predictions: List[Dict[str, Any]], stats_actions: List[Dict[str, Any]]) -> str:
    """Build the Claude prompt from predictions and statistical baseline."""
    # Summarize routines
    routines_summary = "## Detected Household Routines (from last week's data)\n\n"
    for p in predictions:
        routines_summary += (
            f"- {p['member']}: {p['event_type']} in {p['room']} at ~{p['predicted_time']} "
            f"(confidence: {p['confidence']}, seen {p['days_observed']} days, "
            f"devices: {', '.join(p.get('devices', []))})\n"
        )

    # Show the statistical baseline
    stats_summary = "\n## Statistical Baseline Actions (for reference)\n\n"
    for a in stats_actions:
        h, m = divmod(a["triggerTime"], 60)
        stats_summary += f"- {a['name']} at {h:02d}:{m:02d} → {a['targetDevice']} ({a['reasoning']})\n"

    prompt = (
        f"{routines_summary}\n{stats_summary}\n"
        "Based on the above routines, generate the optimal set of proactive actions "
        "Alexa should take today. Improve on the statistical baseline where possible — "
        "adjust timings, refine reasoning to be more contextual and family-aware, "
        "and add actions if the data supports them.\n\n"
        "Remember: actions should ANTICIPATE routines (fire before they happen). "
        "Use the Sharma family context: Rajesh and Priya are working parents, "
        "Arjun (14) has online classes, Ananya (10) has activities, "
        "Dadaji and Dadiji are elderly and need comfort."
    )
    return prompt


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract a JSON object from model output.

    Models (Mistral, Llama, etc.) sometimes wrap JSON in markdown fences or
    add prose around it. This pulls out the first balanced ``{...}`` block and
    parses it. Returns an empty dict on failure.
    """
    if not text:
        return {}
    # Direct parse first.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip common markdown fences.
    cleaned = text.strip()
    if "```" in cleaned:
        # Take the content between the first pair of fences.
        parts = cleaned.split("```")
        for part in parts:
            p = part.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                try:
                    return json.loads(p)
                except json.JSONDecodeError:
                    continue
    # Fall back to the first {...} span.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def predict_with_bedrock(
    predictions: List[Dict[str, Any]],
    stats_actions: List[Dict[str, Any]],
    client=None,
) -> Dict[str, Any]:
    """Invoke Bedrock Claude to generate AI-powered proactive actions.

    Args:
        predictions: The routine predictions from the statistical predictor.
        stats_actions: The statistically derived proactive actions (fallback).
        client: Optional boto3 bedrock-runtime client (injectable for testing).

    Returns:
        Dict with:
          - ``proactive_actions``: The final list of actions (from AI or fallback).
          - ``ai_enhanced``: Boolean indicating whether Bedrock was used.
          - ``model_reasoning``: Claude's explanation (empty if fallback).
          - ``model_id``: The Bedrock model used.
    """
    config = get_config()

    # Return a cached AI result if we've already computed one for these routines.
    cache_key = hashlib.sha256(
        (config.bedrock_model_id + json.dumps(predictions, sort_keys=True, default=str)).encode()
    ).hexdigest()
    if cache_key in _CACHE:
        logger.info("Returning cached Bedrock prediction")
        return _CACHE[cache_key]

    try:
        from botocore.config import Config as BotoConfig
        from botocore.exceptions import ClientError, ReadTimeoutError
        import boto3

        boto_config = BotoConfig(
            read_timeout=60,  # Bedrock latency in some regions is high/variable
            retries={"max_attempts": 1},
        )

        bedrock = client or boto3.client(
            "bedrock-runtime",
            region_name=config.bedrock_region,
            config=boto_config,
        )

        system_prompt = SYSTEM_PROMPT.format(
            action_types=", ".join(VALID_ACTION_TYPES),
            devices=", ".join(VALID_DEVICES),
        )

        user_prompt = _build_prompt(predictions, stats_actions)

        # Use the Converse API — a single, model-agnostic interface that works
        # across Mistral, Llama, Amazon Nova, Anthropic Claude, etc. The model
        # is chosen via BEDROCK_MODEL_ID; no per-model request formatting needed.
        start = time.time()
        response = bedrock.converse(
            modelId=config.bedrock_model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={"maxTokens": 2048, "temperature": 0.3},
        )
        latency = round((time.time() - start) * 1000)

        # Converse returns a uniform shape regardless of model.
        text = response["output"]["message"]["content"][0]["text"]

        # Models sometimes wrap JSON in markdown fences or prose — extract the
        # JSON object defensively.
        parsed = _extract_json(text)
        ai_actions = parsed.get("actions", [])
        model_reasoning = parsed.get("model_reasoning", "")

        # Validate each action has the required fields
        valid_actions = []
        for a in ai_actions:
            if (
                isinstance(a.get("triggerTime"), (int, float))
                and a.get("targetDevice") in VALID_DEVICES
                and a.get("actionType") in VALID_ACTION_TYPES
            ):
                a["triggerTime"] = int(a["triggerTime"])
                if "announcement" not in a:
                    a["announcement"] = {}
                valid_actions.append(a)

        if not valid_actions:
            # Claude returned something but no valid actions — fall back
            logger.warning("Bedrock returned no valid actions, falling back to stats")
            return {
                "proactive_actions": stats_actions,
                "ai_enhanced": False,
                "model_reasoning": f"Claude response invalid, used statistical fallback. Raw: {text[:200]}",
                "model_id": config.bedrock_model_id,
                "latency_ms": latency,
            }

        valid_actions.sort(key=lambda a: a["triggerTime"])

        logger.info(
            f"Bedrock prediction: {len(valid_actions)} actions, "
            f"latency={latency}ms, model={config.bedrock_model_id}"
        )

        result = {
            "proactive_actions": valid_actions,
            "ai_enhanced": True,
            "model_reasoning": model_reasoning,
            "model_id": config.bedrock_model_id,
            "latency_ms": latency,
        }
        _CACHE[cache_key] = result
        return result

    except Exception as e:
        logger.warning(f"Bedrock prediction failed ({type(e).__name__}: {e}), using statistical fallback")
        return {
            "proactive_actions": stats_actions,
            "ai_enhanced": False,
            "model_reasoning": f"Bedrock unavailable ({type(e).__name__}), used statistical derivation.",
            "model_id": config.bedrock_model_id,
            "latency_ms": 0,
        }
