"""racehooks — official RaceHooks client library for Python.

Verify F1 live-timing webhooks signed by RaceHooks and work with typed
event models.

    from racehooks import WebhookHandler

    handler = WebhookHandler(secret="whsec_...")
    event = handler.construct_event(raw_body, signature_header)
    if event.feed == "raceevent":
        print(event.event, event.data)
"""

from .models import (
    AnyEvent,
    CurrentTyres,
    DriverEntry,
    DriverList,
    LapCount,
    RaceControlMessages,
    RaceEvent,
    RaceSummaryEvent,
    SessionStatus,
    SessionTimingEvent,
    TimingData,
    TrackStatus,
    WeatherData,
    WebhookEvent,
    parse_event,
)
from .webhook import (
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    AsyncWebhookHandler,
    WebhookHandler,
    WebhookSignatureError,
    WebhookTimestampError,
    sign_payload,
    verify_signature,
)

__version__ = "0.2.0"

__all__ = [
    "__version__",
    # webhook
    "WebhookHandler",
    "AsyncWebhookHandler",
    "verify_signature",
    "sign_payload",
    "WebhookSignatureError",
    "WebhookTimestampError",
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    # events
    "parse_event",
    "WebhookEvent",
    "RaceEvent",
    "SessionTimingEvent",
    "RaceSummaryEvent",
    "AnyEvent",
    # feed models
    "WeatherData",
    "TrackStatus",
    "SessionStatus",
    "LapCount",
    "DriverEntry",
    "DriverList",
    "TimingData",
    "CurrentTyres",
    "RaceControlMessages",
]
