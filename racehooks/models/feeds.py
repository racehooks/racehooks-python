"""Pydantic models for RaceHooks feed webhook payloads.

Each model corresponds to the ``data`` field of a RaceHooks webhook
envelope for a specific feed type. Numeric values are delivered as
strings. All models permit extra fields (``extra="allow"``) so that
new fields never break parsing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Feed(BaseModel):
    """Base for all feed data models — tolerant of unknown fields."""

    model_config = ConfigDict(extra="allow")


class WeatherData(_Feed):
    """``weatherdata`` — circuit weather, updated ~every 30s."""

    air_temp: Optional[str] = Field(default=None, alias="AirTemp")
    humidity: Optional[str] = Field(default=None, alias="Humidity")
    pressure: Optional[str] = Field(default=None, alias="Pressure")
    rainfall: Optional[str] = Field(default=None, alias="Rainfall")
    track_temp: Optional[str] = Field(default=None, alias="TrackTemp")
    wind_direction: Optional[str] = Field(default=None, alias="WindDirection")
    wind_speed: Optional[str] = Field(default=None, alias="WindSpeed")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class TrackStatus(_Feed):
    """``trackstatus`` — 1=Clear 2=Yellow 4=SC 6=VSC 7=VSC Ending."""

    status: Optional[str] = Field(default=None, alias="Status")
    message: Optional[str] = Field(default=None, alias="Message")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class SessionStatus(_Feed):
    """``sessionstatus`` — Started, Aborted, Finished, Finalised, Ends."""

    status: Optional[str] = Field(default=None, alias="Status")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class LapCount(_Feed):
    """``lapcount`` — current and total laps."""

    current_lap: Optional[int] = Field(default=None, alias="CurrentLap")
    total_laps: Optional[int] = Field(default=None, alias="TotalLaps")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class DriverEntry(_Feed):
    """A single driver in the ``driverlist`` feed."""

    racing_number: Optional[str] = Field(default=None, alias="RacingNumber")
    tla: Optional[str] = Field(default=None, alias="Tla")
    team_name: Optional[str] = Field(default=None, alias="TeamName")
    team_colour: Optional[str] = Field(default=None, alias="TeamColour")
    first_name: Optional[str] = Field(default=None, alias="FirstName")
    last_name: Optional[str] = Field(default=None, alias="LastName")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


# Feeds whose payloads are keyed/nested in ways better left as raw dicts are
# represented as permissive models so callers can still index into ``data``.
class TimingData(_Feed):
    """``timingdata`` — lap/sector times, gaps, speed traps (per driver)."""

    lines: Optional[Dict[str, Any]] = Field(default=None, alias="Lines")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class DriverList(_Feed):
    """``driverlist`` — keyed by racing number → :class:`DriverEntry`."""

    model_config = ConfigDict(extra="allow")


class CurrentTyres(_Feed):
    """``currenttyres`` — current compound per driver."""

    model_config = ConfigDict(extra="allow")


class RaceControlMessages(_Feed):
    """``racecontrolmessages`` — safety car, flags, penalties."""

    messages: Optional[Any] = Field(default=None, alias="Messages")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsStrategy(_Feed):
    """``analytics.strategy`` — per-lap strategy signals (race/sprint only).

    Delivered once per lap for every driver. Fires independently of timingdata.
    """

    feed: str = "analytics.strategy"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    race_id: Optional[str] = Field(default=None, alias="raceId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    regulations_era: Optional[str] = Field(default=None, alias="regulationsEra")
    safety_car_probability: Optional[float] = Field(default=None, alias="safetyCarProbability")
    drivers: Optional[List[Any]] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsRaceOdds(_Feed):
    """``analytics.race-odds`` — per-lap CTMC outcome probabilities (race/sprint only).

    Includes per-driver positionDistribution, podium/points odds, H2H vs teammate,
    and a top-level ``pairs`` array with same-constructor H2H probabilities.
    """

    feed: str = "analytics.race-odds"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    race_id: Optional[str] = Field(default=None, alias="raceId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    regulations_era: Optional[str] = Field(default=None, alias="regulationsEra")
    drivers: Optional[List[Any]] = None
    pairs: Optional[List[Any]] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsGapProjection(_Feed):
    """``analytics.gap-projection`` — Monte Carlo projected gap to race leader.

    Five percentile bands (p10–p90) plus P(lapped) per driver. Race/sprint only.
    """

    feed: str = "analytics.gap-projection"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    race_id: Optional[str] = Field(default=None, alias="raceId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    regulations_era: Optional[str] = Field(default=None, alias="regulationsEra")
    drivers: Optional[List[Any]] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsTireStrategy(_Feed):
    """``analytics.tire-strategy`` — next-compound probabilities.

    Sparse — fires only for drivers whose pitStopProbability exceeds the
    approach threshold (~0.25). Includes compound probability distribution.
    """

    feed: str = "analytics.tire-strategy"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    race_id: Optional[str] = Field(default=None, alias="raceId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    regulations_era: Optional[str] = Field(default=None, alias="regulationsEra")
    drivers: Optional[List[Any]] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsConstructor(_Feed):
    """``analytics.constructor`` — constructor-level expected points (race/sprint only).

    Computed from discrete joint position distribution convolution across both drivers.
    """

    feed: str = "analytics.constructor"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    race_id: Optional[str] = Field(default=None, alias="raceId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    regulations_era: Optional[str] = Field(default=None, alias="regulationsEra")
    constructors: Optional[List[Any]] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsChampionshipProbability(_Feed):
    """``analytics.championship-probability`` — post-race WDC win probability.

    Delivered once after each race when the post-race inference pipeline completes.
    ``after_race_id`` identifies which race triggered the computation.
    """

    feed: str = "analytics.championship-probability"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    race_id: Optional[str] = Field(default=None, alias="raceId")
    after_race_id: Optional[str] = Field(default=None, alias="afterRaceId")
    utc: Optional[str] = None
    drivers: Optional[List[Any]] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsQualifying(_Feed):
    """``analytics.qualifying`` — per-lap-improvement qualifying intelligence.

    Fires after each personal best lap during qualifying. Includes per-sector
    fastest probabilities, pole probability, and pace deltas vs session best.
    """

    feed: str = "analytics.qualifying"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    race_id: Optional[str] = Field(default=None, alias="raceId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    sectors: Optional[Any] = None
    drivers: Optional[List[Any]] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


__all__ = [
    "WeatherData",
    "TrackStatus",
    "SessionStatus",
    "LapCount",
    "DriverEntry",
    "DriverList",
    "TimingData",
    "CurrentTyres",
    "RaceControlMessages",
    "AnalyticsStrategy",
    "AnalyticsRaceOdds",
    "AnalyticsGapProjection",
    "AnalyticsTireStrategy",
    "AnalyticsConstructor",
    "AnalyticsChampionshipProbability",
    "AnalyticsQualifying",
]
