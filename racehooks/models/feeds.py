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


class AnalyticsSectorPace(_Feed):
    """``analytics.sector-pace`` — per-driver sector anomaly detection (race/sprint).

    ``data`` is a SectorPaceSnapshot: per-sector deltas vs clean-lap baseline,
    anomaly flags, classified cause (RAIN/TIRE_CLIFF/INCIDENT), cross-driver correlation.
    """

    feed: str = "analytics.sector-pace"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    data: Optional[Any] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsBattle(_Feed):
    """``analytics.battle`` — head-to-head battle tracking (race/sprint).

    ``data`` is a BattleState: attacker/defender, gap, catch rate, laps to striking
    distance, and battleStatus (APPROACHING/STRIKING_RANGE/EQUAL_PACE/PULLING_AWAY).
    """

    feed: str = "analytics.battle"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    data: Optional[Any] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsPitWindow(_Feed):
    """``analytics.pit-window`` — per-driver optimal pit window (race/sprint).

    ``data`` is a PitWindowAlert plus ``pitCount``: status (OPEN/URGENT/CLOSING/CLOSED),
    pit probability, undercut viability, cliff risk, VSC/SC override reason.
    """

    feed: str = "analytics.pit-window"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    data: Optional[Any] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsTrackConditions(_Feed):
    """``analytics.track-conditions`` — per-sector wet/dry state (race/sprint).

    ``data`` is a SectorConditions: per-sector DRY/WET/DRYING, full-circuit-wet flag,
    intermediate-window-open, and crossover recommendation.
    """

    feed: str = "analytics.track-conditions"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    data: Optional[Any] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsPitQuality(_Feed):
    """``analytics.pit-quality`` — per-stop pit crew performance (race/sprint).

    ``data`` is a PitQualityAlert: stationary time, team session average, delta,
    and quality grade (EXCEPTIONAL/NORMAL/SLOW/CRITICAL).
    """

    feed: str = "analytics.pit-quality"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    data: Optional[Any] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class WeatherRainEvent(_Feed):
    """``weather.rain_onset`` / ``weather.rain_cleared`` — rain state-machine events.

    ``data`` is a WeatherEvent: precip rate, rain start lap + duration (on clear),
    track/air temp, humidity.
    """

    feed: str = "weather.rain_onset"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    event: Optional[str] = None
    lap: Optional[int] = None
    utc: Optional[str] = None
    data: Optional[Any] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class WeatherForecastUpdate(_Feed):
    """``weather.forecast_update`` — predictive rain forecast (race/sprint).

    Top-level forecast fields plus ``next60min``: up to 4 × 15-min slots ahead.
    """

    feed: str = "weather.forecast_update"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    event: Optional[str] = None
    lap: Optional[int] = None
    utc: Optional[str] = None
    source: Optional[str] = None
    forecast_model: Optional[str] = Field(default=None, alias="model")
    current_precip_rate_mmhr: Optional[float] = Field(default=None, alias="currentPrecipRateMmhr")
    precip_probability_pct: Optional[float] = Field(default=None, alias="precipProbabilityPct")
    next_60min: Optional[List[Any]] = Field(default=None, alias="next60min")

    # `model` is in pydantic's protected namespace; disable it for this wire field.
    model_config = ConfigDict(extra="allow", populate_by_name=True, protected_namespaces=())


class WeatherTyreMismatch(_Feed):
    """``weather.tyre_mismatch`` — per-driver wet-tyre alert (race/sprint).

    Fires when a slick-shod driver has rain falling or imminent. ``severity`` is
    urgent/advisory; ``trigger`` is raining_now/forecast_imminent/forecast_watch.
    """

    feed: str = "weather.tyre_mismatch"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    event: Optional[str] = None
    lap: Optional[int] = None
    utc: Optional[str] = None
    driver: Optional[Any] = None
    current_compound: Optional[str] = Field(default=None, alias="currentCompound")
    severity: Optional[str] = None
    trigger: Optional[str] = None
    expected_wet_onset_lap: Optional[int] = Field(default=None, alias="expectedWetOnsetLap")
    rain_probability_next5_laps: Optional[float] = Field(default=None, alias="rainProbabilityNext5Laps")
    intermediate_window_open: Optional[bool] = Field(default=None, alias="intermediateWindowOpen")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class WeatherStrategyDivergence(_Feed):
    """``weather.strategy_divergence`` — wet vs dry compound split (race/sprint).

    ``data`` carries ``on_wet_compounds`` / ``on_dry_compounds`` group stats and
    ``favored_group`` (wet_compounds/dry_compounds/neutral).
    """

    feed: str = "weather.strategy_divergence"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    event: Optional[str] = None
    lap: Optional[int] = None
    utc: Optional[str] = None
    data: Optional[Any] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class WeatherCompoundCrossoverAlert(_Feed):
    """``weather.compound_crossover_alert`` — inter→slick crossover after rain.

    Fires once per wet phase when slick drivers are measurably faster than inters.
    Wire keys are snake_case (``rain_cleared_lap``, ``estimated_laps_until_all_on_slick``).
    """

    feed: str = "weather.compound_crossover_alert"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    event: Optional[str] = None
    lap: Optional[int] = None
    utc: Optional[str] = None
    direction: Optional[str] = None
    confidence: Optional[float] = None
    evidence: Optional[Any] = None
    rain_cleared_lap: Optional[int] = None
    estimated_laps_until_all_on_slick: Optional[int] = None

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
    "AnalyticsSectorPace",
    "AnalyticsBattle",
    "AnalyticsPitWindow",
    "AnalyticsTrackConditions",
    "AnalyticsPitQuality",
    "WeatherRainEvent",
    "WeatherForecastUpdate",
    "WeatherTyreMismatch",
    "WeatherStrategyDivergence",
    "WeatherCompoundCrossoverAlert",
]
