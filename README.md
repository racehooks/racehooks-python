# racehooks

Official [RaceHooks](https://racehooks.io) client library for Python.

**Predictive models and analytics for motorsport — race intelligence delivered to your endpoint.** RaceHooks pushes a catalog of event and analytics feeds, many backed by production predictive models, to your webhook (or an SSE stream), and serves historical results from 1950 to present over a REST API. Data covers Formula 1 and other series. Each delivery is signed with HMAC-SHA256 so you can confirm it really came from RaceHooks and wasn't tampered with in transit. This library is a typed REST client, verifies those signatures, and parses deliveries into Pydantic v2 models.

> RaceHooks is an independent service and is not affiliated with or endorsed by Formula One Management or the FIA. "Formula 1," "F1," and related marks are trademarks of Formula One Licensing BV.

## Install

```bash
pip install racehooks
```

Python 3.9 or newer. Runtime dependencies are `pydantic>=2` and `httpx`.

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
)  # base URL defaults to https://api.racehooks.io
```

Create credentials in the [console](https://racehooks.io/console). The client
exchanges them at `POST /v1/oauth` for a Bearer token (valid 12 hours by
default) and refreshes it for you. Plan gating (Free, Developer, Custom) is
enforced by the API: a call above your plan raises `RaceHooksAPIError` with
status 402 or 403.

The fantasy, session-replay and webhook methods return typed Pydantic models.
The data, historical, insights, telemetry, models, lines, analytics, preview,
strategy and usage namespaces return the decoded JSON `data` payload (`dict`
or `list`); field names are listed in the
[OpenAPI spec](https://api.racehooks.io/openapi.json).

### Fantasy

Estimated fantasy-game points and pit-stop leaderboards (paid plan — Developer or
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

### Model outputs and analytics

```python
rh.insights.list_races()                    # races with a completed post-race analytics run
rh.insights.get_race("2026-bahrain-r1")     # per-driver per-lap model outputs (Developer+ for strategic predictions)
rh.insights.get_model_meta()                # what each model predicts, calibration tier, last retrain
rh.models.manifest(); rh.models.scorecard(); rh.models.race_winner_record()

rh.lines.list()                             # model-implied fair odds lines (Custom plan)
rh.lines.get("2026-singapore-r17", checkpoint="q_end", market="winner")
rh.analytics.h2h("1", "33")                 # P(A finishes ahead of B) (Custom plan)
rh.preview.upcoming()                       # next-session preview (detail depends on plan)
rh.strategy.preview_next(); rh.strategy.recap("2026-monaco-r5")
```

### Data, historical and telemetry

```python
rh.data.list_drivers(search="ver", active=True)
rh.data.get_race("2026-bahrain-r1")
rh.data.get_race_telemetry_laps("2026-bahrain-r1", driver_id="max_verstappen", lap=12)
rh.data.get_season_standings(2026)

rh.historical.results(2021, 22)             # 1950 to present
rh.historical.driver_career("lewis_hamilton")
rh.telemetry.get_lap_comparison("2026-bahrain-r1", 20)
rh.indycar.standings()
```

### Account and usage

```python
rh.usage.current()          # deliveries this period
rh.usage.by_feed(); rh.usage.latency(); rh.usage.hourly(); rh.usage.history()
rh.usage.subscription(); rh.usage.billing_plan(); rh.usage.tiers()
```

### Stream without a webhook server (SSE)

```python
for feed, payload in rh.stream(["events.race", "timing.data"]):
    print(feed, payload)
```

Omit the list for every feed your plan allows. Reconnecting is up to you.

### Core resources

```python
rh.feeds.list()                            # feed catalog
rh.feeds.example("events.race")            # most recent delivered payload for a feed
rh.events.list(upcoming=True)              # calendar + sessions
rh.events.list(season=2026, order="desc")
rh.live.context()                          # current drivers / positions / flag / RC

# Webhook subscriptions
res = rh.webhooks.create(
    feed_id="events.race",
    webhook_url="https://yourserver.com/webhook",
    filters={"drivers": ["VER", "NOR"], "constructors": ["ferrari"]},
)
print(res.webhook_secret)                  # shown once — store it to verify signatures

# One endpoint, many feeds ("*" and "analytics.*" globs work); per-feed filters via subscriptions
rh.webhooks.create(webhook_url="https://yourserver.com/webhook", feed_ids=["events.race", "analytics.*"])
rh.webhooks.create(
    webhook_url="https://yourserver.com/webhook",
    subscriptions=[{"feedId": "events.race", "filters": {"drivers": ["VER"]}}],
)

rh.webhooks.list_endpoints()               # grouped: one row per endpoint, with feeds + 7-day stats
rh.webhooks.list()                         # flat: one row per (endpoint, feed)
rh.webhooks.get(webhook_id)                # -> WebhookEndpoint
rh.webhooks.update(webhook_id, active=False)
rh.webhooks.add_feeds(webhook_id, feed_ids=["weather.data"])
rh.webhooks.update_feed(webhook_id, "events.race", filters={"drivers": ["NOR"]})
rh.webhooks.remove_feed(webhook_id, "weather.data")
rh.webhooks.test(webhook_id)
rh.webhooks.logs(webhook_id)
rh.webhooks.deliveries(mode="live")        # recent deliveries across all endpoints + summary
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
            signature_v1=request.headers.get("X-RaceHooks-Signature-V1"),
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
            signature_v1=request.headers.get("X-RaceHooks-Signature-V1"),
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

Every delivery carries two signatures:

- `X-RaceHooks-Signature-V1: t=<sentAtMs>,v1=<hmac of "t.body">` — the send time
  is **inside** the signature, so a tolerance check on it is real replay
  protection.
- `X-RaceHooks-Signature: sha256=<hmac of body>` — the legacy body-only
  signature. `X-RaceHooks-Sent-At` is not covered by it, so a tolerance check on
  that header is only a staleness hint.

Pass the V1 header and set a tolerance:

```python
handler = WebhookHandler(secret="whsec_...", tolerance_seconds=300, require_v1=True)
event = handler.construct_event(
    raw_body,
    request.headers.get("X-RaceHooks-Signature"),
    signature_v1=request.headers.get("X-RaceHooks-Signature-V1"),
)
# raises WebhookTimestampError if the signed send time is older than 5 minutes
```

When no V1 header is supplied the legacy signature is checked (unless
`require_v1=True`), and the tolerance reads `timestamp=` (the
`X-RaceHooks-Sent-At` header). Deliveries are at-least-once: dedupe on the
`X-RaceHooks-Delivery-Id` header.

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
