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
            "feed": "weatherdata",
            "sessionId": "s1",
            "data": {"AirTemp": "24.1"},
        }
    )
    event = parse_event(payload)
    assert isinstance(event, WebhookEvent)
    assert event.feed == "weatherdata"
    assert event.session_id == "s1"
    assert event.data["AirTemp"] == "24.1"


def test_parse_raceevent_specializes():
    payload = {
        "feed": "raceevent",
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
        "feed": "sessiontiming",
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
    event = parse_event(b'{"feed":"trackstatus","sessionId":null,"data":{"Status":"1"}}')
    assert event.feed == "trackstatus"
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
        {"feed": "raceevent", "sessionId": "s1", "event": "session.start", "data": {}}
    )
    assert event.lap == 0


def test_parse_derived_analytics_feeds_specialize():
    from racehooks.models.feeds import (
        AnalyticsSectorPace,
        AnalyticsBattle,
        AnalyticsPitWindow,
        AnalyticsTrackConditions,
        AnalyticsPitQuality,
    )

    cases = {
        "analytics.sector-pace": AnalyticsSectorPace,
        "analytics.battle": AnalyticsBattle,
        "analytics.pit-window": AnalyticsPitWindow,
        "analytics.track-conditions": AnalyticsTrackConditions,
        "analytics.pit-quality": AnalyticsPitQuality,
    }
    for feed, cls in cases.items():
        ev = parse_event(
            {"feed": feed, "sessionId": "9724", "lap": 20, "utc": "t", "data": {"k": 1}}
        )
        assert isinstance(ev, cls)
        assert ev.data == {"k": 1}


def test_parse_weather_feeds_specialize():
    from racehooks.models.feeds import (
        WeatherRainEvent,
        WeatherForecastUpdate,
        WeatherTyreMismatch,
        WeatherStrategyDivergence,
        WeatherCompoundCrossoverAlert,
    )

    rain = parse_event(
        {"feed": "weather.rain_onset", "sessionId": "9724", "event": "rain_onset",
         "lap": 14, "utc": "t", "data": {"type": "rain_onset", "precipRateMmhr": 1.2}}
    )
    assert isinstance(rain, WeatherRainEvent)

    # rain_cleared maps to the same model
    assert isinstance(parse_event({"feed": "weather.rain_cleared", "sessionId": "9724"}), WeatherRainEvent)

    forecast = parse_event(
        {"feed": "weather.forecast_update", "sessionId": "9724", "event": "weather.forecast_update",
         "lap": 10, "utc": "t", "source": "open-meteo", "model": "ukmo_seamless",
         "currentPrecipRateMmhr": 0.0, "precipProbabilityPct": 65, "next60min": []}
    )
    assert isinstance(forecast, WeatherForecastUpdate)
    assert forecast.forecast_model == "ukmo_seamless"
    assert forecast.precip_probability_pct == 65.0

    mismatch = parse_event(
        {"feed": "weather.tyre_mismatch", "event": "weather.tyre_mismatch", "sessionId": "9724",
         "lap": 15, "utc": "t", "currentCompound": "MEDIUM", "severity": "urgent",
         "trigger": "raining_now", "expectedWetOnsetLap": 15,
         "rainProbabilityNext5Laps": 0.82, "intermediateWindowOpen": True}
    )
    assert isinstance(mismatch, WeatherTyreMismatch)
    assert mismatch.current_compound == "MEDIUM"
    assert mismatch.severity == "urgent"

    assert isinstance(parse_event({"feed": "weather.strategy_divergence", "sessionId": "9724"}), WeatherStrategyDivergence)

    crossover = parse_event(
        {"feed": "weather.compound_crossover_alert", "sessionId": "9724", "event": "x",
         "lap": 24, "utc": "t", "direction": "inter_to_slick", "confidence": 0.78,
         "evidence": {}, "rain_cleared_lap": 20, "estimated_laps_until_all_on_slick": 3}
    )
    assert isinstance(crossover, WeatherCompoundCrossoverAlert)
    assert crossover.rain_cleared_lap == 20
