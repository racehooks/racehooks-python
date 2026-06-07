"""Pydantic model parsing tests."""

import json

import pytest

from racehooks import (
    LapCount,
    RaceEvent,
    SessionTimingEvent,
    TrackStatus,
    WeatherData,
    WebhookEvent,
    parse_event,
)


def test_parse_generic_feed_event():
    payload = json.dumps(
        {
            "type": "weatherdata",
            "sessionId": "s1",
            "data": {"AirTemp": "24.1"},
        }
    )
    event = parse_event(payload)
    assert isinstance(event, WebhookEvent)
    assert event.type == "weatherdata"
    assert event.session_id == "s1"
    assert event.data["AirTemp"] == "24.1"


def test_parse_raceevent_specializes():
    payload = {
        "type": "raceevent",
        "sessionId": "s1",
        "event": "overtake",
        "lap": 5,
        "utc": "2026-03-16T15:00:00Z",
        "data": {"overtakingDriver": "1", "overtakenDriver": "44"},
    }
    event = parse_event(payload)
    assert isinstance(event, RaceEvent)
    assert event.event == "overtake"
    assert event.lap == 5
    assert event.data["overtakingDriver"] == "1"


def test_parse_sessiontiming_specializes():
    payload = {
        "type": "sessiontiming",
        "sessionId": "s1",
        "utc": "2026-03-16T15:00:00Z",
        "lap": 3,
        "totalLaps": 57,
        "trackStatus": "green",
        "remaining": "01:28:00",
    }
    event = parse_event(payload)
    assert isinstance(event, SessionTimingEvent)
    assert event.lap == 3
    assert event.total_laps == 57
    assert event.track_status == "green"
    # Unknown extra fields are preserved via extra="allow".
    assert event.remaining == "01:28:00"


def test_parse_event_accepts_bytes():
    event = parse_event(b'{"type":"trackstatus","sessionId":null,"data":{"Status":"1"}}')
    assert event.type == "trackstatus"
    assert event.session_id is None


def test_parse_event_rejects_non_object():
    with pytest.raises(ValueError):
        parse_event("[]")


def test_weather_data_model_aliases():
    wd = WeatherData.model_validate(
        {"AirTemp": "24.1", "TrackTemp": "31.0", "Rainfall": "0", "Extra": "x"}
    )
    assert wd.air_temp == "24.1"
    assert wd.track_temp == "31.0"
    # Extra fields allowed for forward compatibility.
    assert wd.model_dump().get("Extra") == "x" or wd.Extra == "x"  # type: ignore[attr-defined]


def test_track_status_model():
    ts = TrackStatus.model_validate({"Status": "4", "Message": "SCDeployed"})
    assert ts.status == "4"
    assert ts.message == "SCDeployed"


def test_lap_count_model_coerces_ints():
    lc = LapCount.model_validate({"CurrentLap": "12", "TotalLaps": "57"})
    assert lc.current_lap == 12
    assert lc.total_laps == 57


def test_raceevent_defaults_lap_to_zero():
    event = RaceEvent.model_validate(
        {"type": "raceevent", "sessionId": "s1", "event": "session.start", "data": {}}
    )
    assert event.lap == 0
