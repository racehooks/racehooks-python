"""Signature verification tests — sync, async, and framework integration."""

import hashlib
import hmac
import json
import time

import pytest

from racehooks import (
    AsyncWebhookHandler,
    WebhookHandler,
    WebhookSignatureError,
    WebhookTimestampError,
    sign_payload,
    verify_signature,
)

SECRET = "whsec_test_0123456789abcdef0123456789abcdef"

WEATHER_PAYLOAD = json.dumps(
    {
        "feed": "weatherdata",
        "sessionId": "2026-bahrain-r1",
        "data": {"AirTemp": "24.1", "TrackTemp": "31.0", "Rainfall": "0"},
    }
)


def server_sign(secret: str, body: str) -> str:
    """Reproduce the server's signing logic (webhookDelivery.ts)."""
    digest = hmac.new(
        secret.encode(), body.encode(), hashlib.sha256
    ).hexdigest()
    return "sha256=" + digest


# ── sign_payload ─────────────────────────────────────────────────────────────


def test_sign_payload_matches_server_format():
    ours = sign_payload(SECRET, WEATHER_PAYLOAD)
    theirs = server_sign(SECRET, WEATHER_PAYLOAD)
    assert ours == theirs
    assert ours.startswith("sha256=")
    assert len(ours) == len("sha256=") + 64


def test_sign_payload_bytes_and_str_match():
    assert sign_payload(SECRET, WEATHER_PAYLOAD.encode()) == sign_payload(
        SECRET, WEATHER_PAYLOAD
    )


# ── verify_signature ─────────────────────────────────────────────────────────


def test_valid_signature_passes():
    sig = server_sign(SECRET, WEATHER_PAYLOAD)
    assert verify_signature(WEATHER_PAYLOAD, sig, SECRET) is True


def test_tampered_body_fails():
    sig = server_sign(SECRET, WEATHER_PAYLOAD)
    tampered = WEATHER_PAYLOAD.replace("24.1", "99.9")
    with pytest.raises(WebhookSignatureError):
        verify_signature(tampered, sig, SECRET)


def test_wrong_secret_fails():
    sig = server_sign("whsec_wrong", WEATHER_PAYLOAD)
    with pytest.raises(WebhookSignatureError):
        verify_signature(WEATHER_PAYLOAD, sig, SECRET)


def test_missing_signature_fails():
    with pytest.raises(WebhookSignatureError, match="Missing signature"):
        verify_signature(WEATHER_PAYLOAD, None, SECRET)


def test_malformed_signature_fails():
    with pytest.raises(WebhookSignatureError, match="sha256="):
        verify_signature(WEATHER_PAYLOAD, "deadbeef", SECRET)


def test_empty_secret_fails():
    sig = server_sign(SECRET, WEATHER_PAYLOAD)
    with pytest.raises(WebhookSignatureError, match="No webhook secret"):
        verify_signature(WEATHER_PAYLOAD, sig, "")


def test_bytes_payload_verifies():
    sig = server_sign(SECRET, WEATHER_PAYLOAD)
    assert verify_signature(WEATHER_PAYLOAD.encode(), sig, SECRET) is True


# ── replay protection ────────────────────────────────────────────────────────


def test_fresh_delivery_within_tolerance_passes():
    sig = server_sign(SECRET, WEATHER_PAYLOAD)
    now_ms = int(time.time() * 1000)
    assert (
        verify_signature(
            WEATHER_PAYLOAD,
            sig,
            SECRET,
            timestamp=now_ms,
            tolerance_seconds=300,
        )
        is True
    )


def test_old_delivery_replay_fails():
    sig = server_sign(SECRET, WEATHER_PAYLOAD)
    old_ms = int(time.time() * 1000) - 10 * 60 * 1000  # 10 minutes ago
    with pytest.raises(WebhookTimestampError):
        verify_signature(
            WEATHER_PAYLOAD,
            sig,
            SECRET,
            timestamp=old_ms,
            tolerance_seconds=300,
        )


def test_missing_timestamp_when_required_fails():
    sig = server_sign(SECRET, WEATHER_PAYLOAD)
    with pytest.raises(WebhookTimestampError):
        verify_signature(WEATHER_PAYLOAD, sig, SECRET, tolerance_seconds=300)


# ── WebhookHandler ───────────────────────────────────────────────────────────


def test_handler_construct_event_returns_typed_event():
    handler = WebhookHandler(secret=SECRET)
    sig = server_sign(SECRET, WEATHER_PAYLOAD)
    event = handler.construct_event(WEATHER_PAYLOAD, sig)
    assert event.feed == "weatherdata"
    assert event.session_id == "2026-bahrain-r1"
    assert event.data["AirTemp"] == "24.1"


def test_handler_construct_raceevent():
    handler = WebhookHandler(secret=SECRET)
    body = json.dumps(
        {
            "feed": "raceevent",
            "sessionId": "2026-bahrain-r1",
            "event": "safety.car.deployed",
            "lap": 12,
            "utc": "2026-03-16T15:42:10.000Z",
            "data": {"type": "full"},
        }
    )
    sig = server_sign(SECRET, body)
    event = handler.construct_event(body, sig)
    assert event.feed == "raceevent"
    assert event.event == "safety.car.deployed"
    assert event.lap == 12


def test_handler_bad_signature_raises():
    handler = WebhookHandler(secret=SECRET)
    with pytest.raises(WebhookSignatureError):
        handler.construct_event(WEATHER_PAYLOAD, "sha256=bad")


def test_handler_requires_secret():
    with pytest.raises(ValueError):
        WebhookHandler(secret="")


# ── AsyncWebhookHandler ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_handler_construct_event():
    handler = AsyncWebhookHandler(secret=SECRET)
    sig = server_sign(SECRET, WEATHER_PAYLOAD)
    event = await handler.construct_event(WEATHER_PAYLOAD.encode(), sig)
    assert event.feed == "weatherdata"


@pytest.mark.asyncio
async def test_async_handler_bad_signature_raises():
    handler = AsyncWebhookHandler(secret=SECRET)
    with pytest.raises(WebhookSignatureError):
        await handler.construct_event(WEATHER_PAYLOAD, "sha256=bad")


# ── Flask integration ────────────────────────────────────────────────────────


def test_flask_integration():
    flask = pytest.importorskip("flask")
    from flask import Flask, request

    handler = WebhookHandler(secret=SECRET)
    app = Flask(__name__)
    received = {}

    @app.post("/webhook")
    def webhook():
        try:
            event = handler.construct_event(
                request.get_data(),
                request.headers.get("X-RaceHooks-Signature"),
                timestamp=request.headers.get("X-RaceHooks-Sent-At"),
            )
        except WebhookSignatureError as exc:
            return {"error": str(exc)}, 400
        received["event"] = event
        return {"received": True}, 200

    client = app.test_client()
    sig = server_sign(SECRET, WEATHER_PAYLOAD)

    ok = client.post(
        "/webhook",
        data=WEATHER_PAYLOAD,
        headers={
            "Content-Type": "application/json",
            "X-RaceHooks-Signature": sig,
        },
    )
    assert ok.status_code == 200
    assert ok.get_json()["received"] is True
    assert received["event"].feed == "weatherdata"

    bad = client.post(
        "/webhook",
        data=WEATHER_PAYLOAD.replace("24.1", "99.9"),
        headers={
            "Content-Type": "application/json",
            "X-RaceHooks-Signature": sig,
        },
    )
    assert bad.status_code == 400


# ── FastAPI integration (async) ──────────────────────────────────────────────


def test_fastapi_integration():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.testclient import TestClient

    handler = AsyncWebhookHandler(secret=SECRET)
    app = FastAPI()

    @app.post("/webhook")
    async def webhook(request: Request):
        body = await request.body()
        try:
            event = await handler.construct_event(
                body,
                request.headers.get("X-RaceHooks-Signature"),
                timestamp=request.headers.get("X-RaceHooks-Sent-At"),
            )
        except WebhookSignatureError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return {"received": True, "feed": event.feed}

    client = TestClient(app)
    sig = server_sign(SECRET, WEATHER_PAYLOAD)

    ok = client.post(
        "/webhook",
        content=WEATHER_PAYLOAD,
        headers={"X-RaceHooks-Signature": sig},
    )
    assert ok.status_code == 200
    assert ok.json() == {"received": True, "feed": "weatherdata"}

    bad = client.post(
        "/webhook",
        content=WEATHER_PAYLOAD,
        headers={"X-RaceHooks-Signature": "sha256=bad"},
    )
    assert bad.status_code == 400
