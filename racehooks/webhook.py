"""Webhook signature verification and event construction.

Mirrors the server-side signing in ``src/common/webhookDelivery.ts``::

    signPayload(secret, body) = "sha256=" + HMAC_SHA256(secret, body).hex()

The signed ``body`` is the exact raw JSON RaceHooks POSTs to your endpoint,
and the signature travels in the ``X-RaceHooks-Signature`` header. Always
verify against the **raw request body bytes** — re-serializing a parsed body
can change whitespace/key order and break verification.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional, Union

from .models.events import AnyEvent, parse_event

#: Header carrying the HMAC signature on every signed delivery.
SIGNATURE_HEADER = "X-RaceHooks-Signature"
#: Header carrying the send time (epoch milliseconds, as a string).
TIMESTAMP_HEADER = "X-RaceHooks-Sent-At"

_Body = Union[str, bytes]


class WebhookSignatureError(Exception):
    """Raised when webhook signature verification fails."""


class WebhookTimestampError(WebhookSignatureError):
    """Raised when a delivery is older than the configured tolerance.

    Subclasses :class:`WebhookSignatureError` so a single ``except`` clause can
    catch every verification failure.
    """


def _to_bytes(value: _Body) -> bytes:
    return value.encode("utf-8") if isinstance(value, str) else value


def sign_payload(secret: _Body, body: _Body) -> str:
    """Compute the signature for ``body`` in the exact server format.

    :returns: ``"sha256=<hex digest>"``.
    """
    digest = hmac.new(_to_bytes(secret), _to_bytes(body), hashlib.sha256).hexdigest()
    return "sha256=" + digest


def verify_signature(
    payload: _Body,
    signature_header: Optional[str],
    secret: _Body,
    *,
    timestamp: Optional[Union[str, int, float]] = None,
    tolerance_seconds: Optional[int] = None,
) -> bool:
    """Verify a webhook signature against the raw payload.

    :param payload: The raw request body (``str`` or ``bytes``) — *not* a
        parsed object.
    :param signature_header: The ``X-RaceHooks-Signature`` header value,
        e.g. ``"sha256=abc..."``.
    :param secret: The webhook signing secret.
    :param timestamp: The ``X-RaceHooks-Sent-At`` header (epoch ms). Required
        when ``tolerance_seconds`` is set.
    :param tolerance_seconds: If set to a positive integer, reject deliveries
        older than this many seconds (replay protection). ``None`` or ``0``
        disables the check (default behaviour when no tolerance is configured).
    :returns: ``True`` on success.
    :raises WebhookSignatureError: if the signature is missing or invalid.
    :raises WebhookTimestampError: if the delivery is too old.
    """
    if not secret:
        raise WebhookSignatureError("No webhook secret provided")
    if not signature_header:
        raise WebhookSignatureError("Missing signature header")

    sig = signature_header.strip()
    if not sig.startswith("sha256="):
        raise WebhookSignatureError(
            "Unexpected signature format (expected 'sha256=' prefix)"
        )

    expected = sign_payload(secret, payload)
    # Constant-time comparison to avoid timing oracles.
    if not hmac.compare_digest(sig, expected):
        raise WebhookSignatureError(
            "Signature mismatch — payload may be tampered or secret is wrong"
        )

    if tolerance_seconds is not None and tolerance_seconds > 0:
        if timestamp is None or timestamp == "":
            raise WebhookTimestampError(
                "Timestamp required for replay protection but none provided"
            )
        try:
            sent_at_ms = int(float(timestamp))
        except (TypeError, ValueError) as exc:
            raise WebhookTimestampError("Invalid timestamp header") from exc
        age_seconds = (time.time() * 1000 - sent_at_ms) / 1000
        if age_seconds > tolerance_seconds:
            raise WebhookTimestampError(
                f"Delivery is {round(age_seconds)}s old "
                f"(tolerance {tolerance_seconds}s)"
            )

    return True


class WebhookHandler:
    """Verify deliveries and construct typed events.

    ::

        handler = WebhookHandler(secret="whsec_...")

        @app.post("/webhook")
        def webhook():
            event = handler.construct_event(
                request.get_data(),
                request.headers.get("X-RaceHooks-Signature"),
                timestamp=request.headers.get("X-RaceHooks-Sent-At"),
            )
            if event.feed == "raceevent":
                print(event.event, event.data)
    """

    def __init__(self, secret: _Body, *, tolerance_seconds: int = 0) -> None:
        if not secret:
            raise ValueError("WebhookHandler requires a non-empty secret")
        self.secret = secret
        self.tolerance_seconds = tolerance_seconds

    def verify(
        self,
        payload: _Body,
        signature_header: Optional[str],
        *,
        timestamp: Optional[Union[str, int, float]] = None,
    ) -> bool:
        """Verify a signature; raise on failure. See :func:`verify_signature`."""
        return verify_signature(
            payload,
            signature_header,
            self.secret,
            timestamp=timestamp,
            tolerance_seconds=self.tolerance_seconds,
        )

    def construct_event(
        self,
        payload: _Body,
        signature_header: Optional[str],
        *,
        timestamp: Optional[Union[str, int, float]] = None,
    ) -> AnyEvent:
        """Verify the signature and parse the payload into a typed event.

        :raises WebhookSignatureError: on signature/timestamp failure.
        """
        self.verify(payload, signature_header, timestamp=timestamp)
        return parse_event(payload)


class AsyncWebhookHandler(WebhookHandler):
    """Async variant for FastAPI / aiohttp.

    Signature verification is CPU-bound and synchronous, but exposing an
    ``async`` API keeps call sites uniform in async frameworks::

        handler = AsyncWebhookHandler(secret="whsec_...")

        @app.post("/webhook")
        async def webhook(request: Request):
            body = await request.body()
            event = await handler.construct_event(
                body,
                request.headers.get("X-RaceHooks-Signature"),
                timestamp=request.headers.get("X-RaceHooks-Sent-At"),
            )
            return {"received": True, "feed": event.feed}
    """

    async def construct_event(  # type: ignore[override]
        self,
        payload: _Body,
        signature_header: Optional[str],
        *,
        timestamp: Optional[Union[str, int, float]] = None,
    ) -> AnyEvent:
        self.verify(payload, signature_header, timestamp=timestamp)
        return parse_event(payload)


__all__ = [
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    "WebhookSignatureError",
    "WebhookTimestampError",
    "WebhookHandler",
    "AsyncWebhookHandler",
    "sign_payload",
    "verify_signature",
]
