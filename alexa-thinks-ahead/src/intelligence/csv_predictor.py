"""CSV-based event prediction for the demo.

Validates an uploaded CSV containing the household's **previous-week**
activity log and predicts **today's** likely events (with timing) by
detecting recurring daily patterns.

CSV schema (a header row is required; column order does not matter):

    date        YYYY-MM-DD   Day of the logged activity. Must fall within the
                             previous 7 days — NOT today and NOT a future date.
    time        HH:MM        24-hour local time the activity happened.
    member      str          Family member (e.g. Rajesh, Priya, Arjun).
    event_type  str          Activity label (e.g. "Wake up", "Online class").
    room        str          Room name (e.g. Kitchen, Study Room).
    devices     str          OPTIONAL. Pipe-separated device list,
                             e.g. "Lights|Geyser".

Prediction approach:
    Rows are grouped by (member, event_type, room). For each group we look at
    how many distinct days it occurred and the average time-of-day. The
    confidence is the fraction of analyzed days on which the routine appeared,
    and the predicted time is the average of the observed times.
"""

import csv
import io
import math
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

REQUIRED_COLUMNS = ["date", "time", "member", "event_type", "room"]
OPTIONAL_COLUMNS = ["devices"]

# How far back the history window may reach (in days, excluding today).
HISTORY_WINDOW_DAYS = 7


def _parse_time_to_minutes(value: str) -> Optional[int]:
    """Parse 'HH:MM' (or 'H:MM') into minutes since midnight, or None."""
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hours, minutes = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    return hours * 60 + minutes


def _minutes_to_hhmm(minutes: int) -> str:
    """Convert minutes since midnight to a zero-padded 'HH:MM' string."""
    minutes = max(0, min(1439, int(round(minutes))))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _parse_devices(value: str) -> List[str]:
    """Split a pipe/comma-separated devices cell into a clean list."""
    if not value:
        return []
    raw = value.replace(",", "|")
    return [d.strip() for d in raw.split("|") if d.strip()]


def parse_and_validate(
    csv_text: str, today: Optional[date] = None
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse and validate the uploaded CSV text.

    Args:
        csv_text: Raw CSV content (including the header row).
        today: The date treated as "today". Defaults to the server's
            current local date. Injectable for deterministic tests.

    Returns:
        ``(rows, errors)`` where ``rows`` is the list of validated row dicts
        (each with ``date``, ``minutes``, ``member``, ``event_type``,
        ``room``, ``devices``) and ``errors`` is a list of human-readable
        validation messages. When ``errors`` is non-empty the CSV is invalid
        and ``rows`` should not be used for prediction.
    """
    today = today or datetime.now().date()
    earliest = today - timedelta(days=HISTORY_WINDOW_DAYS)
    errors: List[str] = []

    text = (csv_text or "").strip()
    if not text:
        return [], ["CSV is empty. Upload a file with a header row and data."]

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], ["CSV has no header row."]

    headers = [h.strip().lower() for h in reader.fieldnames]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        return [], [
            f"Missing required column(s): {', '.join(missing)}. "
            f"Required columns are: {', '.join(REQUIRED_COLUMNS)}."
        ]

    rows: List[Dict[str, Any]] = []
    seen_dates = set()

    for i, raw in enumerate(reader, start=2):  # row 1 is the header
        # Normalize keys to lowercase/stripped.
        record = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}

        date_str = record.get("date", "")
        time_str = record.get("time", "")
        member = record.get("member", "")
        event_type = record.get("event_type", "")
        room = record.get("room", "")
        devices = _parse_devices(record.get("devices", ""))

        if not (date_str and time_str and member and event_type and room):
            errors.append(f"Row {i}: missing one or more required values.")
            continue

        # Date validation.
        try:
            row_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            errors.append(f"Row {i}: invalid date '{date_str}' (expected YYYY-MM-DD).")
            continue

        if row_date >= today:
            errors.append(
                f"Row {i}: date '{date_str}' is today or in the future. "
                "The CSV must contain only the previous week's data."
            )
            continue
        if row_date < earliest:
            errors.append(
                f"Row {i}: date '{date_str}' is older than {HISTORY_WINDOW_DAYS} days. "
                f"Only data from the last {HISTORY_WINDOW_DAYS} days is allowed."
            )
            continue

        # Time validation.
        minutes = _parse_time_to_minutes(time_str)
        if minutes is None:
            errors.append(f"Row {i}: invalid time '{time_str}' (expected HH:MM).")
            continue

        seen_dates.add(row_date)
        rows.append(
            {
                "date": row_date,
                "minutes": minutes,
                "member": member,
                "event_type": event_type,
                "room": room,
                "devices": devices,
            }
        )

    if not rows and not errors:
        errors.append("CSV contained a header but no data rows.")

    return rows, errors


def predict(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Predict today's events from validated historical rows.

    Groups rows by (member, event_type, room), then for each group computes
    the average time-of-day, a confidence (fraction of analyzed days the
    routine appeared on), and the union of devices involved.

    Args:
        rows: Validated rows from :func:`parse_and_validate`.

    Returns:
        Dict with ``predictions`` (sorted by predicted time), ``days_analyzed``,
        and ``rows_analyzed``.
    """
    all_dates = {r["date"] for r in rows}
    total_days = len(all_dates) or 1

    groups: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for r in rows:
        key = (r["member"], r["event_type"], r["room"])
        group = groups.setdefault(
            key,
            {
                "member": r["member"],
                "event_type": r["event_type"],
                "room": r["room"],
                "dates": set(),
                "minutes": [],
                "devices": [],
            },
        )
        group["dates"].add(r["date"])
        group["minutes"].append(r["minutes"])
        for d in r["devices"]:
            if d not in group["devices"]:
                group["devices"].append(d)

    predictions: List[Dict[str, Any]] = []
    for group in groups.values():
        days_observed = len(group["dates"])
        avg_minutes = sum(group["minutes"]) / len(group["minutes"])
        confidence = round(min(1.0, days_observed / total_days), 2)
        predictions.append(
            {
                "member": group["member"],
                "event_type": group["event_type"],
                "room": group["room"],
                "devices": group["devices"],
                "predicted_time": _minutes_to_hhmm(avg_minutes),
                "predicted_minutes": int(round(avg_minutes)),
                "confidence": confidence,
                "days_observed": days_observed,
            }
        )

    # Keep recurring routines (seen on 2+ distinct days). If the window is a
    # single day, nothing is "recurring" yet, so return everything.
    recurring = [p for p in predictions if p["days_observed"] >= 2]
    chosen = recurring if recurring else predictions
    chosen.sort(key=lambda p: (p["predicted_minutes"], -p["confidence"]))

    return {
        "predictions": chosen,
        "days_analyzed": total_days,
        "rows_analyzed": len(rows),
    }


# Devices/rooms used by the derived proactive actions. These device ids match
# the scene device ids the frontend FloorPlan2D / EventScheduler understand.
def _norm(event_type: str) -> str:
    return event_type.lower().strip()


def _find(predictions: List[Dict[str, Any]], needles: List[str]) -> List[Dict[str, Any]]:
    """Return predictions whose event_type contains any of the given substrings."""
    out = []
    for p in predictions:
        et = _norm(p["event_type"])
        if any(n in et for n in needles):
            out.append(p)
    return out


def derive_proactive_actions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Turn learned routines into Alexa's anticipatory proactive actions.

    This is the "thinks ahead" layer: instead of replaying the routine, it
    derives the proactive action Alexa would take *around* each routine
    (e.g. pre-heat the geyser before the family wakes, arm security once
    everyone has left, pre-cool before the first arrival home).

    Each returned action matches the shape the frontend ``EventScheduler``
    consumes: ``name``, ``actionType``, ``triggerTime`` (minutes since
    midnight), ``targetDevice``, ``category``, ``room``, ``reasoning``,
    ``announcement`` (with elder/parent/child variants), and ``confidence``.

    Args:
        predictions: Output of :func:`predict` (the ``predictions`` list).

    Returns:
        A list of proactive action dicts, sorted by trigger time.
    """
    actions: List[Dict[str, Any]] = []

    wakes = _find(predictions, ["wake"])
    leaves = _find(predictions, ["leave", "depart"])
    arrivals = _find(predictions, ["arrive", "return", "reach", "back home"])
    cooking = _find(predictions, ["cook"])

    # 1. Geyser pre-heat — 45 min before the earliest wake-up.
    if wakes:
        earliest = min(wakes, key=lambda p: p["predicted_minutes"])
        trigger = max(0, earliest["predicted_minutes"] - 45)
        actions.append({
            "name": "Geyser Pre-heat",
            "actionType": "geyser_preheat",
            "triggerTime": trigger,
            "targetDevice": "smart_geyser",
            "category": "utility",
            "room": "bath",
            "confidence": earliest["confidence"],
            "reasoning": (
                f"{earliest['member']} usually wakes around {earliest['predicted_time']}. "
                f"Pre-heating water 45 minutes ahead ensures it's ready."
            ),
            "announcement": {
                "elder": "Good morning! Hot water is ready for you.",
                "parent": f"Geyser warmed up — the family usually wakes around {earliest['predicted_time']}.",
            },
        })

    # 2. Security arm — when the last person leaves (house goes empty).
    if leaves:
        last_leave = max(leaves, key=lambda p: p["predicted_minutes"])
        actions.append({
            "name": "Security Arm",
            "actionType": "security_arm",
            "triggerTime": last_leave["predicted_minutes"],
            "targetDevice": "smart_lock",
            "category": "security",
            "room": "balcony",
            "confidence": last_leave["confidence"],
            "reasoning": (
                f"The household typically leaves by {last_leave['predicted_time']}. "
                f"Arming the lock and camera once everyone is out."
            ),
            "announcement": {
                "elder": "Security has been armed. You are safe inside.",
                "parent": "Everyone's out — I've armed the lock and camera.",
            },
        })

    # 3. Pre-cooling — 30 min before the earliest arrival home.
    if arrivals:
        first_arrival = min(arrivals, key=lambda p: p["predicted_minutes"])
        trigger = max(0, first_arrival["predicted_minutes"] - 30)
        actions.append({
            "name": "Pre-cooling Living Room",
            "actionType": "ac_precool",
            "triggerTime": trigger,
            "targetDevice": "living_room_ac",
            "category": "climate",
            "room": "livingRoom",
            "confidence": first_arrival["confidence"],
            "reasoning": (
                f"{first_arrival['member']} usually arrives around {first_arrival['predicted_time']}. "
                f"Pre-cooling 30 minutes ahead ensures a comfortable temperature on arrival."
            ),
            "announcement": {
                "parent": f"Cooling the living room before {first_arrival['member']} gets home.",
            },
        })

    # 4. Comfort lighting — 15 min before the first evening activity (>= 17:00),
    #    falling back to a sunset default of 17:45.
    evening = [p for p in predictions if p["predicted_minutes"] >= 17 * 60]
    if evening:
        anchor = min(evening, key=lambda p: p["predicted_minutes"])
        trigger = max(0, anchor["predicted_minutes"] - 15)
        conf = anchor["confidence"]
        reason = (
            f"Evening activity starts around {anchor['predicted_time']}. "
            f"Transitioning to warm lighting for comfort."
        )
    else:
        trigger = 17 * 60 + 45
        conf = 0.75
        reason = "Sunset approaching. Transitioning to warm indoor lighting for comfort."
    actions.append({
        "name": "Comfort Lighting",
        "actionType": "comfort_lighting",
        "triggerTime": trigger,
        "targetDevice": "smart_lights",
        "category": "lighting",
        "room": "livingRoom",
        "confidence": conf,
        "reasoning": reason,
        "announcement": {"elder": "Turning on warm lights for the evening."},
    })

    # 5. Energy optimization — peak tariff window (14:00), included whenever the
    #    home has any daytime routine to optimize around.
    daytime = [p for p in predictions if 11 * 60 <= p["predicted_minutes"] <= 17 * 60]
    if daytime or cooking:
        actions.append({
            "name": "Energy Optimization",
            "actionType": "energy_optimization",
            "triggerTime": 14 * 60,
            "targetDevice": "inverter_ups",
            "category": "power",
            "room": "utility",
            "confidence": round(sum(p["confidence"] for p in (daytime or predictions)) / len(daytime or predictions), 2),
            "reasoning": (
                "Peak electricity tariff begins around 14:00. "
                "Shifting non-essential loads to inverter backup to save cost."
            ),
            "announcement": {
                "parent": "Switched to inverter for non-essentials to save on peak tariff.",
            },
        })

    actions.sort(key=lambda a: a["triggerTime"])
    return actions
