"""Pydantic models for the Fantasy REST endpoints (``/v1/fantasy/*``).

Pit-stop leaderboards and estimated F1 Fantasy points per driver. These mirror
the canonical REST shapes; wire format is camelCase and every model exposes
snake_case attributes via pydantic aliases, tolerating unknown fields
(``extra="allow"``) so new fields never break parsing.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Resource(BaseModel):
    """Base for fantasy resource models — tolerant of unknown fields."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class PitTimeStop(_Resource):
    """A single stationary pit-stop time on a fantasy pit-times leaderboard.

    ``pit_stop_time_sec`` is the number of seconds the car is stationary in its
    box. ``lap`` may be ``None`` for live-only stops that carry no lap number.
    """

    driver: Optional[str] = None
    tla: Optional[str] = None
    team: Optional[str] = None
    name: Optional[str] = None
    pit_stop_time_sec: Optional[float] = Field(default=None, alias="pitStopTimeSec")
    lap: Optional[int] = None


class SessionPitTimes(_Resource):
    """Response from ``GET /v1/fantasy/session/:sessionId/pit-times``."""

    session_id: Optional[str] = Field(default=None, alias="sessionId")
    source: Optional[str] = None  # "live" | "historical"
    fastest_stop: Optional[PitTimeStop] = Field(default=None, alias="fastestStop")
    stops: List[PitTimeStop] = Field(default_factory=list)


class FantasyScoreBreakdown(_Resource):
    """Per-driver fantasy points breakdown.

    Nullable components (grid-derived, fastest-lap, teammate-quali) are ``None``
    while a session is live or when the component does not apply to the session.
    """

    race_pos_points: Optional[int] = Field(default=None, alias="racePosPoints")
    quali_pos_points: Optional[int] = Field(default=None, alias="qualiPosPoints")
    q3_bonus: Optional[int] = Field(default=None, alias="q3Bonus")
    positions_gained: Optional[int] = Field(default=None, alias="positionsGained")
    positions_gained_points: Optional[int] = Field(
        default=None, alias="positionsGainedPoints"
    )
    fastest_lap_points: Optional[int] = Field(default=None, alias="fastestLapPoints")
    beat_teammate_race: Optional[int] = Field(default=None, alias="beatTeammateRace")
    beat_teammate_quali: Optional[int] = Field(default=None, alias="beatTeammateQuali")
    dnf_penalty: Optional[int] = Field(default=None, alias="dnfPenalty")
    total: Optional[int] = None


class FantasyScoreEntry(_Resource):
    """One driver's fantasy score with its :class:`FantasyScoreBreakdown`."""

    driver: Optional[str] = None
    tla: Optional[str] = None
    team: Optional[str] = None
    breakdown: Optional[FantasyScoreBreakdown] = None


class RaceScores(_Resource):
    """Response from ``GET /v1/fantasy/races/:raceId/scores``.

    ``session_type`` echoes which session was scored (``"grand_prix"`` or
    ``"sprint"``). ``data_quality`` is present only when a caveat applies (e.g.
    missing qualifying data, or no results for the race id).
    """

    race_id: Optional[str] = Field(default=None, alias="raceId")
    session_type: Optional[str] = Field(default=None, alias="sessionType")
    scores: List[FantasyScoreEntry] = Field(default_factory=list)
    data_quality: Optional[str] = Field(default=None, alias="dataQuality")


class SessionScores(_Resource):
    """Response from ``GET /v1/fantasy/session/:sessionId/scores`` — the running
    (provisional) score while a session is live.

    ``live`` is ``False`` and ``scores`` is empty when no session is currently
    live for this id; use :class:`RaceScores` for a completed session.
    """

    session_id: Optional[str] = Field(default=None, alias="sessionId")
    live: Optional[bool] = None
    provisional: Optional[bool] = None
    session_type: Optional[str] = Field(default=None, alias="sessionType")
    current_lap: Optional[int] = Field(default=None, alias="currentLap")
    total_laps: Optional[int] = Field(default=None, alias="totalLaps")
    scores: List[FantasyScoreEntry] = Field(default_factory=list)


__all__ = [
    "PitTimeStop",
    "SessionPitTimes",
    "FantasyScoreBreakdown",
    "FantasyScoreEntry",
    "RaceScores",
    "SessionScores",
]
