"""Tests for the CSV event predictor and the /predict/events endpoint."""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intelligence.csv_predictor import parse_and_validate, predict, derive_proactive_actions
from src.handlers.api_handler import lambda_handler


FIXED_TODAY = date(2024, 6, 14)


def _d(days_ago: int) -> str:
    return (FIXED_TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _csv(rows, header="date,time,member,event_type,room,devices"):
    return header + "\n" + "\n".join(rows)


# ── Validation ────────────────────────────────────────────────────────────

def test_valid_csv_parses_with_no_errors():
    text = _csv([
        f"{_d(1)},07:00,Rajesh,Wake up,Master Bedroom,Lights|Geyser",
        f"{_d(2)},07:05,Rajesh,Wake up,Master Bedroom,Lights",
    ])
    rows, errors = parse_and_validate(text, today=FIXED_TODAY)
    assert errors == []
    assert len(rows) == 2
    assert rows[0]["minutes"] == 7 * 60


def test_missing_required_column_is_rejected():
    text = _csv([f"{_d(1)},07:00,Rajesh,Wake up"], header="date,time,member,event_type")
    rows, errors = parse_and_validate(text, today=FIXED_TODAY)
    assert rows == []
    assert any("Missing required column" in e for e in errors)


def test_today_date_is_rejected():
    text = _csv([f"{_d(0)},07:00,Rajesh,Wake up,Master Bedroom,Lights"])
    rows, errors = parse_and_validate(text, today=FIXED_TODAY)
    assert rows == []
    assert any("today or in the future" in e for e in errors)


def test_future_date_is_rejected():
    future = (FIXED_TODAY + timedelta(days=2)).strftime("%Y-%m-%d")
    text = _csv([f"{future},07:00,Rajesh,Wake up,Master Bedroom,Lights"])
    rows, errors = parse_and_validate(text, today=FIXED_TODAY)
    assert rows == []
    assert any("today or in the future" in e for e in errors)


def test_date_older_than_a_week_is_rejected():
    text = _csv([f"{_d(9)},07:00,Rajesh,Wake up,Master Bedroom,Lights"])
    rows, errors = parse_and_validate(text, today=FIXED_TODAY)
    assert rows == []
    assert any("older than 7 days" in e for e in errors)


def test_invalid_time_is_rejected():
    text = _csv([f"{_d(1)},25:99,Rajesh,Wake up,Master Bedroom,Lights"])
    rows, errors = parse_and_validate(text, today=FIXED_TODAY)
    assert any("invalid time" in e for e in errors)


def test_empty_csv_is_rejected():
    rows, errors = parse_and_validate("", today=FIXED_TODAY)
    assert rows == []
    assert errors


# ── Prediction ────────────────────────────────────────────────────────────

def test_recurring_event_predicted_with_average_time():
    text = _csv([
        f"{_d(1)},07:00,Rajesh,Wake up,Master Bedroom,Lights",
        f"{_d(2)},07:10,Rajesh,Wake up,Master Bedroom,Geyser",
        f"{_d(3)},07:20,Rajesh,Wake up,Master Bedroom,Lights",
    ])
    rows, errors = parse_and_validate(text, today=FIXED_TODAY)
    assert errors == []
    result = predict(rows)

    assert result["days_analyzed"] == 3
    assert len(result["predictions"]) == 1
    p = result["predictions"][0]
    assert p["member"] == "Rajesh"
    assert p["event_type"] == "Wake up"
    assert p["predicted_time"] == "07:10"  # average of 07:00/07:10/07:20
    assert p["confidence"] == 1.0
    assert p["days_observed"] == 3
    assert set(p["devices"]) == {"Lights", "Geyser"}


def test_confidence_reflects_fraction_of_days():
    # 'Wake up' on 3 days, 'TV time' on only 1 of those 3 days.
    text = _csv([
        f"{_d(1)},07:00,Arjun,Wake up,Kids Room,Lights",
        f"{_d(2)},07:00,Arjun,Wake up,Kids Room,Lights",
        f"{_d(3)},07:00,Arjun,Wake up,Kids Room,Lights",
        f"{_d(1)},20:00,Arjun,TV time,Living Room,TV",
    ])
    rows, _ = parse_and_validate(text, today=FIXED_TODAY)
    result = predict(rows)
    # Only the recurring (2+ day) routine is predicted.
    types = {p["event_type"] for p in result["predictions"]}
    assert "Wake up" in types
    assert "TV time" not in types


def test_predictions_sorted_by_time():
    text = _csv([
        f"{_d(1)},22:00,Priya,Bedtime,Master Bedroom,AC",
        f"{_d(2)},22:00,Priya,Bedtime,Master Bedroom,AC",
        f"{_d(1)},06:00,Priya,Wake up,Master Bedroom,Lights",
        f"{_d(2)},06:00,Priya,Wake up,Master Bedroom,Lights",
    ])
    rows, _ = parse_and_validate(text, today=FIXED_TODAY)
    result = predict(rows)
    times = [p["predicted_minutes"] for p in result["predictions"]]
    assert times == sorted(times)


# ── Proactive action derivation ───────────────────────────────────────────

def _recurring(member, etype, room, times):
    """Build rows for a routine seen across len(times) days."""
    return [
        f"{_d(i + 1)},{t},{member},{etype},{room},Lights"
        for i, t in enumerate(times)
    ]


def test_geyser_preheat_45min_before_earliest_wake():
    rows = (
        _recurring("Priya", "Wake up", "Master Bedroom", ["06:00", "06:00"])
        + _recurring("Rajesh", "Wake up", "Master Bedroom", ["07:00", "07:00"])
    )
    valid, errors = parse_and_validate(_csv(rows), today=FIXED_TODAY)
    assert errors == []
    actions = derive_proactive_actions(predict(valid)["predictions"])
    geyser = next(a for a in actions if a["actionType"] == "geyser_preheat")
    # Earliest wake is 06:00 (360 min) -> 360 - 45 = 315 = 05:15
    assert geyser["triggerTime"] == 315
    assert geyser["targetDevice"] == "smart_geyser"


def test_security_arm_at_last_leave_time():
    rows = (
        _recurring("Rajesh", "Leave home", "Balcony", ["08:00", "08:00"])
        + _recurring("Priya", "Leave home", "Balcony", ["09:00", "09:00"])
    )
    valid, _ = parse_and_validate(_csv(rows), today=FIXED_TODAY)
    actions = derive_proactive_actions(predict(valid)["predictions"])
    arm = next(a for a in actions if a["actionType"] == "security_arm")
    assert arm["triggerTime"] == 9 * 60  # last leave (09:00)


def test_precool_30min_before_earliest_arrival():
    rows = _recurring("Rajesh", "Arrive home", "Balcony", ["18:30", "18:30"])
    valid, _ = parse_and_validate(_csv(rows), today=FIXED_TODAY)
    actions = derive_proactive_actions(predict(valid)["predictions"])
    precool = next(a for a in actions if a["actionType"] == "ac_precool")
    assert precool["triggerTime"] == 18 * 60 + 30 - 30  # 18:00
    assert precool["targetDevice"] == "living_room_ac"


def test_actions_have_required_scheduler_fields():
    rows = _recurring("Rajesh", "Wake up", "Master Bedroom", ["07:00", "07:00"])
    valid, _ = parse_and_validate(_csv(rows), today=FIXED_TODAY)
    actions = derive_proactive_actions(predict(valid)["predictions"])
    assert actions
    for a in actions:
        for field in ("name", "actionType", "triggerTime", "targetDevice",
                      "category", "room", "reasoning", "announcement"):
            assert field in a, f"missing {field}"
        assert isinstance(a["triggerTime"], int)
        assert isinstance(a["announcement"], dict)


def test_endpoint_returns_proactive_actions():
    today = datetime.now().date()
    d1 = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    d2 = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    text = (
        "date,time,member,event_type,room,devices\n"
        f"{d1},07:00,Rajesh,Wake up,Master Bedroom,Lights\n"
        f"{d2},07:00,Rajesh,Wake up,Master Bedroom,Lights\n"
    )
    event = {
        "httpMethod": "POST",
        "path": "/predict/events",
        "pathParameters": {},
        "body": json.dumps({"csv": text}),
    }
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "proactive_actions" in body
    assert any(a["actionType"] == "geyser_preheat" for a in body["proactive_actions"])


# ── Endpoint ──────────────────────────────────────────────────────────────
def test_endpoint_rejects_invalid_csv():
    event = {
        "httpMethod": "POST",
        "path": "/predict/events",
        "pathParameters": {},
        "body": json.dumps({"csv": "not,a,valid,header\n1,2,3,4"}),
    }
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "details" in body


def test_endpoint_requires_csv_field():
    event = {
        "httpMethod": "POST",
        "path": "/predict/events",
        "pathParameters": {},
        "body": json.dumps({}),
    }
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400


def test_endpoint_predicts_with_real_today():
    # Use dates relative to the real current date so the endpoint (which uses
    # the real "today") accepts them.
    today = datetime.now().date()
    d1 = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    d2 = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    text = (
        "date,time,member,event_type,room,devices\n"
        f"{d1},07:00,Rajesh,Wake up,Master Bedroom,Lights\n"
        f"{d2},07:00,Rajesh,Wake up,Master Bedroom,Lights\n"
    )
    event = {
        "httpMethod": "POST",
        "path": "/predict/events",
        "pathParameters": {},
        "body": json.dumps({"csv": text}),
    }
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["rows_analyzed"] == 2
    assert len(body["predictions"]) == 1
    assert body["predictions"][0]["event_type"] == "Wake up"
