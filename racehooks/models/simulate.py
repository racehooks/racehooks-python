"""Pydantic models for the session-replay REST endpoints (``/v1/simulate/*``).

Wire format is camelCase and every model exposes snake_case attributes via
pydantic aliases, tolerating unknown fields (``extra="allow"``) so new fields
never break parsing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Resource(BaseModel):
    """Base for replay resource models — tolerant of unknown fields."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ReplayableSession(_Resource):
    """A completed session that can be replayed (``GET /v1/simulate/sessions``)."""

    session_id: str = Field(alias="sessionId")
    session_name: Optional[str] = Field(default=None, alias="sessionName")
    event_id: Optional[str] = Field(default=None, alias="eventId")
    event_name: Optional[str] = Field(default=None, alias="eventName")
    circuit_id: Optional[str] = Field(default=None, alias="circuitId")
    circuit_outline: Optional[Dict[str, Any]] = Field(
        default=None, alias="circuitOutline"
    )
    year: Optional[int] = None
    type: Optional[str] = None
    start_date: Optional[str] = Field(default=None, alias="startDate")
    #: Replaying this session delivers the full Analytics feeds on any plan
    #: without using a replay slot.
    analytics_preview: Optional[bool] = Field(default=None, alias="analyticsPreview")


class ReplayableSessionList(_Resource):
    """Paginated replayable-session listing."""

    sessions: List[ReplayableSession] = Field(default_factory=list)
    total: int = 0
    limit: Optional[int] = None
    offset: Optional[int] = None
    #: The season the listing is clamped to when the tier limits the archive.
    restricted_to_season: Optional[str] = Field(
        default=None, alias="restrictedToSeason"
    )


class SimulateArtifact(_Resource):
    """Recorded-playback artifact state for a session.

    ``status`` is ``"ready"`` (stream it now), ``"preparing"`` (generation was
    triggered; poll ``status()``), ``"missing"`` (call ``prepare()``) or
    ``"unknown"`` (no such session). ``profile`` is ``"lite"`` or ``"full"``.
    """

    session_id: str = Field(alias="sessionId")
    session_name: Optional[str] = Field(default=None, alias="sessionName")
    model_version: Optional[str] = Field(default=None, alias="modelVersion")
    profile: Optional[str] = None
    status: str
    #: Served from a compatible prior format while the current one regenerates.
    format_fallback: Optional[bool] = Field(default=None, alias="formatFallback")


class DemoSession(_Resource):
    """The curated demo session (``GET /v1/simulate/demo``)."""

    session_id: str = Field(alias="sessionId")
    session_name: Optional[str] = Field(default=None, alias="sessionName")
    #: ``"ready"`` or ``"missing"``.
    status: str


class ReplayQuota(_Resource):
    """Distinct-session replay-delivery quota (``GET /v1/simulate/quota``).

    Watching is unlimited; ``-1`` means unlimited for ``limit``/``remaining``.
    """

    limit: int
    used: int
    remaining: int
    #: Session ids already unlocked; re-running them is free.
    unlocked: List[str] = Field(default_factory=list)
    current_season_only: bool = Field(default=False, alias="currentSeasonOnly")


__all__ = [
    "ReplayableSession",
    "ReplayableSessionList",
    "SimulateArtifact",
    "DemoSession",
    "ReplayQuota",
]
