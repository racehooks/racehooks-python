"""Pydantic v2 models for RaceHooks webhook event envelopes.

Every webhook RaceHooks delivers is a JSON object with a common envelope. The
``feed`` field is the canonical, hyphenated feed id; the shape of the body
depends on it.

Envelope shapes mirror the canonical contract (the published Node SDK):

* Generic feeds: ``{ feed, sessionId, data }``
* ``events.race`` / ``events.qualifying``:
  ``{ feed, sessionId, event, lap, utc, data }`` — a discriminated union keyed
  on ``event`` (e.g. ``"overtake"``, ``"safety.car.deployed"``).
* ``session.timing``: ``{ feed, sessionId, utc, ...trackerFields }``
* ``results.race-summary``: predates the ``feed`` envelope; carries a ``type``
  discriminator (``"race.summary.complete"``).
* Derived analytics + weather feeds: see :mod:`racehooks.models.feeds`.

:func:`parse_event` deserializes a raw payload into the most specific model,
falling back to :class:`WebhookEvent` for feeds without a dedicated class.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from racehooks.models.common import DriverRef, ReplayMeta
from racehooks.models.feeds import (
    AnalyticsBattle,
    AnalyticsChampionshipProbability,
    AnalyticsGapProjection,
    AnalyticsPitQuality,
    AnalyticsPitWindow,
    AnalyticsQualifying,
    AnalyticsRaceDuration,
    AnalyticsRaceOdds,
    AnalyticsRacePreview,
    AnalyticsSectorPace,
    AnalyticsStrategy,
    AnalyticsTeamPoints,
    AnalyticsTireStrategy,
    AnalyticsTrackConditions,
    AnalyticsTruePace,
    AnalyticsWinningMargin,
    WeatherCompoundCrossover,
    WeatherForecastUpdate,
    WeatherRainEvent,
    WeatherStrategyDivergence,
    WeatherTireMismatch,
)


class WebhookEvent(BaseModel):
    """Base envelope shared by every RaceHooks webhook delivery.

    Generic feeds (``weather.data``, ``session.track-status``, …) use exactly
    this shape: ``{ feed, sessionId, data }``. ``data`` is kept as a raw value
    so callers can index into it for feeds without a typed model. Per-driver
    normalized feeds may use ``drivers`` instead of ``data``.
    """

    feed: str
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    data: Any = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RaceEvent(WebhookEvent):
    """``events.race`` — synthetic race events emitted on state transitions.

    A discriminated union keyed on ``event`` (a dot-separated name such as
    ``"safety.car.deployed"``, ``"overtake"``, ``"lead.change"``). The envelope
    carries extra top-level fields: ``event``, ``lap``, ``utc`` and an optional
    ``_replay`` block; every nested driver is a full :class:`DriverRef`.
    """

    feed: str = "events.race"
    event: str
    lap: int = 0
    utc: Optional[str] = None
    replay: Optional[ReplayMeta] = Field(default=None, alias="_replay")


class QualifyingEvent(WebhookEvent):
    """``events.qualifying`` — qualifying-specific synthetic events.

    Same envelope as :class:`RaceEvent`, keyed on ``event`` (e.g.
    ``"qualifying.pole_position"``, ``"qualifying.driver_eliminated"``,
    ``"qualifying.session_complete"``).
    """

    feed: str = "events.qualifying"
    event: str
    lap: int = 0
    utc: Optional[str] = None
    replay: Optional[ReplayMeta] = Field(default=None, alias="_replay")


class SessionTimingEvent(WebhookEvent):
    """``session.timing`` — normalized session-timing snapshot.

    Tracker fields are spread onto the top level alongside ``utc``. Known
    fields are typed; anything else remains accessible via attribute access
    thanks to ``extra="allow"``.
    """

    feed: str = "session.timing"
    utc: Optional[str] = None
    lap: Optional[int] = None
    total_laps: Optional[int] = Field(default=None, alias="totalLaps")
    track_status: Optional[str] = Field(default=None, alias="trackStatus")


class RaceSummaryEvent(WebhookEvent):
    """``results.race-summary`` — post-race telemetry summary (once, after CarData).

    This delivery predates the standard ``feed`` envelope and instead carries a
    ``type`` discriminator (``"race.summary.complete"``). Top-level fields mirror
    the canonical ``RaceSummaryPayload``.
    """

    feed: str = "results.race-summary"
    type: Optional[str] = None
    race_id: Optional[str] = Field(default=None, alias="raceId")
    race_name: Optional[str] = Field(default=None, alias="raceName")
    processed_at: Optional[str] = Field(default=None, alias="processedAt")
    total_samples: Optional[int] = Field(default=None, alias="totalSamples")
    max_speed_kph: Optional[float] = Field(default=None, alias="maxSpeedKph")
    max_speed_driver: Optional[DriverRef] = Field(default=None, alias="maxSpeedDriver")
    avg_throttle_pct: Optional[float] = Field(default=None, alias="avgThrottlePct")
    avg_brake_pct: Optional[float] = Field(default=None, alias="avgBrakePct")
    top_aggression_driver: Optional[DriverRef] = Field(default=None, alias="topAggressionDriver")
    top_aggression_score: Optional[float] = Field(default=None, alias="topAggressionScore")


# Canonical feed ids that get a dedicated envelope model. Everything else is
# parsed as the generic :class:`WebhookEvent`.
_EVENT_MODELS: Dict[str, Any] = {
    "events.race": RaceEvent,
    "events.qualifying": QualifyingEvent,
    "session.timing": SessionTimingEvent,
    "results.race-summary": RaceSummaryEvent,
    "analytics.strategy": AnalyticsStrategy,
    "analytics.race-odds": AnalyticsRaceOdds,
    "analytics.true-pace": AnalyticsTruePace,
    "analytics.gap-projection": AnalyticsGapProjection,
    "analytics.winning-margin": AnalyticsWinningMargin,
    "analytics.race-duration": AnalyticsRaceDuration,
    "analytics.race-preview": AnalyticsRacePreview,
    "analytics.tire-strategy": AnalyticsTireStrategy,
    "analytics.team-points": AnalyticsTeamPoints,
    "analytics.championship-probability": AnalyticsChampionshipProbability,
    "analytics.qualifying": AnalyticsQualifying,
    "analytics.sector-pace": AnalyticsSectorPace,
    "analytics.battle": AnalyticsBattle,
    "analytics.pit-window": AnalyticsPitWindow,
    "analytics.track-conditions": AnalyticsTrackConditions,
    "analytics.pit-quality": AnalyticsPitQuality,
    "weather.rain-onset": WeatherRainEvent,
    "weather.rain-cleared": WeatherRainEvent,
    "weather.forecast-update": WeatherForecastUpdate,
    "weather.tire-mismatch": WeatherTireMismatch,
    "weather.strategy-divergence": WeatherStrategyDivergence,
    "weather.compound-crossover": WeatherCompoundCrossover,
}

AnyEvent = Union[
    RaceEvent,
    QualifyingEvent,
    SessionTimingEvent,
    RaceSummaryEvent,
    AnalyticsStrategy,
    AnalyticsRaceOdds,
    AnalyticsTruePace,
    AnalyticsGapProjection,
    AnalyticsWinningMargin,
    AnalyticsRaceDuration,
    AnalyticsRacePreview,
    AnalyticsTireStrategy,
    AnalyticsTeamPoints,
    AnalyticsChampionshipProbability,
    AnalyticsQualifying,
    AnalyticsSectorPace,
    AnalyticsBattle,
    AnalyticsPitWindow,
    AnalyticsTrackConditions,
    AnalyticsPitQuality,
    WeatherRainEvent,
    WeatherForecastUpdate,
    WeatherTireMismatch,
    WeatherStrategyDivergence,
    WeatherCompoundCrossover,
    WebhookEvent,
]


def parse_event(payload: Union[str, bytes, bytearray, Dict[str, Any]]) -> AnyEvent:
    """Parse a raw webhook payload into the most specific event model.

    Dispatch is on the canonical ``feed`` discriminator. The
    ``results.race-summary`` delivery predates the ``feed`` envelope and instead
    carries ``type == "race.summary.complete"``; that shape is recognised too.

    :param payload: Raw JSON ``str``/``bytes`` or an already-decoded ``dict``.
    :returns: The most specific :class:`AnyEvent` member, or generic
        :class:`WebhookEvent`.
    """
    if isinstance(payload, (str, bytes, bytearray)):
        data = json.loads(payload)
    else:
        data = payload

    if not isinstance(data, dict):
        raise ValueError("Webhook payload must be a JSON object")

    feed = data.get("feed")
    if not feed and data.get("type") == "race.summary.complete":
        return RaceSummaryEvent.model_validate(data)

    model = _EVENT_MODELS.get(feed or "", WebhookEvent)
    return model.model_validate(data)


__all__ = [
    "WebhookEvent",
    "RaceEvent",
    "QualifyingEvent",
    "SessionTimingEvent",
    "RaceSummaryEvent",
    "AnyEvent",
    "parse_event",
    "DriverRef",
    "ReplayMeta",
    "AnalyticsStrategy",
    "AnalyticsRaceOdds",
    "AnalyticsTruePace",
    "AnalyticsGapProjection",
    "AnalyticsWinningMargin",
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
