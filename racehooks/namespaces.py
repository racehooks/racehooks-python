"""Namespaces for the read-only analytics, data and account endpoints.

These methods return the decoded ``data`` payload of each response as plain
JSON (``dict`` / ``list``). The shapes are large and evolve with the models and
datasets, so they are not frozen into Pydantic classes; see the OpenAPI spec at
https://api.racehooks.io/openapi.json for the exact fields. Plan gating (Free /
Developer / Custom) is enforced by the API: a call above your plan raises
``RaceHooksAPIError`` with status 402 or 403.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional, Tuple
import json

if TYPE_CHECKING:  # pragma: no cover
    from .client import RaceHooks


def _q(**params: Any) -> Dict[str, Any]:
    """Drop ``None`` values so unset options are not sent."""
    return {k: v for k, v in params.items() if v is not None}


def _data(res: Any) -> Any:
    """Return the ``data`` envelope when present, else the body unchanged."""
    if isinstance(res, dict) and "data" in res:
        return res["data"]
    return res


class _Namespace:
    def __init__(self, client: "RaceHooks") -> None:
        self._client = client

    def _get(self, path: str, **params: Any) -> Any:
        return _data(self._client._get(path, _q(**params)))


class DataNamespace(_Namespace):
    """Drivers, constructors, circuits, seasons, races and post-race telemetry
    analytics (``/v1/data/*``). Available on every plan; timing fields and some
    telemetry are gated by plan."""

    def list_drivers(
        self,
        *,
        series: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        nationality: Optional[str] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Any:
        return self._get(
            "/data/drivers",
            series=series,
            limit=limit,
            offset=offset,
            nationality=nationality,
            active=active,
            search=search,
        )

    def get_driver(self, driver_id: str) -> Any:
        return self._get(f"/data/drivers/{driver_id}")

    def get_driver_results(
        self,
        driver_id: str,
        *,
        series: Optional[str] = None,
        season: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Any:
        return self._get(
            f"/data/drivers/{driver_id}/results",
            series=series,
            season=season,
            limit=limit,
            offset=offset,
        )

    def get_driver_standings(
        self,
        driver_id: str,
        *,
        series: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Any:
        return self._get(
            f"/data/drivers/{driver_id}/standings",
            series=series,
            limit=limit,
            offset=offset,
        )

    def list_constructors(
        self,
        *,
        series: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        lineage: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Any:
        return self._get(
            "/data/constructors",
            series=series,
            limit=limit,
            offset=offset,
            lineage=lineage,
            active=active,
        )

    def get_constructor(self, constructor_id: str) -> Any:
        return self._get(f"/data/constructors/{constructor_id}")

    def get_constructor_results(
        self,
        constructor_id: str,
        *,
        series: Optional[str] = None,
        season: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Any:
        return self._get(
            f"/data/constructors/{constructor_id}/results",
            series=series,
            season=season,
            limit=limit,
            offset=offset,
        )

    def get_constructor_standings(
        self,
        constructor_id: str,
        *,
        series: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Any:
        return self._get(
            f"/data/constructors/{constructor_id}/standings",
            series=series,
            limit=limit,
            offset=offset,
        )

    def list_circuits(
        self,
        *,
        series: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        country: Optional[str] = None,
    ) -> Any:
        return self._get(
            "/data/circuits",
            series=series,
            limit=limit,
            offset=offset,
            country=country,
        )

    def get_circuit(self, circuit_id: str) -> Any:
        return self._get(f"/data/circuits/{circuit_id}")

    def list_seasons(self) -> Any:
        return self._get("/data/seasons")

    def get_season_standings(self, year: int) -> Any:
        return self._get(f"/data/seasons/{year}/standings")

    def get_season_races(self, year: int) -> Any:
        return self._get(f"/data/seasons/{year}/races")

    def get_championship_probability(self, year: int) -> Any:
        return self._get(f"/data/seasons/{year}/championship-probability")

    def get_race(self, race_id: str) -> Any:
        return self._get(f"/data/races/{race_id}")

    def get_race_qualifying(self, race_id: str) -> Any:
        return self._get(f"/data/races/{race_id}/qualifying")

    def get_race_pitstops(self, race_id: str) -> Any:
        return self._get(f"/data/races/{race_id}/pitstops")

    def get_race_tyres(self, race_id: str) -> Any:
        return self._get(f"/data/races/{race_id}/tyres")

    def get_race_weather(self, race_id: str) -> Any:
        return self._get(f"/data/races/{race_id}/weather")

    def get_race_summary(self, race_id: str) -> Any:
        return self._get(f"/data/races/{race_id}/summary")

    def get_race_laps(
        self,
        race_id: str,
        *,
        series: Optional[str] = None,
        driver_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Any:
        return self._get(
            f"/data/races/{race_id}/laps",
            series=series,
            driverId=driver_id,
            limit=limit,
            offset=offset,
        )

    def get_driver_race_laps(self, race_id: str, driver_id: str) -> Any:
        """Every lap of one driver in one race (``/v1/data/races/{raceId}/laps/{driverId}``)."""
        return self._get(f"/data/races/{race_id}/laps/{driver_id}")

    def get_race_telemetry_laps(
        self,
        race_id: str,
        *,
        series: Optional[str] = None,
        driver_id: Optional[str] = None,
        lap: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Any:
        return self._get(
            f"/data/races/{race_id}/telemetry/laps",
            series=series,
            driverId=driver_id,
            lap=lap,
            limit=limit,
            offset=offset,
        )

    def get_race_telemetry_stints(
        self,
        race_id: str,
        *,
        series: Optional[str] = None,
        driver_id: Optional[str] = None,
    ) -> Any:
        return self._get(
            f"/data/races/{race_id}/telemetry/stints",
            series=series,
            driverId=driver_id,
        )

    def get_race_telemetry_aggression(self, race_id: str) -> Any:
        return self._get(f"/data/races/{race_id}/telemetry/aggression")

    def get_session_analytics(
        self,
        session_id: str,
        *,
        series: Optional[str] = None,
        driver_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Any:
        return self._get(
            f"/data/sessions/{session_id}/analytics",
            series=series,
            driverId=driver_id,
            limit=limit,
            offset=offset,
        )

    def get_event_pace(
        self,
        event_id: str,
        *,
        series: Optional[str] = None,
        session: Optional[str] = None,
    ) -> Any:
        return self._get(
            f"/data/events/{event_id}/pace", series=series, session=session
        )


class HistoricalNamespace(_Namespace):
    """Historical results, standings and lap data from 1950 to present
    (``/v1/historical/*``)."""

    def _paged(
        self,
        path: str,
        series: Optional[str],
        limit: Optional[int],
        offset: Optional[int],
        **extra: Any,
    ) -> Any:
        return self._get(path, series=series, limit=limit, offset=offset, **extra)

    def seasons(self, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged("/historical/seasons", series, limit, offset)

    def races(self, season: int, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(f"/historical/{season}/races", series, limit, offset)

    def results(self, season: int, round: int, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(f"/historical/{season}/{round}/results", series, limit, offset)

    def qualifying(self, season: int, round: int, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(f"/historical/{season}/{round}/qualifying", series, limit, offset)

    def qualifying_laps(
        self,
        season: int,
        round: int,
        *,
        driver: Optional[str] = None,
        session: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Any:
        return self._get(
            f"/historical/{season}/{round}/qualifying/laps",
            driver=driver,
            session=session,
            limit=limit,
            offset=offset,
        )

    def laps(self, season: int, round: int, *, driver: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._get(
            f"/historical/{season}/{round}/laps",
            driver=driver,
            limit=limit,
            offset=offset,
        )

    def pitstops(self, season: int, round: int, *, driver: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._get(
            f"/historical/{season}/{round}/pitstops",
            driver=driver,
            limit=limit,
            offset=offset,
        )

    def stints(self, season: int, round: int, *, driver: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._get(
            f"/historical/{season}/{round}/stints",
            driver=driver,
            limit=limit,
            offset=offset,
        )

    def sprint(self, season: int, round: int, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(f"/historical/{season}/{round}/sprint", series, limit, offset)

    def sprint_qualifying(self, season: int, round: int, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(
            f"/historical/{season}/{round}/sprint/qualifying", series, limit, offset
        )

    def practice(self, season: int, round: int, session: str, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(
            f"/historical/{season}/{round}/practice/{session}", series, limit, offset
        )

    def fastest_laps(self, season: int, round: int, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(f"/historical/{season}/{round}/fastestlaps", series, limit, offset)

    def laps_led(self, season: int, round: int, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(f"/historical/{season}/{round}/lapsled", series, limit, offset)

    def weather(self, season: int, round: int, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(f"/historical/{season}/{round}/weather", series, limit, offset)

    def driver_standings(self, season: int, round: Optional[int] = None, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        """Season driver standings, or standings after ``round`` when given."""
        path = (
            f"/historical/{season}/{round}/driverStandings"
            if round is not None
            else f"/historical/{season}/driverStandings"
        )
        return self._paged(path, series, limit, offset)

    def constructor_standings(self, season: int, round: Optional[int] = None, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        """Season constructor standings, or standings after ``round`` when given."""
        path = (
            f"/historical/{season}/{round}/constructorStandings"
            if round is not None
            else f"/historical/{season}/constructorStandings"
        )
        return self._paged(path, series, limit, offset)

    def drivers(self, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged("/historical/drivers", series, limit, offset)

    def get_driver(self, driver_id: str) -> Any:
        return self._get(f"/historical/drivers/{driver_id}")

    def driver_career(self, driver_id: str) -> Any:
        return self._get(f"/historical/drivers/{driver_id}/career")

    def driver_seasons(self, driver_id: str, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(f"/historical/drivers/{driver_id}/seasons", series, limit, offset)

    def driver_circuits(self, driver_id: str, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(f"/historical/drivers/{driver_id}/circuits", series, limit, offset)

    def driver_results(self, driver_id: str, *, season: Optional[int] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._get(
            f"/historical/drivers/{driver_id}/results",
            season=season,
            limit=limit,
            offset=offset,
        )

    def constructors(self, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged("/historical/constructors", series, limit, offset)

    def get_constructor(self, constructor_id: str) -> Any:
        return self._get(f"/historical/constructors/{constructor_id}")

    def constructor_reliability(self, constructor_id: str, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(
            f"/historical/constructors/{constructor_id}/reliability", series, limit, offset
        )

    def constructor_seasons(self, constructor_id: str, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(
            f"/historical/constructors/{constructor_id}/seasons", series, limit, offset
        )

    def circuits(self, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged("/historical/circuits", series, limit, offset)

    def get_circuit(self, circuit_id: str) -> Any:
        return self._get(f"/historical/circuits/{circuit_id}")

    def circuit_races(self, circuit_id: str, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged(f"/historical/circuits/{circuit_id}/races", series, limit, offset)

    def points_systems(self, *, series: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Any:
        return self._paged("/historical/pointssystems", series, limit, offset)


class IndyCarNamespace(_Namespace):
    """IndyCar seasons, races, drivers and standings (``/v1/indycar/*``)."""

    def seasons(self) -> Any:
        return self._get("/indycar/seasons")

    def races(self, year: int) -> Any:
        return self._get(f"/indycar/seasons/{year}/races")

    def drivers(self) -> Any:
        return self._get("/indycar/drivers")

    def standings(self) -> Any:
        return self._get("/indycar/standings")

    def race_results(self, race_id: str) -> Any:
        return self._get(f"/indycar/races/{race_id}/results")


class InsightsNamespace(_Namespace):
    """Post-race predictive-model analytics bundles (``/v1/insights/*``).

    The strategic predictions in a race bundle require Developer or higher; Free
    receives the descriptive data plus tyre state.
    """

    def list_races(self) -> Any:
        return self._get("/insights/races")

    def get_race(self, race_id: str) -> Any:
        return self._get(f"/insights/races/{race_id}")

    def get_model_meta(self) -> Any:
        return self._get("/insights/model-meta")


class TelemetryNamespace(_Namespace):
    """Post-session per-lap telemetry analytics (``/v1/telemetry/*``)."""

    def get_race_laps(
        self,
        race_id: str,
        *,
        driver_id: Optional[str] = None,
        lap_number: Optional[int] = None,
    ) -> Any:
        return self._get(
            f"/telemetry/races/{race_id}/laps",
            driverId=driver_id,
            lapNumber=lap_number,
        )

    def get_driver_laps(self, race_id: str, driver_id: str) -> Any:
        return self._get(f"/telemetry/races/{race_id}/drivers/{driver_id}/laps")

    def get_lap_comparison(self, race_id: str, lap_number: int) -> Any:
        """All drivers for one lap, for cross-driver comparison."""
        return self._get(f"/telemetry/races/{race_id}/laps/{lap_number}")

    def get_race_summary(self, race_id: str) -> Any:
        return self._get(f"/telemetry/races/{race_id}/summary")


class ModelsNamespace(_Namespace):
    """Public model manifest and scorecards (``/v1/models/*``)."""

    def manifest(self) -> Any:
        """What each production model predicts, its calibration tier and last retrain."""
        return self._get("/models/manifest")

    def scorecard(self) -> Any:
        return self._get("/models/scorecard")

    def race_winner_record(self) -> Any:
        """Race by race, whether our lights-out winner odds beat the market's."""
        return self._get("/models/scorecard/race-winner")


class LinesNamespace(_Namespace):
    """Model-implied fair odds lines (``/v1/lines``). Requires the analytics
    entitlement (Custom plan)."""

    def list(self, *, limit: Optional[int] = None) -> Any:
        return self._get("/lines", limit=limit)

    def get(
        self,
        race_id: str,
        *,
        checkpoint: Optional[str] = None,
        market: Optional[str] = None,
    ) -> Any:
        """``checkpoint``: pre_weekend, fp1_end, fp2_end, fp3_end, sq_end, q_end,
        lights_out. ``market``: winner, podium, top6, h2h, pole."""
        return self._get(f"/lines/{race_id}", checkpoint=checkpoint, market=market)


class AnalyticsNamespace(_Namespace):
    """Live model analytics (``/v1/analytics/*``). Custom plan."""

    def status(self) -> Any:
        return self._get("/analytics/status")

    def h2h(self, driver_a: str, driver_b: str) -> Any:
        """P(driver A finishes ahead of driver B). Drivers are a car number or slug."""
        return self._get("/analytics/h2h", driverA=driver_a, driverB=driver_b)

    def position_at_lap(
        self, *, lap: Optional[int] = None, laps_ahead: Optional[int] = None
    ) -> Any:
        return self._get("/analytics/position-at-lap", lap=lap, lapsAhead=laps_ahead)


class PreviewNamespace(_Namespace):
    """Session previews (``/v1/preview/*``); detail depends on plan."""

    def upcoming(self) -> Any:
        return self._get("/preview/upcoming")

    def get(self, session_id: str) -> Any:
        return self._get(f"/preview/{session_id}")


class StrategyNamespace(_Namespace):
    """Strategy teasers and recaps (``/v1/strategy/*``)."""

    def preview_next(self) -> Any:
        return self._get("/strategy/preview/next")

    def preview(self, race_id: str) -> Any:
        return self._get(f"/strategy/preview/{race_id}")

    def recap(self, race_id: str) -> Any:
        return self._get(f"/strategy/recap/{race_id}")


class UsageNamespace(_Namespace):
    """Delivery usage, subscription and billing plan for the authenticated client."""

    def current(self) -> Any:
        return self._get("/usage")

    def by_feed(self) -> Any:
        return self._get("/usage/by-feed")

    def latency(self) -> Any:
        return self._get("/usage/latency")

    def hourly(self) -> Any:
        return self._get("/usage/hourly")

    def history(self) -> Any:
        return self._get("/usage/history")

    def subscription(self) -> Any:
        return self._get("/subscription")

    def billing_plan(self) -> Any:
        return self._get("/billing/plan")

    def tiers(self) -> Any:
        """The public tier comparison matrix (no authentication needed)."""
        return self._get("/billing/tiers")


def iter_sse(lines: Iterator[str]) -> Iterator[Tuple[str, Any]]:
    """Parse Server-Sent-Event lines into ``(event, data)`` pairs.

    ``data`` is JSON-decoded when possible. ``ping`` keep-alives are skipped.
    """
    event = "message"
    data: list = []
    for line in lines:
        if line == "":
            if data:
                raw = "\n".join(data)
                if event != "ping":
                    try:
                        yield event, json.loads(raw)
                    except ValueError:
                        yield event, raw
            event, data = "message", []
        elif line.startswith(":"):
            continue
        elif line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
