"""Tests for the data/analytics namespaces, endpoint-shaped webhooks, SSE
streaming and the timestamped (v1) webhook signature."""

from __future__ import annotations

import json
import time
from typing import List

import httpx
import pytest

from racehooks import (
    RaceHooks,
    WebhookHandler,
    WebhookSignatureError,
    WebhookTimestampError,
    sign_payload,
    sign_payload_v1,
    verify_signature,
)


def _client(handler) -> RaceHooks:
    rh = RaceHooks("cid", "csecret", base_url="https://api.example.test")
    rh._http = httpx.Client(transport=httpx.MockTransport(handler))
    return rh


def _router(seen: List[httpx.Request], body):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        seen.append(request)
        return httpx.Response(200, json=body)

    return handler


@pytest.mark.parametrize(
    "call,path,query",
    [
        (lambda rh: rh.data.get_race("r1"), "/v1/data/races/r1", {}),
        (
            lambda rh: rh.data.list_drivers(search="ver", active=True, limit=5),
            "/v1/data/drivers",
            {"search": "ver", "active": "true", "limit": "5"},
        ),
        (
            lambda rh: rh.data.get_race_telemetry_laps("r1", driver_id="d", lap=3),
            "/v1/data/races/r1/telemetry/laps",
            {"driverId": "d", "lap": "3"},
        ),
        (lambda rh: rh.historical.results(2021, 22), "/v1/historical/2021/22/results", {}),
        (
            lambda rh: rh.historical.driver_standings(2021, 5),
            "/v1/historical/2021/5/driverStandings",
            {},
        ),
        (lambda rh: rh.historical.driver_standings(2021), "/v1/historical/2021/driverStandings", {}),
        (lambda rh: rh.insights.get_race("r1"), "/v1/insights/races/r1", {}),
        (lambda rh: rh.insights.get_model_meta(), "/v1/insights/model-meta", {}),
        (lambda rh: rh.telemetry.get_lap_comparison("r1", 20), "/v1/telemetry/races/r1/laps/20", {}),
        (lambda rh: rh.models.manifest(), "/v1/models/manifest", {}),
        (
            lambda rh: rh.lines.get("r1", checkpoint="q_end", market="winner"),
            "/v1/lines/r1",
            {"checkpoint": "q_end", "market": "winner"},
        ),
        (
            lambda rh: rh.analytics.h2h("1", "33"),
            "/v1/analytics/h2h",
            {"driverA": "1", "driverB": "33"},
        ),
        (lambda rh: rh.strategy.recap("r1"), "/v1/strategy/recap/r1", {}),
        (lambda rh: rh.preview.upcoming(), "/v1/preview/upcoming", {}),
        (lambda rh: rh.indycar.standings(), "/v1/indycar/standings", {}),
        (lambda rh: rh.usage.billing_plan(), "/v1/billing/plan", {}),
        (lambda rh: rh.fantasy.get_prices(2026, 3), "/v1/fantasy/prices", {"season": "2026", "round": "3"}),
        (lambda rh: rh.feeds.example("events.race"), "/v1/feeds/events.race/example", {}),
        (
            lambda rh: rh.events.list(season=2026, order="desc"),
            "/v1/events",
            {"season": "2026", "order": "desc"},
        ),
        (
            lambda rh: rh.webhooks.deliveries(mode="live", limit=10),
            "/v1/webhooks/deliveries",
            {"mode": "live", "limit": "10"},
        ),
    ],
)
def test_get_paths_and_params(call, path, query) -> None:
    seen: List[httpx.Request] = []
    rh = _client(_router(seen, {"data": {"events": [], "ok": 1}}))
    call(rh)
    assert seen[0].method == "GET"
    assert seen[0].url.path == path
    assert dict(seen[0].url.params) == query
    assert seen[0].headers["Authorization"] == "Bearer t"


def test_namespace_returns_unwrapped_data() -> None:
    rh = _client(_router([], {"data": {"drivers": [1], "total": 1}}))
    assert rh.data.list_drivers() == {"drivers": [1], "total": 1}


def test_tiers_without_data_envelope() -> None:
    rh = _client(_router([], {"tiers": [{"tier": "free"}]}))
    assert rh.usage.tiers() == {"tiers": [{"tier": "free"}]}


ENDPOINT = {
    "webhookId": "wh_1",
    "webhookUrl": "https://x.test/h",
    "feedCount": 1,
    "subscriptions": [{"feedId": "events.race", "filters": {}, "active": True}],
}


def test_webhooks_get_update_read_endpoint_envelope() -> None:
    rh = _client(_router([], {"data": {"endpoint": ENDPOINT}}))
    ep = rh.webhooks.get("wh_1")
    assert ep.webhook_id == "wh_1" and ep.subscriptions[0].feed_id == "events.race"
    assert rh.webhooks.update("wh_1", active=False).feed_count == 1
    assert rh.webhooks.add_feeds("wh_1", feed_ids=["a"]).webhook_url == "https://x.test/h"


def test_webhooks_list_flat_and_grouped() -> None:
    seen: List[httpx.Request] = []
    rh = _client(
        _router(seen, {"data": {"webhooks": [{"webhookId": "w"}], "endpoints": [ENDPOINT], "total": 1}})
    )
    assert rh.webhooks.list().webhooks[0].webhook_id == "w"
    assert seen[0].url.params["shape"] == "flat"
    assert rh.webhooks.list_endpoints().endpoints[0].webhook_id == "wh_1"
    assert "shape" not in seen[1].url.params


def test_webhooks_create_multi_feed_body_and_result() -> None:
    seen: List[httpx.Request] = []
    rh = _client(
        _router(
            seen,
            {"data": {"webhookId": "wh_1", "subscriptions": [{"feedId": "a"}], "webhookSecret": "whsec_x"}},
        )
    )
    res = rh.webhooks.create(webhook_url="https://x.test/h", feed_ids=["a", "analytics.*"])
    body = json.loads(seen[0].content)
    assert body["feedIds"] == ["a", "analytics.*"] and "feedId" not in body
    assert res.webhook_id == "wh_1" and res.webhook_secret == "whsec_x"
    with pytest.raises(ValueError):
        rh.webhooks.create(webhook_url="https://x.test/h")
    with pytest.raises(ValueError):
        rh.webhooks.create(webhook_url="u", feed_id="a", feed_ids=["b"])


def test_feed_management_paths() -> None:
    seen: List[httpx.Request] = []
    rh = _client(_router(seen, {"data": {"ok": True}}))
    rh.webhooks.update_feed("wh_1", "events.race", filters={"drivers": ["VER"]}, active=True)
    rh.webhooks.remove_feed("wh_1", "events.race")
    assert (seen[0].method, seen[0].url.path) == ("PATCH", "/v1/webhooks/wh_1/feeds/events.race")
    assert json.loads(seen[0].content) == {"filters": {"drivers": ["VER"]}, "active": True}
    assert (seen[1].method, seen[1].url.path) == ("DELETE", "/v1/webhooks/wh_1/feeds/events.race")


def test_stream_parses_sse_and_skips_ping() -> None:
    sse = (
        "event: ping\ndata: {}\n\n"
        'event: events.race\ndata: {"lap": 3}\n\n'
        ": comment\n"
        "event: timing.data\ndata: not-json\n\n"
    )
    seen: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        seen.append(request)
        return httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})

    rh = _client(handler)
    events = list(rh.stream(["events.race", "timing.data"]))
    assert events == [("events.race", {"lap": 3}), ("timing.data", "not-json")]
    assert seen[0].url.params["feeds"] == "events.race,timing.data"


def test_stream_error_status_raises() -> None:
    from racehooks import RaceHooksAPIError

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        return httpx.Response(403, text="plan")

    with pytest.raises(RaceHooksAPIError):
        list(_client(handler).stream())


# ---- v1 signature -------------------------------------------------------

BODY = b'{"feed":"events.race","event":"x","session_id":"s","data":{}}'
SECRET = "whsec_test"


def _v1(offset_s: float = 0) -> str:
    return sign_payload_v1(SECRET, BODY, int(time.time() * 1000 + offset_s * 1000))


def test_v1_known_vector() -> None:
    import hashlib
    import hmac

    expected = hmac.new(b"s", b"123." + b"body", hashlib.sha256).hexdigest()
    assert sign_payload_v1("s", "body", 123) == f"t=123,v1={expected}"


def test_v1_verifies_and_tolerance() -> None:
    assert verify_signature(BODY, None, SECRET, signature_v1=_v1())
    assert verify_signature(BODY, _v1(), SECRET)  # v1 passed as the signature
    assert verify_signature(BODY, None, SECRET, signature_v1=_v1(-10), tolerance_seconds=300)
    with pytest.raises(WebhookTimestampError):
        verify_signature(BODY, None, SECRET, signature_v1=_v1(-1000), tolerance_seconds=300)
    with pytest.raises(WebhookTimestampError):
        verify_signature(BODY, None, SECRET, signature_v1=_v1(+1000), tolerance_seconds=300)


def test_v1_rejects_tampering() -> None:
    good = _v1()
    with pytest.raises(WebhookSignatureError):
        verify_signature(BODY + b" ", None, SECRET, signature_v1=good)
    t = good.split(",")[0]
    forged = t.replace(t[-1], "0" if t[-1] != "0" else "1") + "," + good.split(",")[1]
    with pytest.raises(WebhookSignatureError):
        verify_signature(BODY, None, SECRET, signature_v1=forged)
    with pytest.raises(WebhookSignatureError):
        verify_signature(BODY, None, SECRET, signature_v1="t=abc,v1=")


def test_legacy_still_works_and_require_v1() -> None:
    legacy = sign_payload(SECRET, BODY)
    assert verify_signature(BODY, legacy, SECRET)
    with pytest.raises(WebhookSignatureError):
        verify_signature(BODY, legacy, SECRET, require_v1=True)
    with pytest.raises(WebhookSignatureError):
        verify_signature(BODY, None, SECRET)


def test_handler_passes_v1() -> None:
    h = WebhookHandler(SECRET, tolerance_seconds=300, require_v1=True)
    ev = h.construct_event(BODY, sign_payload(SECRET, BODY), signature_v1=_v1())
    assert ev.feed == "events.race"
    with pytest.raises(WebhookSignatureError):
        h.construct_event(BODY, sign_payload(SECRET, BODY))
