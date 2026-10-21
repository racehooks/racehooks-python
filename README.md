# racehooks

Official [RaceHooks](https://racehooks.io) client library for Python — verify webhooks and work with typed payloads from the motorsports analytics platform.

RaceHooks delivers a broad catalog of live F1 feeds — timing, race events, and a suite of derived analytics feeds backed by production ML models — to your webhook endpoint. Each delivery is signed with HMAC-SHA256 so you can confirm it really came from RaceHooks and wasn't tampered with in transit. This library verifies those signatures and parses deliveries into Pydantic v2 models.

> RaceHooks is an independent service and is not affiliated with or endorsed by Formula One Management or the FIA. "Formula 1," "F1," and related marks are trademarks of Formula One Licensing BV.

## Install

```bash
pip install racehooks
```

Python 3.9+. Runtime dependencies are `pydantic>=2` and `httpx`.

## REST API client

`RaceHooks` is a typed client for the REST API. It runs the OAuth 2
client-credentials flow for you — pass your console credentials and it fetches
and refreshes the Bearer token automatically. Every method returns a Pydantic
model; a non-2xx response raises `RaceHooksAPIError` (with `status_code` and
`body`), and an auth failure raises `RaceHooksAuthError`.

```python
import os
from racehooks import RaceHooks

rh = RaceHooks(
    client_id=os.environ["RACEHOOKS_CLIENT_ID"],
    client_secret=os.environ["RACEHOOKS_CLIENT_SECRET"],
)
```

### Fantasy

Estimated F1 Fantasy points and pit-stop leaderboards (paid plan — Developer or
higher):

```python
# Completed Grand Prix (default) or Sprint.
gp     = rh.fantasy.get_race_scores("2026-bahrain-r1")
sprint = rh.fantasy.get_race_scores("2026-bahrain-r1", session="sprint")
for entry in gp.scores:
    print(entry.tla, entry.team, entry.breakdown.total)

# Live, in-session provisional scores (empty with live=False when nothing is on track).
live = rh.fantasy.get_session_scores("2026-bahrain-r1_Race")
print(live.live, live.current_lap, "/", live.total_laps)

# Stationary pit-stop time leaderboard.
pits = rh.fantasy.get_session_pit_times("2026-bahrain-r1_Race")
if pits.fastest_stop:
    print(pits.fastest_stop.tla, pits.fastest_stop.pit_stop_time_sec, "s")
```

### Session replay

Replay a completed session as if it were live. List replayable sessions, warm
the recorded-playback artifact, then stream it from the simulate-stream service:

```python
rh.simulate.sessions(year=2026, type="race")   # replayable sessions (+ total, restricted_to_season)
rh.simulate.demo()                             # the curated demo session
art = rh.simulate.prepare("2026-great-britain_r")  # generate the artifact if cold
rh.simulate.status("2026-great-britain_r")     # status: ready | preparing | missing | unknown
rh.simulate.quota()                            # your tier's replay slots (-1 = unlimited)
```

### Core resources

```python
rh.feeds.list()                            # feed catalog
rh.events.list(upcoming=True, year=2026)   # calendar + sessions
rh.live.context()                          # current drivers / positions / flag / RC

# Webhook subscriptions
res = rh.webhooks.create(
    feed_id="events.race",
    webhook_url="https://yourserver.com/webhook",
    filters={"drivers": ["VER", "NOR"], "constructors": ["ferrari"]},
)
print(res.webhook_secret)                  # shown once — store it to verify signatures

rh.webhooks.list()
rh.webhooks.get(webhook_id)
rh.webhooks.update(webhook_id, active=False)
rh.webhooks.test(webhook_id)
rh.webhooks.logs(webhook_id)
rh.webhooks.get_secret(webhook_id)
rh.webhooks.rotate_secret(webhook_id)
rh.webhooks.delete(webhook_id)
```

## Quick start (webhook verification)

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

    if event.feed == "events.race":
        print(event.event, "on lap", event.lap, event.data)
    elif event.feed == "weather.data":
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

`construct_event` / `parse_event` return the most specific model for the feed.
The `feed` discriminator is the canonical, hyphenated feed id:

| `event.feed` | model | extra envelope fields |
|---|---|---|
| `events.race` | `RaceEvent` | `event`, `lap`, `utc` |
| `events.qualifying` | `QualifyingEvent` | `event`, `lap`, `utc` |
| `session.timing` | `SessionTimingEvent` | `utc`, `lap`, `total_laps`, `track_status` |
| `results.race-summary` | `RaceSummaryEvent` | `type`, `race_id`, telemetry summary fields |
| `analytics.*` | `AnalyticsStrategy`, `AnalyticsRaceOdds`, `AnalyticsTruePace`, `AnalyticsGapProjection`, `AnalyticsWinningMargin`, `AnalyticsRaceDuration`, `AnalyticsRacePreview`, `AnalyticsTireStrategy`, `AnalyticsTeamPoints`, `AnalyticsChampionshipProbability`, `AnalyticsQualifying`, `AnalyticsSectorPace`, `AnalyticsBattle`, `AnalyticsPitWindow`, `AnalyticsTrackConditions`, `AnalyticsPitQuality` | per-feed (see `racehooks.models.feeds`) |
| `weather.*` | `WeatherRainEvent` (rain-onset + rain-cleared), `WeatherForecastUpdate`, `WeatherTireMismatch`, `WeatherStrategyDivergence`, `WeatherCompoundCrossover` | per-feed |
| anything else | `WebhookEvent` | — |

The derived `analytics.*` and `weather.*` feeds are delivered on the Analytics
tier and backed by production ML models; import their models from
`racehooks.models.feeds`. Each analytics envelope mirrors its server payload
exactly — most per-lap feeds carry a `session_id`, a separate nullable
`race_id`, and `lap`, while some carry a bespoke envelope (e.g.
`analytics.qualifying` has `session_id` + `race_id` + `segment` but no `lap`;
`analytics.championship-probability` is season-scoped with `season_year` +
`after_race_id`; the per-driver alert feeds carry `session_id` + `lap` with no
`race_id`). Driver entries in every normalized payload are full `DriverRef`
identity blocks (`driver_id`, `constructor_id`, `number`, `tla`, `name`,
`team`).

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

## gRPC streaming (optional)

For low-latency delivery over a single multiplexed socket, install the optional
gRPC client — it carries `grpcio`, so it's opt-in and the core install stays
light. Best for high-throughput / latency-sensitive back ends; requires the
**Analytics** tier.

```bash
pip install 'racehooks[grpc]'
```

```python
from racehooks.grpc import FeedStreamClient, Filters

with FeedStreamClient("grpc-gateway-xxxx.run.app:443", token=TOKEN) as client:
    stream = client.subscribe(
        ["timing.data", "race-control.messages"],
        filters=Filters(driver_numbers=[1, 16]),
    )
    for event in stream:
        print(event.feed, event.seq, event.json())
```

Iterate a subscription to receive events. **Reconnects are handled for you and
are lossless on a live instance:** the server closes long streams with a
reconnect hint (~55 min), transient drops retry with exponential backoff, and
both resume from the last sequence so the gateway replays the gap and duplicates
are dropped by `seq`. The stream is best-effort; webhooks remain the durable
path. Pass `reconnect=False` to surface terminal errors instead; call
`stream.close()` (or use it as a context manager) to stop.

`subscribe(...)` returns lazily and iteration **blocks**, so run it in a thread
(or an executor) if your app has other work to do.

## Documentation

Full docs: https://racehooks.io/docs/sdk

## License

MIT
