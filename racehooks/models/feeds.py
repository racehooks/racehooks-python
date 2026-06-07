"""Pydantic models for RaceHooks F1 live-timing feed payloads.

These mirror the raw F1 SignalR feed shapes delivered inside the
``data`` field of a webhook envelope. All numeric values arrive as
strings in the raw F1 feed, matching ``@racehooks/f1-telemetry-schema``.

Every model permits extra fields (``extra="allow"``) so that new feed
fields added upstream never break parsing.
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
]
