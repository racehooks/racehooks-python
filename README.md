# racehooks

Official [RaceHooks](https://racehooks.io) client library for Python — verify webhooks and work with typed payloads from the motorsports analytics platform.

RaceHooks delivers 50+ live F1 feeds — timing, race events, and 18 derived analytics feeds backed by twelve production ML models — to your webhook endpoint. Each delivery is signed with HMAC-SHA256 so you can confirm it really came from RaceHooks and wasn't tampered with in transit. This library verifies those signatures and parses deliveries into Pydantic v2 models.

> RaceHooks is an independent service and is not affiliated with or endorsed by Formula One Management or the FIA. "Formula 1," "F1," and related marks are trademarks of Formula One Licensing BV.

## Install

```bash
pip install racehooks
```

Python 3.9+. The only runtime dependency is `pydantic>=2`.

## Quick start

```python
from racehooks import WebhookHandler

handler = WebhookHandler(secret="whsec_...")
```

Your webhook secret is shown when you create a webhook (`POST /v1/webhooks`) and is retrievable any time via `GET /v1/webhooks/:id/secret`.

### Flask

The signature is computed over the **raw request body**, so verify against
`request.get_data()` (the unparsed bytes), not a parsed JSON object:

```python
from flask import Flask, request
from racehooks import WebhookHandler, WebhookSignatureError

app = Flask(__name__)
handler = WebhookHandler(secret="whsec_...")

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

    if event.feed == "raceevent":
        print(event.event, "on lap", event.lap, event.data)
    elif event.feed == "weatherdata":
        print("air temp", event.data["AirTemp"])

    return {"received": True}, 200
```

### FastAPI (async)

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from racehooks import AsyncWebhookHandler, WebhookSignatureError

app = FastAPI()
handler = AsyncWebhookHandler(secret="whsec_...")

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
```

### Manual verification

```python
from racehooks import verify_signature, WebhookSignatureError

try:
    verify_signature(raw_body, signature_header, secret="whsec_...")
except WebhookSignatureError:
    ...  # reject
```

`verify_signature` returns `True` on success and raises `WebhookSignatureError`
otherwise. Parse separately with `parse_event(raw_body)` if you only need the
typed model.

### Replay protection (optional)

Every delivery carries an `X-RaceHooks-Sent-At` header (epoch milliseconds).
Reject stale deliveries by setting a tolerance:

```python
handler = WebhookHandler(secret="whsec_...", tolerance_seconds=300)
# raises WebhookTimestampError if the delivery is older than 5 minutes
```

Pass the timestamp header through to `construct_event` / `verify_signature`
(`timestamp=...`) for the check to run.

## Event models

`construct_event` / `parse_event` return the most specific model for the feed:

| `event.feed` | model | extra envelope fields |
|---|---|---|
| `raceevent` | `RaceEvent` | `event`, `lap`, `utc` |
| `sessiontiming` | `SessionTimingEvent` | `utc`, `lap`, `total_laps`, `track_status` |
| `racesummary` | `RaceSummaryEvent` | — |
| `analytics.*` (12 feeds) | `AnalyticsStrategy`, `AnalyticsRaceOdds`, `AnalyticsGapProjection`, `AnalyticsTireStrategy`, `AnalyticsConstructor`, `AnalyticsChampionshipProbability`, `AnalyticsQualifying`, `AnalyticsSectorPace`, `AnalyticsBattle`, `AnalyticsPitWindow`, `AnalyticsTrackConditions`, `AnalyticsPitQuality` | per-feed (see `racehooks.models.feeds`) |
| `weather.*` (6 feeds) | `WeatherRainEvent` (onset + cleared), `WeatherForecastUpdate`, `WeatherTyreMismatch`, `WeatherStrategyDivergence`, `WeatherCompoundCrossoverAlert` | per-feed |
| anything else | `WebhookEvent` | — |

The 18 derived analytics feeds (12 `analytics.*` + 6 `weather.*`) are delivered on the
Analytics tier and backed by twelve production ML models. Import their models from
`racehooks.models.feeds`.

All envelopes expose `feed`, `session_id`, and `data`. Feed data models
(`WeatherData`, `TrackStatus`, `LapCount`, `DriverEntry`, …) are available for
validating the `data` payload and tolerate unknown fields for forward
compatibility:

```python
from racehooks import WeatherData

weather = WeatherData.model_validate(event.data)
print(weather.air_temp, weather.track_temp)
```

## How verification works

The signature mirrors the RaceHooks server exactly:

```
X-RaceHooks-Signature: sha256=HMAC_SHA256(webhook_secret, raw_body)
```

Comparison uses `hmac.compare_digest` (constant time). Always verify against
the **raw body bytes** — re-serializing a parsed body can change whitespace or
key order and break the signature.

## License

MIT
