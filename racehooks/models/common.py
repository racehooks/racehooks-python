"""Shared building-block models used across feed payloads and REST resources.

These mirror the canonical RaceHooks contract (the published Node SDK
``types.ts``). Wire format is camelCase; every model exposes snake_case
attributes via pydantic aliases and tolerates unknown fields
(``extra="allow"``) so new fields never break parsing.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DriverRef(BaseModel):
    """Stable driver identity block nested in every normalized payload driver entry.

    Mirrors ``DriverRef`` in the canonical contract: ``driverId``,
    ``constructorId``, ``number``, ``tla``, ``name``, ``team``. Fields are
    optional for resilient parsing, and extra per-feed driver fields (e.g.
    ``ltoe``, ``truePaceSec``) are preserved via ``extra="allow"``.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    driver_id: Optional[str] = Field(default=None, alias="driverId")
    constructor_id: Optional[str] = Field(default=None, alias="constructorId")
    number: Optional[str] = None
    tla: Optional[str] = None
    name: Optional[str] = None
    team: Optional[str] = None


class ReplayMeta(BaseModel):
    """``_replay`` metadata present only on Simulate (historical replay) deliveries.

    Mirrors ``ReplayMeta``: ``simulationId``, ``originalSessionId``, and an
    optional ``sessionElapsed`` ("HH:MM:SS.mmm" since session start).
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    simulation_id: Optional[str] = Field(default=None, alias="simulationId")
    original_session_id: Optional[str] = Field(default=None, alias="originalSessionId")
    session_elapsed: Optional[str] = Field(default=None, alias="sessionElapsed")


__all__ = ["DriverRef", "ReplayMeta"]
