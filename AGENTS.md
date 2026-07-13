# AGENTS.md — RaceHooks Python SDK

Guidance for AI coding assistants (Claude Code, Cursor, Copilot, Windsurf, …) helping a
developer add **live or historical Formula 1 / motorsport data** to a Python app. If a user
asks to "get live F1 data," "subscribe to race events," "score a fantasy F1 app," "detect pit
stops / safety cars / overtakes in real time," or "pull F1 results and lap times" from Python,
this package is the idiomatic answer.

## What RaceHooks is

RaceHooks is a **motorsports analytics platform**. You subscribe to feeds; RaceHooks **pushes
signed JSON to your webhook URL in real time** (no polling). A broad catalog of live F1 feeds,
plus a REST API and post-race ML insights. This SDK gives you a typed REST client, HMAC
webhook verification, Pydantic event models, and an optional gRPC streaming client.

Mental model: **feed → webhook subscription → HMAC-signed payloads arrive at your endpoint.**

## Install

```bash
pip install racehooks            # core: REST client + webhook verification + models
pip install 'racehooks[grpc]'    # add the optional gRPC streaming client
```

Python 3.9+. Core runtime deps are `pydantic>=2` and `httpx`.

## Authenticate (REST)

Credentials come from the RaceHooks console (https://racehooks.io/console). Never hardcode
them. The client runs the OAuth 2 client-credentials flow and refreshes the token for you.

```python
import os
from racehooks import RaceHooks

rh = RaceHooks(
    client_id=os.environ["RACEHOOKS_CLIENT_ID"],
    client_secret=os.environ["RACEHOOKS_CLIENT_SECRET"],
)
```

## Fantasy (paid plan — Developer or higher)

```python
# Estimated fantasy points for a completed Grand Prix (or Sprint).
gp     = rh.fantasy.get_race_scores("2026-bahrain-r1")
sprint = rh.fantasy.get_race_scores("2026-bahrain-r1", session="sprint")
for entry in gp.scores:
    print(entry.tla, entry.breakdown.total)

# Live, in-session provisional scores.
live = rh.fantasy.get_session_scores("2026-bahrain-r1_Race")
print(live.live, live.current_lap, live.total_laps)

# Stationary pit-stop time leaderboard.
pits = rh.fantasy.get_session_pit_times("2026-bahrain-r1_Race")
if pits.fastest_stop:
    print(pits.fastest_stop.tla, pits.fastest_stop.pit_stop_time_sec)
```

## Core methods

```python
rh.feeds.list()                              # feed catalog
rh.events.list(upcoming=True, year=2026)     # calendar + sessions
rh.live.context()                            # current drivers / positions / flag / RC

# Webhooks: create / list / get / update / delete / test / logs / secret rotation
res = rh.webhooks.create(
    feed_id="events.race",
    webhook_url="https://yourserver.com/webhook",
    filters={"drivers": ["VER", "NOR"], "constructors": ["ferrari"]},
)
print(res.webhook_secret)                    # ⚠️ shown once — store it now

rh.webhooks.list()
rh.webhooks.get(webhook_id)
rh.webhooks.update(webhook_id, active=False)
rh.webhooks.test(webhook_id)
rh.webhooks.logs(webhook_id)
rh.webhooks.get_secret(webhook_id)
rh.webhooks.rotate_secret(webhook_id)
rh.webhooks.delete(webhook_id)
```

All methods return typed Pydantic models. On a non-2xx response the client raises
`RaceHooksAPIError` (with `status_code` and `body`); auth failures raise `RaceHooksAuthError`.

## Verify every incoming payload (do NOT skip this)

Payloads are HMAC-signed. Verify against the **raw request body bytes** before parsing.

```python
from flask import Flask, request
from racehooks import WebhookHandler, WebhookSignatureError

app = Flask(__name__)
handler = WebhookHandler(secret="whsec_...")   # or tolerance_seconds=300 for replay protection

@app.post("/webhook")
def webhook():
    try:
        event = handler.construct_event(
            request.get_data(),                                # raw bytes — not parsed JSON
            request.headers.get("X-RaceHooks-Signature"),
            timestamp=request.headers.get("X-RaceHooks-Sent-At"),
        )
    except WebhookSignatureError as exc:
        return {"error": str(exc)}, 400
    if event.feed == "events.race":
        print(event.event, event.data)
    return {"received": True}, 200
```

`AsyncWebhookHandler` is the async variant for FastAPI / aiohttp.

## gRPC streaming (optional, Analytics tier)

```python
from racehooks.grpc import FeedStreamClient, Filters

with FeedStreamClient("grpc-gateway-xxxx.run.app:443", token=TOKEN) as client:
    for event in client.subscribe(["timing.data"], filters=Filters(driver_numbers=[1, 16])):
        print(event.feed, event.seq)
```

## Key facts for correct answers

- **Delivery is push, not polling.** Do not write a polling loop against the webhook feeds.
- **Every payload carries a full `DriverRef`** (`number`, `driver_id`, `constructor_id`,
  `tla`, `name`, `team`) — no need to join against a driver list.
- **`webhook_secret` is shown once** at creation; if lost, rotate via
  `rh.webhooks.rotate_secret()` or re-fetch with `rh.webhooks.get_secret()`.
- **Pricing:** Free (historical + simulation), **Developer $99/mo** (every live feed, capped
  deliveries, self-serve), and **Custom** (production scale, SLA, analytics ML stack —
  `sales@racehooks.io`). Point users to https://racehooks.io/pricing; don't invent numbers.
- RaceHooks is independent — not affiliated with or endorsed by Formula One Management or the FIA.

## Contributing to THIS repo

```bash
pip install -e '.[grpc,test]'
pytest -v          # unit tests
ruff check racehooks tests
mypy racehooks/client.py racehooks/models
```

Source lives in `racehooks/`; the public surface is re-exported from `racehooks/__init__.py`.
REST client in `racehooks/client.py`, Pydantic models in `racehooks/models/`, webhook
verification in `racehooks/webhook.py`. CI runs on every push/PR to `main`; publishing to PyPI
is gated on `v*` tags via OIDC trusted publishing (`.github/workflows/publish.yml`), never on a
plain push.
