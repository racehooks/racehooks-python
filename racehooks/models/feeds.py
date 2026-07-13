"""Pydantic models for RaceHooks feed webhook payloads.

Each model corresponds to a RaceHooks webhook delivery for a specific
canonical feed. The ``feed`` discriminator equals the canonical, hyphenated
``feedId`` (e.g. ``"events.race"``, ``"analytics.team-points"``,
``"weather.tire-mismatch"``) — never a dotless or underscored legacy id.

Wire format is camelCase; every model exposes snake_case attributes via
pydantic aliases. All models permit extra fields (``extra="allow"``) so that
new fields never break parsing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from racehooks.models.common import DriverRef, ReplayMeta


class _Feed(BaseModel):
    """Base for all feed data models — tolerant of unknown fields."""

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# Raw upstream feed shapes (SignalR-style PascalCase payloads).
# These validate the ``data`` body of the corresponding canonical feed.
# ---------------------------------------------------------------------------


class WeatherData(_Feed):
    """``weather.data`` — circuit weather, updated ~every 30s."""

    air_temp: Optional[str] = Field(default=None, alias="AirTemp")
    humidity: Optional[str] = Field(default=None, alias="Humidity")
    pressure: Optional[str] = Field(default=None, alias="Pressure")
    rainfall: Optional[str] = Field(default=None, alias="Rainfall")
    track_temp: Optional[str] = Field(default=None, alias="TrackTemp")
    wind_direction: Optional[str] = Field(default=None, alias="WindDirection")
    wind_speed: Optional[str] = Field(default=None, alias="WindSpeed")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class TrackStatus(_Feed):
    """``session.track-status`` — 1=Clear 2=Yellow 4=SC 6=VSC 7=VSC Ending."""

    status: Optional[str] = Field(default=None, alias="Status")
    message: Optional[str] = Field(default=None, alias="Message")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class SessionStatus(_Feed):
    """``session.status`` — Started, Aborted, Finished, Finalised, Ends."""

    status: Optional[str] = Field(default=None, alias="Status")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class LapCount(_Feed):
    """``session.lap-count`` — current and total laps."""

    current_lap: Optional[int] = Field(default=None, alias="CurrentLap")
    total_laps: Optional[int] = Field(default=None, alias="TotalLaps")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class DriverEntry(_Feed):
    """A single driver in the ``driver.list`` feed."""

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
    """``timing.data`` — lap/sector times, gaps, speed traps (per driver)."""

    lines: Optional[Dict[str, Any]] = Field(default=None, alias="Lines")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class DriverList(_Feed):
    """``driver.list`` — keyed by racing number → :class:`DriverEntry`."""

    model_config = ConfigDict(extra="allow")


class CurrentTyres(_Feed):
    """``tire.current`` — current compound per driver."""

    model_config = ConfigDict(extra="allow")


class RaceControlMessages(_Feed):
    """``race-control.messages`` — safety car, flags, penalties."""

    messages: Optional[Any] = Field(default=None, alias="Messages")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ---------------------------------------------------------------------------
# Derived analytics feeds — per-lap ML snapshots.
#
# The canonical envelopes are NOT uniform across analytics feeds — each model
# mirrors its node ``types.ts`` payload exactly:
#
# * ``_AnalyticsFeed`` (the ``AnalyticsEnvelope``): sessionId + raceId + lap +
#   utc + _replay — used by strategy, race-odds, true-pace, gap-projection,
#   winning-margin, race-duration, tire-strategy, team-points.
# * ``_SessionLapFeed``: sessionId + lap + utc + _replay (NO raceId) — used by
#   sector-pace, battle, pit-window, track-conditions, pit-quality.
# * qualifying, championship-probability and race-preview each carry a bespoke
#   envelope (see their classes).
# ---------------------------------------------------------------------------


class _AnalyticsFeed(_Feed):
    """The ``AnalyticsEnvelope``: sessionId + raceId + lap + utc + _replay."""

    session_id: Optional[str] = Field(default=None, alias="sessionId")
    race_id: Optional[str] = Field(default=None, alias="raceId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    replay: Optional[ReplayMeta] = Field(default=None, alias="_replay")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class _SessionLapFeed(_Feed):
    """Envelope for the per-driver alert feeds: sessionId + lap + utc + _replay.

    These feeds are keyed on the live session only — node's payloads carry NO
    separate ``raceId``.
    """

    session_id: Optional[str] = Field(default=None, alias="sessionId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    replay: Optional[ReplayMeta] = Field(default=None, alias="_replay")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsStrategy(_AnalyticsFeed):
    """``analytics.strategy`` — per-lap strategy signals (race/sprint only).

    Delivered once per lap for every driver. Fires independently of timing.data.
    """

    feed: str = "analytics.strategy"
    regulations_era: Optional[str] = Field(default=None, alias="regulationsEra")
    safety_car_probability: Optional[float] = Field(default=None, alias="safetyCarProbability")
    drivers: Optional[List[DriverRef]] = None


class AnalyticsRaceOdds(_AnalyticsFeed):
    """``analytics.race-odds`` — per-lap CTMC outcome probabilities (race/sprint only).

    Includes per-driver positionDistribution, podium/points odds, H2H vs teammate,
    and a top-level ``pairs`` array with same-constructor H2H probabilities.
    """

    feed: str = "analytics.race-odds"
    drivers: Optional[List[DriverRef]] = None
    pairs: Optional[List[Any]] = None


class AnalyticsTruePace(_AnalyticsFeed):
    """``analytics.true-pace`` — fuel/tyre/traffic-stripped pace ranking (race/sprint).

    Each driver carries ``truePaceSec``, ``truePaceRelSec`` and a ``rank``
    (1 = fastest), preserved via :class:`DriverRef`'s extra fields.
    """

    feed: str = "analytics.true-pace"
    drivers: Optional[List[DriverRef]] = None


class AnalyticsGapProjection(_AnalyticsFeed):
    """``analytics.gap-projection`` — Monte Carlo projected gap to race leader.

    Five percentile bands (p10–p90) plus P(lapped) per driver. Race/sprint only.
    """

    feed: str = "analytics.gap-projection"
    drivers: Optional[List[DriverRef]] = None


class WinningMarginLeadBattle(_Feed):
    """The ``leadBattle`` block on :class:`AnalyticsWinningMargin`."""

    leader: Optional[DriverRef] = None
    runner_up: Optional[DriverRef] = Field(default=None, alias="runnerUp")
    current_margin_sec: Optional[float] = Field(default=None, alias="currentMarginSec")
    expected_final_margin_sec: Optional[float] = Field(default=None, alias="expectedFinalMarginSec")
    p10_margin_sec: Optional[float] = Field(default=None, alias="p10MarginSec")
    p50_margin_sec: Optional[float] = Field(default=None, alias="p50MarginSec")
    p90_margin_sec: Optional[float] = Field(default=None, alias="p90MarginSec")
    probability_margin_above5: Optional[float] = Field(default=None, alias="probabilityMarginAbove5")
    probability_margin_above10: Optional[float] = Field(default=None, alias="probabilityMarginAbove10")
    probability_margin_below3: Optional[float] = Field(default=None, alias="probabilityMarginBelow3")
    sc_collapse_risk: Optional[float] = Field(default=None, alias="scCollapseRisk")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsWinningMargin(_AnalyticsFeed):
    """``analytics.winning-margin`` — projected P1–P2 winning margin (race/sprint)."""

    feed: str = "analytics.winning-margin"
    lead_battle: Optional[WinningMarginLeadBattle] = Field(default=None, alias="leadBattle")


class AnalyticsRaceDuration(_AnalyticsFeed):
    """``analytics.race-duration`` — projected race duration + red-flag/overtime risk."""

    feed: str = "analytics.race-duration"
    expected_race_time_minutes: Optional[float] = Field(default=None, alias="expectedRaceTimeMinutes")
    p10_race_time_minutes: Optional[float] = Field(default=None, alias="p10RaceTimeMinutes")
    p90_race_time_minutes: Optional[float] = Field(default=None, alias="p90RaceTimeMinutes")
    expected_winner_lap_time_sec: Optional[float] = Field(default=None, alias="expectedWinnerLapTimeSec")
    probability_red_flag: Optional[float] = Field(default=None, alias="probabilityRedFlag")
    probability_overtime_session: Optional[float] = Field(default=None, alias="probabilityOvertimeSession")
    sc_deployed_count: Optional[int] = Field(default=None, alias="scDeployedCount")


class AnalyticsRacePreview(_Feed):
    """``analytics.race-preview`` — two-stage pre-race preview (practice / grid).

    This feed predates the ``AnalyticsEnvelope``: it is keyed on ``eventId`` +
    ``circuitId`` rather than ``sessionId``/``lap``. ``stage`` is ``"practice"``
    or ``"grid"``; the stage-specific fields (``strategy`` for practice,
    ``scheduledRaceLaps`` + ``qualifying`` for grid) are optional accordingly.
    """

    feed: str = "analytics.race-preview"
    stage: Optional[str] = None
    event_id: Optional[str] = Field(default=None, alias="eventId")
    race_id: Optional[str] = Field(default=None, alias="raceId")
    circuit_id: Optional[str] = Field(default=None, alias="circuitId")
    utc: Optional[str] = None
    replay: Optional[ReplayMeta] = Field(default=None, alias="_replay")
    drivers: Optional[List[DriverRef]] = None
    # practice stage
    strategy: Optional[Any] = None
    # grid stage
    scheduled_race_laps: Optional[int] = Field(default=None, alias="scheduledRaceLaps")
    qualifying: Optional[Any] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsTireStrategy(_AnalyticsFeed):
    """``analytics.tire-strategy`` — next-compound probabilities.

    Sparse — fires only for drivers whose pitStopProbability exceeds the
    approach threshold (~0.25). Includes compound probability distribution.
    """

    feed: str = "analytics.tire-strategy"
    drivers: Optional[List[DriverRef]] = None


class AnalyticsTeamPoints(_AnalyticsFeed):
    """``analytics.team-points`` — constructor points outlook (race/sprint only).

    Expected combined points per constructor, computed from a discrete
    convolution of the joint position distribution across both drivers.
    """

    feed: str = "analytics.team-points"
    constructors: Optional[List[Any]] = None


class AnalyticsChampionshipProbability(_Feed):
    """``analytics.championship-probability`` — post-race WDC/WCC outlook (season).

    Delivered once after each official race. ``afterRaceId`` identifies the most
    recent race the probabilities are computed through; ``seasonYear`` is the
    full season the projection covers. Carries both driver and constructor rows.
    """

    feed: str = "analytics.championship-probability"
    season_year: Optional[int] = Field(default=None, alias="seasonYear")
    after_race_id: Optional[str] = Field(default=None, alias="afterRaceId")
    simulations_run: Optional[int] = Field(default=None, alias="simulationsRun")
    utc: Optional[str] = None
    replay: Optional[ReplayMeta] = Field(default=None, alias="_replay")
    drivers: Optional[List[DriverRef]] = None
    constructors: Optional[List[Any]] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsQualifying(_Feed):
    """``analytics.qualifying`` — per-segment qualifying model (Q1/Q2/Q3).

    Keyed on ``sessionId`` + ``raceId`` + ``segment`` + ``circuitId`` — node's
    payload carries NO ``lap``. Includes per-sector fastest probabilities, pole
    margin odds, and per-driver sector deltas + elimination probabilities.
    ``segment`` is "Q1"/"Q2"/"Q3".
    """

    feed: str = "analytics.qualifying"
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    race_id: Optional[str] = Field(default=None, alias="raceId")
    utc: Optional[str] = None
    replay: Optional[ReplayMeta] = Field(default=None, alias="_replay")
    segment: Optional[str] = None
    circuit_id: Optional[str] = Field(default=None, alias="circuitId")
    sectors: Optional[Any] = None
    pole_margin_above100ms: Optional[float] = Field(default=None, alias="poleMarginAbove100ms")
    pole_margin_above300ms: Optional[float] = Field(default=None, alias="poleMarginAbove300ms")
    pole_leader: Optional[DriverRef] = Field(default=None, alias="poleLeader")
    drivers: Optional[List[DriverRef]] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class AnalyticsSectorPace(_SessionLapFeed):
    """``analytics.sector-pace`` — per-driver sector anomaly detection (race/sprint).

    ``data`` is a per-driver reading: per-sector deltas vs the clean-lap baseline,
    anomaly flags, classified cause (RAIN/TIRE_CLIFF/INCIDENT), cross-driver
    correlation.
    """

    feed: str = "analytics.sector-pace"
    data: Optional[Any] = None


class AnalyticsBattle(_SessionLapFeed):
    """``analytics.battle`` — head-to-head battle tracking (race/sprint).

    ``data`` is a BattleState: attacker/defender, gap, catch rate, laps to striking
    distance, battleStatus, and a pass-probability forecast.
    """

    feed: str = "analytics.battle"
    data: Optional[Any] = None


class AnalyticsPitWindow(_SessionLapFeed):
    """``analytics.pit-window`` — per-driver optimal pit window (race/sprint).

    ``data`` is a PitWindowAlert: status (OPEN/URGENT/CLOSING/CLOSED), pit
    probability, undercut viability, cliff risk, VSC/SC override reason, pit count.
    """

    feed: str = "analytics.pit-window"
    data: Optional[Any] = None


class AnalyticsTrackConditions(_SessionLapFeed):
    """``analytics.track-conditions`` — per-sector wet/dry state (race/sprint).

    ``data`` is a SectorConditions: per-sector DRY/WET/DRYING, full-circuit-wet
    flag, intermediate-window-open, and crossover recommendation.
    """

    feed: str = "analytics.track-conditions"
    data: Optional[Any] = None


class AnalyticsPitQuality(_SessionLapFeed):
    """``analytics.pit-quality`` — per-stop pit crew performance (race/sprint).

    ``data`` is a PitQualityAlert: stationary time, team session average, delta,
    and quality grade (EXCEPTIONAL/NORMAL/SLOW/CRITICAL).
    """

    feed: str = "analytics.pit-quality"
    data: Optional[Any] = None


# ---------------------------------------------------------------------------
# Derived weather alert cluster.
#
# The weather alerts share a ``WeatherAlertEnvelope`` (feed + sessionId + lap +
# utc + optional _replay) — note there is NO separate raceId on these feeds.
# ---------------------------------------------------------------------------


class _WeatherAlert(_Feed):
    """Shared ``WeatherAlertEnvelope`` fields for the derived weather feeds."""

    session_id: Optional[str] = Field(default=None, alias="sessionId")
    lap: Optional[int] = None
    utc: Optional[str] = None
    replay: Optional[ReplayMeta] = Field(default=None, alias="_replay")

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class WeatherRainEvent(_WeatherAlert):
    """``weather.rain-onset`` / ``weather.rain-cleared`` — rain state-machine events.

    ``data`` is a rain reading: precip rate, rain start lap + duration (on
    cleared), track/air temp, humidity.
    """

    feed: str = "weather.rain-onset"
    data: Optional[Any] = None


class WeatherForecastUpdate(_WeatherAlert):
    """``weather.forecast-update`` — predictive rain forecast (session-level).

    Top-level forecast fields plus ``next60min``: up to 4 × 15-min slots ahead.
    ``source`` is "forecast" (numerical model) or "radar" (ground-radar nowcast).
    """

    feed: str = "weather.forecast-update"
    source: Optional[str] = None
    current_precip_rate_mmhr: Optional[float] = Field(default=None, alias="currentPrecipRateMmhr")
    precip_probability_pct: Optional[float] = Field(default=None, alias="precipProbabilityPct")
    rain_expected_in_min: Optional[float] = Field(default=None, alias="rainExpectedInMin")
    next_60min: Optional[List[Any]] = Field(default=None, alias="next60min")


class WeatherTireMismatch(_WeatherAlert):
    """``weather.tire-mismatch`` — per-driver wet-tyre alert (race/sprint).

    Fires when a slick-shod driver has rain falling or imminent. ``severity`` is
    urgent/advisory; ``trigger`` is raining_now/forecast_imminent/forecast_watch.
    """

    feed: str = "weather.tire-mismatch"
    driver: Optional[DriverRef] = None
    current_compound: Optional[str] = Field(default=None, alias="currentCompound")
    severity: Optional[str] = None
    trigger: Optional[str] = None
    expected_wet_onset_lap: Optional[int] = Field(default=None, alias="expectedWetOnsetLap")
    rain_probability_next5_laps: Optional[float] = Field(default=None, alias="rainProbabilityNext5Laps")
    intermediate_window_open: Optional[bool] = Field(default=None, alias="intermediateWindowOpen")


class WeatherStrategyDivergence(_WeatherAlert):
    """``weather.strategy-divergence`` — wet vs dry compound split (race/sprint).

    ``data`` carries ``onWetCompounds`` / ``onDryCompounds`` group stats and
    ``favoredGroup`` (wet/dry/neutral).
    """

    feed: str = "weather.strategy-divergence"
    data: Optional[Any] = None


class WeatherCompoundCrossover(_WeatherAlert):
    """``weather.compound-crossover`` — inter→slick crossover after rain clears.

    Fires once per wet phase when slick drivers are measurably faster than inters.
    ``evidence`` groups drivers on slick vs inter with their LTOE.
    """

    feed: str = "weather.compound-crossover"
    direction: Optional[str] = None
    confidence: Optional[float] = None
    evidence: Optional[Any] = None
    rain_cleared_lap: Optional[int] = Field(default=None, alias="rainClearedLap")
    estimated_laps_until_all_on_slick: Optional[int] = Field(
        default=None, alias="estimatedLapsUntilAllOnSlick"
    )


__all__ = [
    "DriverRef",
    "ReplayMeta",
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
    "AnalyticsTruePace",
    "AnalyticsGapProjection",
    "AnalyticsWinningMargin",
    "WinningMarginLeadBattle",
    "AnalyticsRaceDuration",
    "AnalyticsRacePreview",
    "AnalyticsTireStrategy",
    "AnalyticsTeamPoints",
    "AnalyticsChampionshipProbability",
    "AnalyticsQualifying",
    "AnalyticsSectorPace",
    "AnalyticsBattle",
    "AnalyticsPitWindow",
    "AnalyticsTrackConditions",
    "AnalyticsPitQuality",
    "WeatherRainEvent",
    "WeatherForecastUpdate",
    "WeatherTireMismatch",
    "WeatherStrategyDivergence",
    "WeatherCompoundCrossover",
]
