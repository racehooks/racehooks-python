"""Pydantic v2 models for RaceHooks webhook event envelopes.

Every webhook RaceHooks delivers is a JSON object with a common envelope.
The ``feed`` field is the feed slug; the shape of ``data`` depends on it.

Envelope shapes mirror the server (see ``feedHandlers.ts``):

* Generic feeds: ``{ feed, sessionId, data }``
* ``raceevent``:  ``{ feed, sessionId, event, lap, utc, data }``
* ``sessiontiming``: ``{ feed, sessionId, utc, ...trackerFields }``
* Derived analytics feeds (18 total — 12 ``analytics.*`` + 6 ``weather.*``):
  strategy, race-odds, gap-projection, tire-strategy, constructor,
  championship-probability, qualifying, sector-pace, battle, pit-window,
  track-conditions, pit-quality; plus weather rain_onset/rain_cleared,
  forecast_update, tyre_mismatch, strategy_divergence, compound_crossover_alert.

:func:`parse_event` deserializes a raw payload into the most specific model,
falling back to :class:`WebhookEvent` for feeds without a dedicated class.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from racehooks.models.feeds import (
    AnalyticsStrategy,
    AnalyticsRaceOdds,
    AnalyticsGapProjection,
    AnalyticsTireStrategy,
    AnalyticsConstructor,
    AnalyticsChampionshipProbability,
    AnalyticsQualifying,
    AnalyticsSectorPace,
    AnalyticsBattle,
    AnalyticsPitWindow,
    AnalyticsTrackConditions,
    AnalyticsPitQuality,
    WeatherRainEvent,
    WeatherForecastUpdate,
    WeatherTyreMismatch,
    WeatherStrategyDivergence,
    WeatherCompoundCrossoverAlert,
)


class WebhookEvent(BaseModel):
    """Base envelope shared by every RaceHooks webhook delivery.

    Generic feeds (``timingdata``, ``cardata``, ``position`` …) use exactly
    this shape: ``{ feed, sessionId, data }``. ``data`` is kept as a raw
    value so callers can index into it for feeds without a typed model.
    Per-driver feeds (``timingdata``) may use ``drivers`` instead of ``data``.
    """

    feed: str
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    data: Any = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RaceEvent(WebhookEvent):
    """``raceevent`` — synthetic events emitted on state transitions.

    The envelope carries extra top-level fields: ``event`` (a dot-separated
    name such as ``"safety.car.deployed"``), ``lap``, and ``utc``.
    """

    feed: str = "raceevent"
    event: str
    lap: int = 0
    utc: Optional[str] = None


class SessionTimingEvent(WebhookEvent):
    """``sessiontiming`` — normalized session-timing snapshot.

    Tracker fields are spread onto the top level alongside ``utc``. Known
    fields are typed; anything else remains accessible via attribute access
    thanks to ``extra="allow"``.
    """

    feed: str = "sessiontiming"
    utc: Optional[str] = None
    lap: Optional[int] = None
    total_laps: Optional[int] = Field(default=None, alias="totalLaps")
    track_status: Optional[str] = Field(default=None, alias="trackStatus")


class RaceSummaryEvent(WebhookEvent):
    """``racesummary`` — post-race telemetry summary."""

    feed: str = "racesummary"


# Feed slugs that get a dedicated envelope model. Everything else is parsed
# as the generic :class:`WebhookEvent`.
_EVENT_MODELS: Dict[str, Any] = {
    "raceevent":                         RaceEvent,
    "sessiontiming":                     SessionTimingEvent,
    "racesummary":                       RaceSummaryEvent,
    "analytics.strategy":                AnalyticsStrategy,
    "analytics.race-odds":               AnalyticsRaceOdds,
    "analytics.gap-projection":          AnalyticsGapProjection,
    "analytics.tire-strategy":           AnalyticsTireStrategy,
    "analytics.constructor":             AnalyticsConstructor,
    "analytics.championship-probability": AnalyticsChampionshipProbability,
    "analytics.qualifying":              AnalyticsQualifying,
    "analytics.sector-pace":             AnalyticsSectorPace,
    "analytics.battle":                  AnalyticsBattle,
    "analytics.pit-window":              AnalyticsPitWindow,
    "analytics.track-conditions":        AnalyticsTrackConditions,
    "analytics.pit-quality":             AnalyticsPitQuality,
    "weather.rain_onset":                WeatherRainEvent,
    "weather.rain_cleared":              WeatherRainEvent,
    "weather.forecast_update":           WeatherForecastUpdate,
    "weather.tyre_mismatch":             WeatherTyreMismatch,
    "weather.strategy_divergence":       WeatherStrategyDivergence,
    "weather.compound_crossover_alert":  WeatherCompoundCrossoverAlert,
}

AnyEvent = Union[
    RaceEvent,
    SessionTimingEvent,
    RaceSummaryEvent,
    AnalyticsStrategy,
    AnalyticsRaceOdds,
    AnalyticsGapProjection,
    AnalyticsTireStrategy,
    AnalyticsConstructor,
    AnalyticsChampionshipProbability,
    AnalyticsQualifying,
    AnalyticsSectorPace,
    AnalyticsBattle,
    AnalyticsPitWindow,
    AnalyticsTrackConditions,
    AnalyticsPitQuality,
    WeatherRainEvent,
    WeatherForecastUpdate,
    WeatherTyreMismatch,
    WeatherStrategyDivergence,
    WeatherCompoundCrossoverAlert,
    WebhookEvent,
]


def parse_event(payload: Union[str, bytes, bytearray, Dict[str, Any]]) -> AnyEvent:
    """Parse a raw webhook payload into the most specific event model.

    :param payload: Raw JSON ``str``/``bytes`` or an already-decoded ``dict``.
    :returns: A :class:`RaceEvent`, :class:`SessionTimingEvent`,
        :class:`RaceSummaryEvent`, or generic :class:`WebhookEvent`.
    """
    if isinstance(payload, (str, bytes, bytearray)):
        data = json.loads(payload)
    else:
        data = payload

    if not isinstance(data, dict):
        raise ValueError("Webhook payload must be a JSON object")

    event_type = data.get("feed", "")
    model = _EVENT_MODELS.get(event_type, WebhookEvent)
    return model.model_validate(data)


__all__ = [
    "WebhookEvent",
    "RaceEvent",
    "SessionTimingEvent",
    "RaceSummaryEvent",
    "AnyEvent",
    "parse_event",
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
