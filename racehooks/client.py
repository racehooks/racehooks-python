"""Synchronous REST client for the RaceHooks API.

    from racehooks import RaceHooks

    rh = RaceHooks(client_id="...", client_secret="...")

    # Fantasy
    scores = rh.fantasy.get_race_scores("2026-bahrain-r1")
    pits = rh.fantasy.get_session_pit_times("2026-bahrain-r1_Race")

    # Core
    feeds = rh.feeds.list()
    events = rh.events.list(upcoming=True)
    ctx = rh.live.context()

    # Session replay
    rh.simulate.sessions(year=2026)
    rh.simulate.prepare("2026-great-britain_r")

Authentication uses the OAuth 2 client-credentials flow: the client exchanges
``client_id`` + ``client_secret`` for a short-lived Bearer token on the first
request and refreshes it automatically before expiry. Credentials come from the
RaceHooks console (https://racehooks.io/console) — never hardcode them.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple

import httpx

from .models import (
    CreateWebhookResult,
    EventList,
    FeedList,
    DemoSession,
    LiveContext,
    WebhookEndpoint,
    WebhookEndpointList,
    RaceScores,
    ReplayableSessionList,
    ReplayQuota,
    SessionPitTimes,
    SessionScores,
    SimulateArtifact,
    WebhookList,
    WebhookLogList,
    WebhookTestResult,
)

from .namespaces import (
    AnalyticsNamespace,
    DataNamespace,
    HistoricalNamespace,
    IndyCarNamespace,
    InsightsNamespace,
    LinesNamespace,
    ModelsNamespace,
    PreviewNamespace,
    StrategyNamespace,
    TelemetryNamespace,
    UsageNamespace,
    _data,
    _q,
    iter_sse,
)

DEFAULT_BASE_URL = "https://api.racehooks.io"
DEFAULT_TIMEOUT = 30.0
#: Refresh the token this many seconds before its advertised expiry.
_TOKEN_SKEW_SECONDS = 60


class RaceHooksError(Exception):
    """Base class for all RaceHooks REST client errors."""


class RaceHooksAuthError(RaceHooksError):
    """Raised when the OAuth client-credentials exchange fails."""


class RaceHooksAPIError(RaceHooksError):
    """Raised on a non-2xx API response.

    :ivar status_code: The HTTP status code.
    :ivar body: The raw response body text.
    """

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        message = body.strip() or f"HTTP {status_code}"
        super().__init__(f"RaceHooks API error {status_code}: {message}")


def _pagination_params(limit: Optional[int], offset: Optional[int]) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    return params


class RaceHooks:
    """The RaceHooks REST client — entry point for all API operations.

    :param client_id: OAuth client id from the RaceHooks console.
    :param client_secret: OAuth client secret from the RaceHooks console.
    :param base_url: API base URL (override for testing). ``/v1`` is appended
        to every request path.
    :param timeout: Per-request timeout in seconds.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not client_id:
            raise ValueError("client_id is required")
        if not client_secret:
            raise ValueError("client_secret is required")

        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

        self._http = httpx.Client(timeout=timeout)
        self._lock = threading.Lock()
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0

        # API namespaces.
        self.fantasy = FantasyNamespace(self)
        self.webhooks = WebhooksNamespace(self)
        self.feeds = FeedsNamespace(self)
        self.events = EventsNamespace(self)
        self.live = LiveNamespace(self)
        self.simulate = SimulateNamespace(self)
        self.data = DataNamespace(self)
        self.historical = HistoricalNamespace(self)
        self.indycar = IndyCarNamespace(self)
        self.insights = InsightsNamespace(self)
        self.telemetry = TelemetryNamespace(self)
        self.models = ModelsNamespace(self)
        self.lines = LinesNamespace(self)
        self.analytics = AnalyticsNamespace(self)
        self.preview = PreviewNamespace(self)
        self.strategy = StrategyNamespace(self)
        self.usage = UsageNamespace(self)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "RaceHooks":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> str:
        """Exchange client credentials for a Bearer token.

        Called automatically before any request when the token is absent or
        expired, so you rarely need to call this directly.

        :raises RaceHooksAuthError: on invalid credentials or a non-200 response.
        """
        try:
            resp = self._http.post(
                f"{self._base_url}/v1/oauth",
                json={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise RaceHooksAuthError(f"Authentication request failed: {exc}") from exc

        if resp.status_code != 200:
            raise RaceHooksAuthError(
                f"Authentication failed ({resp.status_code}): {resp.text.strip()}"
            )

        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RaceHooksAuthError("No access_token in OAuth response")

        expires_in = data.get("expires_in")
        # Guard against a malformed/zero expires_in; clamp the skew to >= 0 so
        # we never store a past expiry and trigger a re-auth storm.
        if isinstance(expires_in, (int, float)) and expires_in > 0:
            lifetime = max(0.0, float(expires_in) - _TOKEN_SKEW_SECONDS)
        else:
            lifetime = 55 * 60  # default: 55 minutes

        with self._lock:
            self._access_token = token
            self._token_expiry = time.time() + lifetime
        return token

    def _get_token(self) -> str:
        with self._lock:
            if self._access_token and time.time() < self._token_expiry:
                return self._access_token
        return self.authenticate()

    def _invalidate_token(self) -> None:
        with self._lock:
            self._access_token = None
            self._token_expiry = 0.0

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
        _retried: bool = False,
    ) -> Any:
        """Send an authenticated request; return the decoded JSON body.

        Adds the Bearer header, retries once on a 401 (token may have expired
        mid-flight), and raises a typed error on any non-2xx response.
        """
        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        try:
            resp = self._http.request(
                method,
                f"{self._base_url}/v1{path}",
                params=params or None,
                json=json_body,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise RaceHooksError(f"{method} {path} failed: {exc}") from exc

        # Token expired mid-flight — invalidate the cache and retry once.
        if resp.status_code == 401 and not _retried:
            self._invalidate_token()
            return self._request(
                method, path, params=params, json_body=json_body, _retried=True
            )

        if not (200 <= resp.status_code < 300):
            raise RaceHooksAPIError(resp.status_code, resp.text)

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, json_body: Optional[Any] = None) -> Any:
        return self._request("POST", path, json_body=json_body)

    def _patch(self, path: str, json_body: Any) -> Any:
        return self._request("PATCH", path, json_body=json_body)

    def _delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def stream(self, feeds: Optional[List[str]] = None) -> Iterator[Tuple[str, Any]]:
        """Stream feeds over Server-Sent Events (``GET /v1/stream``).

        No public webhook server is needed. Yields ``(feed_id, payload)`` pairs
        while the connection stays open; ``ping`` keep-alives are skipped. Pass
        ``feeds=["events.race", "timing.data"]`` or omit for every feed your tier
        allows. Reconnecting is up to the caller.
        """
        token = self._get_token()
        params = {"feeds": ",".join(feeds) if feeds else "*"}
        try:
            with self._http.stream(
                "GET",
                f"{self._base_url}/v1/stream",
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "text/event-stream",
                },
                timeout=httpx.Timeout(self._timeout, read=None),
            ) as resp:
                if resp.status_code != 200:
                    resp.read()
                    raise RaceHooksAPIError(resp.status_code, resp.text)
                yield from iter_sse(resp.iter_lines())
        except httpx.HTTPError as exc:
            raise RaceHooksError(f"GET /stream failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Fantasy
# ---------------------------------------------------------------------------


class FantasyNamespace:
    """Pit-stop leaderboards and estimated F1 Fantasy points per driver.

    All three endpoints require a paid plan (Developer or higher).
    """

    def __init__(self, client: RaceHooks) -> None:
        self._client = client

    def get_race_scores(
        self, race_id: str, session: Optional[str] = None
    ) -> RaceScores:
        """Estimated fantasy points per driver for a completed session.

        Defaults to the Grand Prix; pass ``session="sprint"`` to score the
        Sprint (compressed points table). ``session_type`` on the response
        echoes which session was scored.
        """
        # The API querystring accepts session=sprint (default = Grand Prix);
        # only the Sprint needs an explicit param.
        params = {"session": "sprint"} if session == "sprint" else None
        res = self._client._get(f"/fantasy/races/{race_id}/scores", params)
        return RaceScores.model_validate(res["data"])

    def get_session_scores(self, session_id: str) -> SessionScores:
        """Running (provisional) fantasy score for each driver while a session
        is live.

        Position, teammate and DNF components update live; grid-derived and
        fastest-lap components stay ``None`` until the session ends (use
        :meth:`get_race_scores` for the final breakdown). ``live`` is ``False``
        and ``scores`` is empty when no session is currently live for this id.
        """
        res = self._client._get(f"/fantasy/session/{session_id}/scores")
        return SessionScores.model_validate(res["data"])

    def get_session_pit_times(self, session_id: str) -> SessionPitTimes:
        """Stationary pit-stop time rankings for a session.

        Each entry's ``pit_stop_time_sec`` is the seconds the car is stopped in
        its box.
        """
        res = self._client._get(f"/fantasy/session/{session_id}/pit-times")
        return SessionPitTimes.model_validate(res["data"])

    def get_prices(self, season: int, round: Optional[int] = None) -> Any:
        """RaceHooks-generated fantasy prices and per-round price history
        (``GET /v1/fantasy/prices``). An estimate that may differ from the game.
        Returns the decoded ``data`` payload."""
        return _data(self._client._get("/fantasy/prices", _q(season=season, round=round)))


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


class WebhooksNamespace:
    """Manage webhook endpoints, their feed subscriptions, secrets, delivery
    logs and test sends.

    An endpoint is one URL + signing secret that can carry many feeds. Plan
    limits cap endpoints and feeds per endpoint (HTTP 402 when exceeded).
    """

    def __init__(self, client: RaceHooks) -> None:
        self._client = client

    def create(
        self,
        *,
        webhook_url: str,
        feed_id: Optional[str] = None,
        feed_ids: Optional[List[str]] = None,
        subscriptions: Optional[List[Dict[str, Any]]] = None,
        webhook_method: str = "post",
        filters: Optional[Dict[str, Any]] = None,
        series_id: Optional[str] = None,
    ) -> CreateWebhookResult:
        """Create a webhook endpoint subscribed to one or more feeds.

        Give exactly one of ``feed_id`` (single feed), ``feed_ids`` (a list;
        ``"*"`` and group globs such as ``"analytics.*"`` are accepted) or
        ``subscriptions`` (``[{"feedId": ..., "filters": {...}}]`` for per-feed
        filters). ``filters`` are endpoint-wide defaults.

        The returned ``webhook_secret`` is shown **only once** — store it now to
        verify delivery signatures.
        """
        given = [x for x in (feed_id, feed_ids, subscriptions) if x is not None]
        if len(given) != 1:
            raise ValueError(
                "pass exactly one of feed_id, feed_ids or subscriptions"
            )
        body: Dict[str, Any] = {
            "webhookUrl": webhook_url,
            "webhookMethod": webhook_method,
            "filters": filters or {},
        }
        if series_id is not None:
            body["seriesId"] = series_id
        if subscriptions is not None:
            body["subscriptions"] = subscriptions
        elif feed_ids is not None:
            body["feedIds"] = feed_ids
        else:
            body["feedId"] = feed_id
        res = self._client._post("/webhooks", body)
        return CreateWebhookResult.model_validate(res["data"])

    def list(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> WebhookList:
        """List feed subscriptions, one row per (endpoint, feed)
        (``GET /v1/webhooks?shape=flat``). Use :meth:`list_endpoints` for the
        grouped view."""
        params = _pagination_params(limit, offset)
        params["shape"] = "flat"
        res = self._client._get("/webhooks", params)
        return WebhookList.model_validate(res["data"])

    def list_endpoints(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> WebhookEndpointList:
        """List endpoints, each grouping its feed subscriptions
        (``GET /v1/webhooks``, the server default)."""
        res = self._client._get("/webhooks", _pagination_params(limit, offset))
        return WebhookEndpointList.model_validate(res["data"])

    def get(self, webhook_id: str) -> WebhookEndpoint:
        """Retrieve one endpoint with its feed subscriptions and 7-day stats."""
        res = self._client._get(f"/webhooks/{webhook_id}")
        return WebhookEndpoint.model_validate(res["data"]["endpoint"])

    def update(
        self,
        webhook_id: str,
        *,
        webhook_url: Optional[str] = None,
        webhook_method: Optional[str] = None,
        active: Optional[bool] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> WebhookEndpoint:
        """Patch an endpoint. Only provided fields are sent and they cascade to
        every feed on the endpoint; use :meth:`update_feed` for one feed."""
        body: Dict[str, Any] = {}
        if webhook_url is not None:
            body["webhookUrl"] = webhook_url
        if webhook_method is not None:
            body["webhookMethod"] = webhook_method
        if active is not None:
            body["active"] = active
        if filters is not None:
            body["filters"] = filters
        res = self._client._patch(f"/webhooks/{webhook_id}", body)
        return WebhookEndpoint.model_validate(res["data"]["endpoint"])

    def delete(self, webhook_id: str) -> None:
        """Delete an endpoint and all of its feed subscriptions."""
        self._client._delete(f"/webhooks/{webhook_id}")

    def add_feeds(
        self,
        webhook_id: str,
        *,
        feed_ids: Optional[List[str]] = None,
        subscriptions: Optional[List[Dict[str, Any]]] = None,
    ) -> WebhookEndpoint:
        """Add feeds to an existing endpoint (same URL and secret). Feeds already
        on the endpoint are skipped."""
        if (feed_ids is None) == (subscriptions is None):
            raise ValueError("pass exactly one of feed_ids or subscriptions")
        body: Dict[str, Any] = (
            {"subscriptions": subscriptions}
            if subscriptions is not None
            else {"feedIds": feed_ids}
        )
        res = self._client._post(f"/webhooks/{webhook_id}/feeds", body)
        return WebhookEndpoint.model_validate(res["data"]["endpoint"])

    def remove_feed(self, webhook_id: str, feed_id: str) -> None:
        """Remove one feed from an endpoint. Removing the last feed deletes it."""
        self._client._delete(f"/webhooks/{webhook_id}/feeds/{feed_id}")

    def update_feed(
        self,
        webhook_id: str,
        feed_id: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        active: Optional[bool] = None,
    ) -> Any:
        """Update one feed subscription's filters or active flag. Returns the
        decoded ``data`` payload."""
        body: Dict[str, Any] = {}
        if filters is not None:
            body["filters"] = filters
        if active is not None:
            body["active"] = active
        res = self._client._patch(f"/webhooks/{webhook_id}/feeds/{feed_id}", body)
        return _data(res)

    def test(self, webhook_id: str) -> WebhookTestResult:
        """Fire a test payload at the webhook URL immediately."""
        res = self._client._post(f"/webhooks/{webhook_id}/test")
        return WebhookTestResult.model_validate(res["data"])

    def logs(
        self,
        webhook_id: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> WebhookLogList:
        """Retrieve delivery logs for a webhook."""
        res = self._client._get(
            f"/webhooks/{webhook_id}/logs", _pagination_params(limit, offset)
        )
        return WebhookLogList.model_validate(res["data"])

    def deliveries(
        self,
        *,
        mode: Optional[str] = None,
        since: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        """Recent deliveries across all your endpoints, newest first, with a
        summary (sent / ok / retried / failed / p50 / p99). ``mode`` is one of
        ``live``, ``replay``, ``test`` (``GET /v1/webhooks/deliveries``)."""
        res = self._client._get(
            "/webhooks/deliveries", _q(mode=mode, since=since, limit=limit)
        )
        return _data(res)

    def get_secret(self, webhook_id: str) -> str:
        """Retrieve the HMAC signing secret for a webhook."""
        res = self._client._get(f"/webhooks/{webhook_id}/secret")
        return res["data"]["webhookSecret"]

    def rotate_secret(self, webhook_id: str) -> str:
        """Rotate the HMAC signing secret and return the new one."""
        res = self._client._post(f"/webhooks/{webhook_id}/rotate-secret")
        return res["data"]["webhookSecret"]


# ---------------------------------------------------------------------------
# Feeds / Events / Live
# ---------------------------------------------------------------------------


class FeedsNamespace:
    """The RaceHooks feed catalog."""

    def __init__(self, client: RaceHooks) -> None:
        self._client = client

    def list(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> FeedList:
        """List available feeds (``GET /v1/feeds``)."""
        res = self._client._get("/feeds", _pagination_params(limit, offset))
        return FeedList.model_validate(res["data"])

    def example(self, feed_id: str) -> Any:
        """The most recent delivered payload for a feed
        (``GET /v1/feeds/{feedId}/example``), for inspecting payload structure."""
        return _data(self._client._get(f"/feeds/{feed_id}/example"))


class EventsNamespace:
    """The race-weekend event calendar."""

    def __init__(self, client: RaceHooks) -> None:
        self._client = client

    def list(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        upcoming: bool = False,
        season: Optional[int] = None,
        year: Optional[Any] = None,
        order: Optional[str] = None,
    ) -> EventList:
        """List calendar events and their sessions (``GET /v1/events``).

        ``season`` filters to one year (``year`` is the older alias); ``order``
        is ``asc`` (default) or ``desc``.
        """
        params = _pagination_params(limit, offset)
        if upcoming:
            params["upcoming"] = 1
        if season is not None:
            params["season"] = season
        if year is not None:
            params["year"] = year
        if order is not None:
            params["order"] = order
        res = self._client._get("/events", params)
        return EventList.model_validate(res["data"])


class LiveNamespace:
    """The current live-session context snapshot."""

    def __init__(self, client: RaceHooks) -> None:
        self._client = client

    def context(self) -> LiveContext:
        """Fetch the current live-session context (``GET /v1/live/context``).

        When no session is live, ``active`` is ``False``.
        """
        res = self._client._get("/live/context")
        return LiveContext.model_validate(res["data"])


class SimulateNamespace:
    """Session replay: prepare a completed session's recorded-playback artifact.

    Playback itself streams from the simulate-stream service. Any authenticated
    tier can list and prepare real sessions; tier controls the artifact profile
    (``lite`` vs ``full``) and the replay quota.
    """

    def __init__(self, client: RaceHooks) -> None:
        self._client = client

    def sessions(
        self,
        *,
        year: Optional[int] = None,
        type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> ReplayableSessionList:
        """List completed sessions available for replay.

        ``type`` is one of ``race``, ``qualifying``, ``sprint``, ``practice``
        (``GET /v1/simulate/sessions``). Self-serve tiers see the current
        season plus the demo session; ``restricted_to_season`` reports the clamp.
        """
        params = _pagination_params(limit, offset)
        if year is not None:
            params["year"] = year
        if type is not None:
            params["type"] = type
        res = self._client._get("/simulate/sessions", params)
        return ReplayableSessionList.model_validate(res["data"])

    def demo(self) -> DemoSession:
        """The curated demo session (``GET /v1/simulate/demo``)."""
        res = self._client._get("/simulate/demo")
        return DemoSession.model_validate(res["data"])

    def quota(self) -> ReplayQuota:
        """Distinct-session replay quota for your tier (``GET /v1/simulate/quota``)."""
        res = self._client._get("/simulate/quota")
        return ReplayQuota.model_validate(res["data"])

    def prepare(self, session_id: str) -> SimulateArtifact:
        """Ensure a session's artifact exists, triggering generation if cold
        (``POST /v1/simulate/prepare``)."""
        res = self._client._post("/simulate/prepare", {"sessionId": session_id})
        return SimulateArtifact.model_validate(res["data"])

    def status(self, session_id: str) -> SimulateArtifact:
        """Whether a session's artifact is ready to stream
        (``GET /v1/simulate/status``)."""
        res = self._client._get("/simulate/status", {"session": session_id})
        return SimulateArtifact.model_validate(res["data"])


__all__: List[str] = [
    "RaceHooks",
    "RaceHooksError",
    "RaceHooksAuthError",
    "RaceHooksAPIError",
    "FantasyNamespace",
    "WebhooksNamespace",
    "FeedsNamespace",
    "EventsNamespace",
    "LiveNamespace",
    "SimulateNamespace",
    "DataNamespace",
    "HistoricalNamespace",
    "IndyCarNamespace",
    "InsightsNamespace",
    "TelemetryNamespace",
    "ModelsNamespace",
    "LinesNamespace",
    "AnalyticsNamespace",
    "PreviewNamespace",
    "StrategyNamespace",
    "UsageNamespace",
    "DEFAULT_BASE_URL",
]
