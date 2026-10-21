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
from typing import Any, Dict, List, Optional

import httpx

from .models import (
    CreateWebhookResult,
    EventList,
    FeedList,
    DemoSession,
    LiveContext,
    RaceScores,
    ReplayableSessionList,
    ReplayQuota,
    SessionPitTimes,
    SessionScores,
    SimulateArtifact,
    Webhook,
    WebhookList,
    WebhookLogList,
    WebhookTestResult,
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


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


class WebhooksNamespace:
    """Manage webhook subscriptions, secrets, delivery logs and test sends."""

    def __init__(self, client: RaceHooks) -> None:
        self._client = client

    def create(
        self,
        *,
        feed_id: str,
        webhook_url: str,
        webhook_method: str = "post",
        filters: Optional[Dict[str, Any]] = None,
    ) -> CreateWebhookResult:
        """Create a webhook subscription.

        The returned ``webhook_secret`` is shown **only once** — store it now to
        verify delivery signatures.
        """
        body: Dict[str, Any] = {
            "feedId": feed_id,
            "webhookUrl": webhook_url,
            "webhookMethod": webhook_method,
            "filters": filters or {},
        }
        res = self._client._post("/webhooks", body)
        return CreateWebhookResult.model_validate(res["data"])

    def list(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> WebhookList:
        """List all webhook subscriptions for the authenticated client."""
        res = self._client._get("/webhooks", _pagination_params(limit, offset))
        return WebhookList.model_validate(res["data"])

    def get(self, webhook_id: str) -> Webhook:
        """Retrieve a single webhook by id."""
        res = self._client._get(f"/webhooks/{webhook_id}")
        return Webhook.model_validate(res["data"]["webhook"])

    def update(
        self,
        webhook_id: str,
        *,
        webhook_url: Optional[str] = None,
        webhook_method: Optional[str] = None,
        active: Optional[bool] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Webhook:
        """Patch a webhook subscription. Only provided fields are sent."""
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
        return Webhook.model_validate(res["data"]["webhook"])

    def delete(self, webhook_id: str) -> None:
        """Delete a webhook subscription."""
        self._client._delete(f"/webhooks/{webhook_id}")

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
        year: Optional[Any] = None,
    ) -> EventList:
        """List calendar events and their sessions (``GET /v1/events``)."""
        params = _pagination_params(limit, offset)
        if upcoming:
            params["upcoming"] = 1
        if year is not None:
            params["year"] = year
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
    "DEFAULT_BASE_URL",
]
