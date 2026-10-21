"""Tests for the RaceHooks REST client.

These drive the client against an in-process ``httpx.MockTransport`` so no
network is touched: we assert the OAuth flow, Bearer header, path/query
building, typed-model parsing (including the ``pitStopTimeSec`` alias), the
401-refresh retry, and typed error raising.
"""

from __future__ import annotations

import json
from typing import List

import httpx
import pytest

from racehooks import (
    CreateWebhookResult,
    RaceHooks,
    RaceHooksAPIError,
    RaceHooksAuthError,
    RaceScores,
    SessionPitTimes,
    SessionScores,
)


def _make_client(handler) -> RaceHooks:
    """Build a RaceHooks whose HTTP layer is backed by ``handler``."""
    rh = RaceHooks("cid", "csecret", base_url="https://api.example.test")
    rh._http = httpx.Client(transport=httpx.MockTransport(handler))
    return rh


def _oauth_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={"access_token": "tok-123", "token_type": "Bearer", "expires_in": 3600},
    )


def test_oauth_flow_and_bearer_header() -> None:
    seen: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/v1/oauth":
            body = json.loads(request.content)
            assert body == {
                "grant_type": "client_credentials",
                "client_id": "cid",
                "client_secret": "csecret",
            }
            return _oauth_response()
        assert request.headers["Authorization"] == "Bearer tok-123"
        return httpx.Response(200, json={"data": {"feeds": [], "total": 0}})

    rh = _make_client(handler)
    rh.feeds.list()

    # First request authenticates, second is the actual call — token is cached.
    assert seen[0].url.path == "/v1/oauth"
    assert seen[1].url.path == "/v1/feeds"
    rh.feeds.list()  # no second oauth
    assert [r.url.path for r in seen].count("/v1/oauth") == 1


def test_get_race_scores_default_and_sprint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return _oauth_response()
        session = request.url.params.get("session")
        session_type = "sprint" if session == "sprint" else "grand_prix"
        return httpx.Response(
            200,
            json={
                "data": {
                    "raceId": "2026-bahrain-r1",
                    "sessionType": session_type,
                    "scores": [
                        {
                            "driver": "max_verstappen",
                            "tla": "VER",
                            "team": "Red Bull",
                            "breakdown": {
                                "racePosPoints": 25,
                                "qualiPosPoints": 10,
                                "q3Bonus": 3,
                                "positionsGained": None,
                                "positionsGainedPoints": 0,
                                "fastestLapPoints": 5,
                                "beatTeammateRace": 3,
                                "beatTeammateQuali": 2,
                                "dnfPenalty": 0,
                                "total": 48,
                            },
                        }
                    ],
                }
            },
        )

    rh = _make_client(handler)

    gp = rh.fantasy.get_race_scores("2026-bahrain-r1")
    assert isinstance(gp, RaceScores)
    assert gp.session_type == "grand_prix"
    assert gp.scores[0].tla == "VER"
    assert gp.scores[0].breakdown.total == 48
    assert gp.scores[0].breakdown.fastest_lap_points == 5

    sprint = rh.fantasy.get_race_scores("2026-bahrain-r1", session="sprint")
    assert sprint.session_type == "sprint"


def test_session_scores() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return _oauth_response()
        assert request.url.path == "/v1/fantasy/session/2026-bahrain-r1_Race/scores"
        return httpx.Response(
            200,
            json={
                "data": {
                    "sessionId": "2026-bahrain-r1_Race",
                    "live": True,
                    "provisional": True,
                    "sessionType": "grand_prix",
                    "currentLap": 12,
                    "totalLaps": 57,
                    "scores": [],
                }
            },
        )

    rh = _make_client(handler)
    res = rh.fantasy.get_session_scores("2026-bahrain-r1_Race")
    assert isinstance(res, SessionScores)
    assert res.live is True
    assert res.current_lap == 12
    assert res.total_laps == 57


def test_pit_times_uses_pit_stop_time_sec_alias() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return _oauth_response()
        return httpx.Response(
            200,
            json={
                "data": {
                    "sessionId": "2026-bahrain-r1_Race",
                    "source": "historical",
                    "fastestStop": {
                        "driver": "lando_norris",
                        "tla": "NOR",
                        "team": "McLaren",
                        "pitStopTimeSec": 2.31,
                        "lap": 18,
                    },
                    "stops": [
                        {
                            "driver": "lando_norris",
                            "tla": "NOR",
                            "team": "McLaren",
                            "pitStopTimeSec": 2.31,
                            "lap": 18,
                        }
                    ],
                }
            },
        )

    rh = _make_client(handler)
    res = rh.fantasy.get_session_pit_times("2026-bahrain-r1_Race")
    assert isinstance(res, SessionPitTimes)
    assert res.source == "historical"
    assert res.fastest_stop.pit_stop_time_sec == 2.31
    assert res.stops[0].pit_stop_time_sec == 2.31
    assert res.stops[0].lap == 18


def test_webhook_create_returns_secret_once() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return _oauth_response()
        assert request.method == "POST"
        body = json.loads(request.content)
        assert body["feedId"] == "events.race"
        assert body["webhookMethod"] == "post"
        return httpx.Response(
            200,
            json={
                "data": {
                    "webhook": {
                        "webhookId": "wh_1",
                        "feedId": "events.race",
                        "active": True,
                    },
                    "webhookSecret": "whsec_abc",
                    "tier": "developer",
                }
            },
        )

    rh = _make_client(handler)
    res = rh.webhooks.create(feed_id="events.race", webhook_url="https://x.test/hook")
    assert isinstance(res, CreateWebhookResult)
    assert res.webhook_secret == "whsec_abc"
    assert res.webhook.webhook_id == "wh_1"


def test_webhook_delete_returns_none_on_204() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return _oauth_response()
        assert request.method == "DELETE"
        return httpx.Response(204)

    rh = _make_client(handler)
    assert rh.webhooks.delete("wh_1") is None


def test_events_list_query_params() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return _oauth_response()
        assert request.url.params.get("upcoming") == "1"
        assert request.url.params.get("year") == "2026"
        assert request.url.params.get("limit") == "5"
        return httpx.Response(200, json={"data": {"events": [], "total": 0}})

    rh = _make_client(handler)
    rh.events.list(upcoming=True, year=2026, limit=5)


def test_401_triggers_reauth_and_retry() -> None:
    state = {"oauth_calls": 0, "feed_calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            state["oauth_calls"] += 1
            tok = f"tok-{state['oauth_calls']}"
            return httpx.Response(
                200,
                json={"access_token": tok, "token_type": "Bearer", "expires_in": 3600},
            )
        state["feed_calls"] += 1
        # First data call: pretend the token expired mid-flight.
        if state["feed_calls"] == 1:
            return httpx.Response(401, text="token expired")
        return httpx.Response(200, json={"data": {"feeds": [], "total": 0}})

    rh = _make_client(handler)
    rh.feeds.list()
    assert state["oauth_calls"] == 2  # re-authenticated after the 401
    assert state["feed_calls"] == 2  # retried the data call once


def test_api_error_raised_on_non_2xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return _oauth_response()
        return httpx.Response(403, text="Forbidden: paid plan required")

    rh = _make_client(handler)
    with pytest.raises(RaceHooksAPIError) as exc:
        rh.fantasy.get_race_scores("2026-bahrain-r1")
    assert exc.value.status_code == 403
    assert "paid plan" in exc.value.body


def test_auth_error_on_bad_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid_client")

    rh = _make_client(handler)
    with pytest.raises(RaceHooksAuthError):
        rh.feeds.list()


def test_missing_credentials_raise_value_error() -> None:
    with pytest.raises(ValueError):
        RaceHooks("", "secret")
    with pytest.raises(ValueError):
        RaceHooks("cid", "")


# ---------------------------------------------------------------------------
# Session replay (/v1/simulate/*)
# ---------------------------------------------------------------------------


def _replay_client(payload, seen: List[httpx.Request]) -> RaceHooks:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return _oauth_response()
        seen.append(request)
        return httpx.Response(200, json={"data": payload})

    return _make_client(handler)


def test_simulate_sessions_query_and_models() -> None:
    seen: List[httpx.Request] = []
    rh = _replay_client(
        {
            "sessions": [
                {
                    "sessionId": "2026-great-britain_r",
                    "sessionName": "Race",
                    "eventId": "e1",
                    "eventName": "British Grand Prix",
                    "circuitId": None,
                    "year": 2026,
                    "type": "r",
                    "startDate": "2026-07-05T14:00:00Z",
                    "analyticsPreview": True,
                }
            ],
            "total": 1,
            "limit": 20,
            "offset": 0,
            "restrictedToSeason": "2026",
        },
        seen,
    )
    res = rh.simulate.sessions(year=2026, type="race", limit=20, offset=0)
    req = seen[0]
    assert req.method == "GET" and req.url.path == "/v1/simulate/sessions"
    assert dict(req.url.params) == {
        "year": "2026",
        "type": "race",
        "limit": "20",
        "offset": "0",
    }
    assert res.restricted_to_season == "2026"
    assert res.sessions[0].session_id == "2026-great-britain_r"
    assert res.sessions[0].analytics_preview is True


def test_simulate_sessions_no_filters_sends_no_query() -> None:
    seen: List[httpx.Request] = []
    rh = _replay_client({"sessions": [], "total": 0}, seen)
    assert rh.simulate.sessions().sessions == []
    assert str(seen[0].url.query, "ascii") == ""


def test_simulate_status_and_prepare() -> None:
    art = {
        "sessionId": "2026-great-britain_r",
        "modelVersion": "v1",
        "profile": "lite",
        "status": "preparing",
        "formatFallback": True,
    }
    seen: List[httpx.Request] = []
    rh = _replay_client(art, seen)
    s = rh.simulate.status("2026-great-britain_r")
    assert seen[0].method == "GET" and seen[0].url.path == "/v1/simulate/status"
    assert seen[0].url.params["session"] == "2026-great-britain_r"
    assert s.status == "preparing" and s.format_fallback is True

    p = rh.simulate.prepare("2026-great-britain_r")
    assert seen[1].method == "POST" and seen[1].url.path == "/v1/simulate/prepare"
    assert json.loads(seen[1].content) == {"sessionId": "2026-great-britain_r"}
    assert p.profile == "lite" and p.model_version == "v1"


def test_simulate_demo_and_quota() -> None:
    seen: List[httpx.Request] = []
    rh = _replay_client({"sessionId": "2026-demo_r", "status": "ready"}, seen)
    demo = rh.simulate.demo()
    assert seen[0].url.path == "/v1/simulate/demo"
    assert demo.session_id == "2026-demo_r" and demo.status == "ready"

    seen2: List[httpx.Request] = []
    rh2 = _replay_client(
        {
            "limit": -1,
            "used": 2,
            "remaining": -1,
            "unlocked": ["a", "b"],
            "currentSeasonOnly": True,
        },
        seen2,
    )
    q = rh2.simulate.quota()
    assert seen2[0].url.path == "/v1/simulate/quota"
    assert q.limit == -1 and q.unlocked == ["a", "b"] and q.current_season_only


def test_simulate_error_raises_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return _oauth_response()
        return httpx.Response(403, text="forbidden")

    rh = _make_client(handler)
    with pytest.raises(RaceHooksAPIError) as ei:
        rh.simulate.quota()
    assert ei.value.status_code == 403
