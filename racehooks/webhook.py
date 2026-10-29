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
from typing import List, Optional, Tuple, Union

from .models.events import AnyEvent, parse_event

#: Header carrying the HMAC signature on every signed delivery.
SIGNATURE_HEADER = "X-RaceHooks-Signature"
#: Header carrying the send time (epoch milliseconds, as a string).
TIMESTAMP_HEADER = "X-RaceHooks-Sent-At"
#: Header carrying the timestamped signature ``t=<sentAtMs>,v1=<hmac of "t.body">``.
#: The send time is covered by the signature, so a tolerance check on it is
#: real replay protection (unlike ``X-RaceHooks-Sent-At``, which is unsigned).
SIGNATURE_V1_HEADER = "X-RaceHooks-Signature-V1"

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


def sign_payload_v1(secret: _Body, body: _Body, sent_at_ms: int) -> str:
    """Compute the timestamped v1 signature: ``"t=<ms>,v1=<hex>"`` where the
    HMAC covers ``"<ms>." + body``."""
    t = str(int(sent_at_ms))
    mac = hmac.new(_to_bytes(secret), t.encode("ascii") + b".", hashlib.sha256)
    mac.update(_to_bytes(body))
    return f"t={t},v1={mac.hexdigest()}"


def _parse_v1(header: str) -> Tuple[str, List[str]]:
    t = ""
    sigs: List[str] = []
    for part in header.split(","):
        key, sep, value = part.partition("=")
        if not sep or not key.strip():
            continue
        key, value = key.strip(), value.strip()
        if key == "t":
            t = value
        elif key == "v1" and value:
            sigs.append(value)
    return t, sigs


def _check_age(sent_at_ms: float, tolerance_seconds: int, signed: bool) -> None:
    age_seconds = (time.time() * 1000 - sent_at_ms) / 1000
    if age_seconds > tolerance_seconds:
        raise WebhookTimestampError(
            f"Delivery is {round(age_seconds)}s old (tolerance {tolerance_seconds}s)"
        )
    if signed and -age_seconds > tolerance_seconds:
        raise WebhookTimestampError(
            f"Delivery is timestamped {round(-age_seconds)}s in the future "
            f"(tolerance {tolerance_seconds}s)"
        )


def _verify_v1(
    payload: _Body, header: str, secret: _Body, tolerance_seconds: Optional[int]
) -> None:
    t, sigs = _parse_v1(header)
    if not t.isdigit() or not sigs:
        raise WebhookSignatureError(
            "Unexpected v1 signature format (expected 't=<ms>,v1=<hex>')"
        )
    expected = sign_payload_v1(secret, payload, int(t)).split("v1=", 1)[1]
    ok = False
    for candidate in sigs:  # no early exit: timing must not reveal which matched
        ok = hmac.compare_digest(candidate, expected) or ok
    if not ok:
        raise WebhookSignatureError(
            "Signature mismatch — payload or timestamp tampered, or secret is wrong"
        )
    if tolerance_seconds is not None and tolerance_seconds > 0:
        _check_age(float(t), tolerance_seconds, signed=True)


def verify_signature(
    payload: _Body,
    signature_header: Optional[str],
    secret: _Body,
    *,
    timestamp: Optional[Union[str, int, float]] = None,
    tolerance_seconds: Optional[int] = None,
    signature_v1: Optional[str] = None,
    require_v1: bool = False,
) -> bool:
    """Verify a webhook signature against the raw payload.

    :param payload: The raw request body (``str`` or ``bytes``) — *not* a
        parsed object.
    :param signature_header: The ``X-RaceHooks-Signature`` header value,
        e.g. ``"sha256=abc..."``.
    :param secret: The webhook signing secret.
    :param timestamp: The ``X-RaceHooks-Sent-At`` header (epoch ms). Required
        when ``tolerance_seconds`` is set.
    :param signature_v1: The ``X-RaceHooks-Signature-V1`` header
        (``t=<ms>,v1=<hex>``). When present it is verified instead of the legacy
        signature and ``tolerance_seconds`` is enforced on its *signed* send
        time, which makes it genuine replay protection. Passing the v1 value as
        ``signature_header`` also works.
    :param require_v1: Reject deliveries that carry no v1 signature.
    :param tolerance_seconds: If set to a positive integer, reject deliveries
        older than this many seconds (replay protection). ``None`` or ``0``
        disables the check (default behaviour when no tolerance is configured).
    :returns: ``True`` on success.
    :raises WebhookSignatureError: if the signature is missing or invalid.
    :raises WebhookTimestampError: if the delivery is too old.
    """
    if not secret:
        raise WebhookSignatureError("No webhook secret provided")
    sig = (signature_header or "").strip()
    v1 = (signature_v1 or "").strip() or (sig if sig.startswith("t=") else "")
    if v1:
        _verify_v1(payload, v1, secret, tolerance_seconds)
        return True
    if require_v1:
        raise WebhookSignatureError(
            "Missing X-RaceHooks-Signature-V1 header (require_v1 is set)"
        )
    if not sig:
        raise WebhookSignatureError("Missing signature header")
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
        _check_age(sent_at_ms, tolerance_seconds, signed=False)

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
            if event.feed == "events.race":
                print(event.event, event.data)
    """

    def __init__(
        self,
        secret: _Body,
        *,
        tolerance_seconds: int = 0,
        require_v1: bool = False,
    ) -> None:
        if not secret:
            raise ValueError("WebhookHandler requires a non-empty secret")
        self.secret = secret
        self.tolerance_seconds = tolerance_seconds
        self.require_v1 = require_v1

    def verify(
        self,
        payload: _Body,
        signature_header: Optional[str],
        *,
        timestamp: Optional[Union[str, int, float]] = None,
        signature_v1: Optional[str] = None,
    ) -> bool:
        """Verify a signature; raise on failure. See :func:`verify_signature`."""
        return verify_signature(
            payload,
            signature_header,
            self.secret,
            timestamp=timestamp,
            tolerance_seconds=self.tolerance_seconds,
            signature_v1=signature_v1,
            require_v1=self.require_v1,
        )

    def construct_event(
        self,
        payload: _Body,
        signature_header: Optional[str],
        *,
        timestamp: Optional[Union[str, int, float]] = None,
        signature_v1: Optional[str] = None,
    ) -> AnyEvent:
        """Verify the signature and parse the payload into a typed event.

        :raises WebhookSignatureError: on signature/timestamp failure.
        """
        self.verify(
            payload, signature_header, timestamp=timestamp, signature_v1=signature_v1
        )
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
        signature_v1: Optional[str] = None,
    ) -> AnyEvent:
        self.verify(
            payload, signature_header, timestamp=timestamp, signature_v1=signature_v1
        )
        return parse_event(payload)


__all__ = [
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    "SIGNATURE_V1_HEADER",
    "WebhookSignatureError",
    "WebhookTimestampError",
    "WebhookHandler",
    "AsyncWebhookHandler",
    "sign_payload",
    "sign_payload_v1",
    "verify_signature",
]
