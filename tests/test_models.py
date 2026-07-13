"""Pydantic model parsing tests."""

import json

import pytest

from racehooks import (
    DriverRef,
    Event,
    LapCount,
    QualifyingEvent,
    RaceEvent,
    RaceSummaryEvent,
    SessionTimingEvent,
    TrackStatus,
    WeatherData,
    WebhookEvent,
    parse_event,
)


def _driver_ref(num="1"):
    return {
        "driverId": "max-verstappen",
        "constructorId": "red-bull",
        "number": num,
        "tla": "VER",
        "name": "Max Verstappen",
        "team": "Red Bull",
    }


def test_parse_generic_feed_event():
    payload = json.dumps(
        {
            "feed": "weather.data",
            "sessionId": "s1",
            "data": {"AirTemp": "24.1"},
        }
    )
    event = parse_event(payload)
    assert isinstance(event, WebhookEvent)
    assert event.feed == "weather.data"
    assert event.session_id == "s1"
    assert event.data["AirTemp"] == "24.1"


def test_parse_events_race_specializes():
    payload = {
        "feed": "events.race",
        "sessionId": "s1",
        "event": "overtake",
        "lap": 5,
        "utc": "2026-03-16T15:00:00Z",
        "data": {"overtakingDriver": _driver_ref("1"), "overtakenDriver": _driver_ref("44")},
    }
    event = parse_event(payload)
    assert isinstance(event, RaceEvent)
    assert event.feed == "events.race"
    assert event.event == "overtake"
    assert event.lap == 5
    assert event.data["overtakingDriver"]["tla"] == "VER"


def test_parse_events_qualifying_specializes():
    payload = {
        "feed": "events.qualifying",
        "sessionId": "s1",
        "event": "qualifying.pole_position",
        "lap": 0,
        "utc": "2026-03-15T15:00:00Z",
        "data": {"driver": _driver_ref("1"), "marginToP2Ms": 122},
    }
    event = parse_event(payload)
    assert isinstance(event, QualifyingEvent)
    assert event.feed == "events.qualifying"
    assert event.event == "qualifying.pole_position"


def test_parse_session_timing_specializes():
    payload = {
        "feed": "session.timing",
        "sessionId": "s1",
        "utc": "2026-03-16T15:00:00Z",
        "lap": 3,
        "totalLaps": 57,
        "trackStatus": "green",
        "remaining": "01:28:00",
    }
    event = parse_event(payload)
    assert isinstance(event, SessionTimingEvent)
    assert event.feed == "session.timing"
    assert event.lap == 3
    assert event.total_laps == 57
    assert event.track_status == "green"
    # Unknown extra fields are preserved via extra="allow".
    assert event.remaining == "01:28:00"


def test_parse_results_race_summary_by_type_discriminator():
    # results.race-summary predates the feed envelope — dispatched on `type`.
    payload = {
        "type": "race.summary.complete",
        "raceId": "2026-bahrain-r1",
        "raceName": "Bahrain Grand Prix",
        "processedAt": "2026-03-16T17:30:00Z",
        "totalSamples": 123456,
        "maxSpeedKph": 342.1,
        "maxSpeedDriver": _driver_ref("1"),
    }
    event = parse_event(payload)
    assert isinstance(event, RaceSummaryEvent)
    assert event.feed == "results.race-summary"
    assert event.race_id == "2026-bahrain-r1"
    assert event.total_samples == 123456
    assert event.max_speed_driver.tla == "VER"


def test_parse_event_accepts_bytes():
    event = parse_event(b'{"feed":"session.track-status","sessionId":null,"data":{"Status":"1"}}')
    assert event.feed == "session.track-status"
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


def test_events_race_defaults_lap_to_zero():
    event = RaceEvent.model_validate(
        {"feed": "events.race", "sessionId": "s1", "event": "session.start", "data": {}}
    )
    assert event.lap == 0


def test_driver_ref_model():
    dr = DriverRef.model_validate(_driver_ref("16"))
    assert dr.driver_id == "max-verstappen"
    assert dr.constructor_id == "red-bull"
    assert dr.number == "16"
    assert dr.tla == "VER"
    assert dr.team == "Red Bull"
    # Per-driver analytics extras are preserved.
    extra = DriverRef.model_validate({**_driver_ref(), "truePaceSec": 91.2, "rank": 1})
    assert extra.model_dump().get("truePaceSec") == 91.2


def test_analytics_driver_lists_are_typed_driver_refs():
    from racehooks.models.feeds import AnalyticsStrategy

    ev = parse_event(
        {
            "feed": "analytics.strategy",
            "sessionId": "9724",
            "raceId": "2026-bahrain-r1",
            "lap": 20,
            "utc": "t",
            "regulationsEra": "2026",
            "drivers": [{**_driver_ref("1"), "pitStopProbability": 0.4}],
        }
    )
    assert isinstance(ev, AnalyticsStrategy)
    assert ev.race_id == "2026-bahrain-r1"
    assert isinstance(ev.drivers[0], DriverRef)
    assert ev.drivers[0].tla == "VER"
    assert ev.drivers[0].model_dump().get("pitStopProbability") == 0.4


def test_parse_derived_analytics_data_feeds_carry_session_and_lap_only():
    # Node parity: these 5 alert feeds carry sessionId + lap + utc (NO raceId).
    from racehooks.models.feeds import (
        AnalyticsBattle,
        AnalyticsPitQuality,
        AnalyticsPitWindow,
        AnalyticsSectorPace,
        AnalyticsTrackConditions,
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
            {
                "feed": feed,
                "sessionId": "9724",
                "lap": 20,
                "utc": "t",
                "data": {"k": 1},
            }
        )
        assert isinstance(ev, cls)
        assert ev.session_id == "9724"
        assert ev.lap == 20
        assert ev.data == {"k": 1}
        # These feeds have NO raceId field in the node contract.
        assert "race_id" not in cls.model_fields


def test_analytics_qualifying_has_no_lap_but_has_race_id():
    from racehooks.models.feeds import AnalyticsQualifying

    ev = parse_event(
        {
            "feed": "analytics.qualifying",
            "sessionId": "9724",
            "raceId": "2026-bahrain-r1",
            "utc": "t",
            "segment": "Q3",
            "circuitId": "bahrain",
            "sectors": {"s1": {"drivers": []}},
            "drivers": [_driver_ref("1")],
        }
    )
    assert isinstance(ev, AnalyticsQualifying)
    assert ev.session_id == "9724"
    assert ev.race_id == "2026-bahrain-r1"
    assert ev.segment == "Q3"
    assert ev.circuit_id == "bahrain"
    # Node's qualifying payload carries NO lap.
    assert "lap" not in AnalyticsQualifying.model_fields


def test_championship_probability_is_season_scoped():
    from racehooks.models.feeds import AnalyticsChampionshipProbability

    ev = parse_event(
        {
            "feed": "analytics.championship-probability",
            "seasonYear": 2026,
            "afterRaceId": "2026-bahrain-r1",
            "simulationsRun": 20000,
            "utc": "t",
            "drivers": [{**_driver_ref("1"), "scwp": 0.42}],
            "constructors": [{"constructorId": "red-bull", "ccwp": 0.55}],
        }
    )
    assert isinstance(ev, AnalyticsChampionshipProbability)
    assert ev.season_year == 2026
    assert ev.after_race_id == "2026-bahrain-r1"
    assert ev.simulations_run == 20000
    # No sessionId / raceId / lap on this season-level feed.
    assert "session_id" not in AnalyticsChampionshipProbability.model_fields
    assert "race_id" not in AnalyticsChampionshipProbability.model_fields
    assert "lap" not in AnalyticsChampionshipProbability.model_fields


def test_parse_new_analytics_feeds_specialize():
    from racehooks.models.feeds import (
        AnalyticsRaceDuration,
        AnalyticsRacePreview,
        AnalyticsTeamPoints,
        AnalyticsTruePace,
        AnalyticsWinningMargin,
    )

    true_pace = parse_event(
        {
            "feed": "analytics.true-pace",
            "sessionId": "9724",
            "raceId": "2026-bahrain-r1",
            "lap": 20,
            "utc": "t",
            "drivers": [{**_driver_ref("1"), "truePaceSec": 91.2, "rank": 1}],
        }
    )
    assert isinstance(true_pace, AnalyticsTruePace)
    assert isinstance(true_pace.drivers[0], DriverRef)

    duration = parse_event(
        {
            "feed": "analytics.race-duration",
            "sessionId": "9724",
            "raceId": "2026-bahrain-r1",
            "lap": 20,
            "utc": "t",
            "expectedRaceTimeMinutes": 92.5,
            "probabilityRedFlag": 0.08,
            "scDeployedCount": 1,
        }
    )
    assert isinstance(duration, AnalyticsRaceDuration)
    assert duration.expected_race_time_minutes == 92.5
    assert duration.sc_deployed_count == 1

    margin = parse_event(
        {
            "feed": "analytics.winning-margin",
            "sessionId": "9724",
            "raceId": "2026-bahrain-r1",
            "lap": 20,
            "utc": "t",
            "leadBattle": {
                "leader": _driver_ref("1"),
                "runnerUp": _driver_ref("16"),
                "currentMarginSec": 4.2,
                "expectedFinalMarginSec": 6.1,
                "scCollapseRisk": 0.3,
            },
        }
    )
    assert isinstance(margin, AnalyticsWinningMargin)
    assert margin.lead_battle.current_margin_sec == 4.2
    assert margin.lead_battle.leader.tla == "VER"

    team = parse_event(
        {
            "feed": "analytics.team-points",
            "sessionId": "9724",
            "raceId": "2026-bahrain-r1",
            "lap": 20,
            "utc": "t",
            "constructors": [{"constructorId": "red-bull", "expectedConstructorPoints": 33.0}],
        }
    )
    assert isinstance(team, AnalyticsTeamPoints)
    assert team.constructors[0]["constructorId"] == "red-bull"

    preview = parse_event(
        {
            "feed": "analytics.race-preview",
            "stage": "grid",
            "eventId": "2026-bahrain",
            "raceId": "2026-bahrain-r1",
            "circuitId": "bahrain",
            "utc": "t",
            "scheduledRaceLaps": 57,
            "drivers": [_driver_ref("1")],
        }
    )
    assert isinstance(preview, AnalyticsRacePreview)
    assert preview.stage == "grid"
    assert preview.circuit_id == "bahrain"
    assert preview.scheduled_race_laps == 57


def test_parse_weather_feeds_specialize():
    from racehooks.models.feeds import (
        WeatherCompoundCrossover,
        WeatherForecastUpdate,
        WeatherRainEvent,
        WeatherStrategyDivergence,
        WeatherTireMismatch,
    )

    rain = parse_event(
        {
            "feed": "weather.rain-onset",
            "sessionId": "9724",
            "lap": 14,
            "utc": "t",
            "data": {"precipRateMmhr": 1.2},
        }
    )
    assert isinstance(rain, WeatherRainEvent)
    assert rain.session_id == "9724"

    # rain-cleared maps to the same model
    assert isinstance(
        parse_event({"feed": "weather.rain-cleared", "sessionId": "9724"}), WeatherRainEvent
    )

    forecast = parse_event(
        {
            "feed": "weather.forecast-update",
            "sessionId": "9724",
            "lap": 10,
            "utc": "t",
            "source": "radar",
            "currentPrecipRateMmhr": 0.0,
            "precipProbabilityPct": 65,
            "rainExpectedInMin": 12,
            "next60min": [],
        }
    )
    assert isinstance(forecast, WeatherForecastUpdate)
    assert forecast.source == "radar"
    assert forecast.precip_probability_pct == 65.0
    assert forecast.rain_expected_in_min == 12

    mismatch = parse_event(
        {
            "feed": "weather.tire-mismatch",
            "sessionId": "9724",
            "lap": 15,
            "utc": "t",
            "driver": _driver_ref("1"),
            "currentCompound": "MEDIUM",
            "severity": "urgent",
            "trigger": "raining_now",
            "expectedWetOnsetLap": 15,
            "rainProbabilityNext5Laps": 0.82,
            "intermediateWindowOpen": True,
        }
    )
    assert isinstance(mismatch, WeatherTireMismatch)
    assert mismatch.current_compound == "MEDIUM"
    assert mismatch.severity == "urgent"
    assert mismatch.driver.tla == "VER"

    assert isinstance(
        parse_event({"feed": "weather.strategy-divergence", "sessionId": "9724"}),
        WeatherStrategyDivergence,
    )

    crossover = parse_event(
        {
            "feed": "weather.compound-crossover",
            "sessionId": "9724",
            "lap": 24,
            "utc": "t",
            "direction": "inter_to_slick",
            "confidence": 0.78,
            "evidence": {},
            "rainClearedLap": 20,
            "estimatedLapsUntilAllOnSlick": 3,
        }
    )
    assert isinstance(crossover, WeatherCompoundCrossover)
    assert crossover.rain_cleared_lap == 20
    assert crossover.estimated_laps_until_all_on_slick == 3


def test_rest_resource_models():
    event = Event.model_validate(
        {
            "eventId": "2026-bahrain",
            "name": "Bahrain Grand Prix",
            "officialName": "Formula 1 Bahrain Grand Prix 2026",
            "countryCode": "BHR",
            "type": "conventional",
            "roundText": "Round 1",
            "sessions": [
                {
                    "sessionId": "2026-bahrain-r1_Race",
                    "type": "race",
                    "name": "Race",
                    "status": "completed",
                    "startDate": "2026-03-16T15:00:00Z",
                    "endDate": "2026-03-16T17:00:00Z",
                    "gmtOffset": "+03:00",
                    "path": "2026/…/Race/",
                }
            ],
        }
    )
    assert event.event_id == "2026-bahrain"
    assert event.official_name.startswith("Formula 1")
    assert event.sessions[0].session_id == "2026-bahrain-r1_Race"
    assert event.sessions[0].gmt_offset == "+03:00"
