# CHANGELOG

<!-- version list -->

## v0.7.0 (2026-10-29)

### Features

- Bring SDK current with the live API ([#3](https://github.com/racehooks/racehooks-python/pull/3),
  [`bd4b34c`](https://github.com/racehooks/racehooks-python/commit/bd4b34c7de1a369d27f6e770b5aeb498c372732b))

Fix webhooks.get/update (API returns data.endpoint, not data.webhook) and webhooks.list (now sends
  shape=flat). Add multi-feed webhook endpoints (feed_ids, subscriptions, add_feeds, update_feed,
  remove_feed, list_endpoints, deliveries), X-RaceHooks-Signature-V1 verification with
  signed-timestamp replay protection, SSE stream(), feeds.example, fantasy.get_prices, events
  season/order, and data, historical, indycar, insights, telemetry, models, lines, analytics,
  preview, strategy and usage namespaces. Update description, keywords and docs to the approved
  positioning.


## v0.6.1 (2026-10-29)

### Bug Fixes

- First PyPI publish via trusted publishing
  ([`f58634b`](https://github.com/racehooks/racehooks-python/commit/f58634bb4c0e3efb3f9480cbef4ed43abc330271))


## v0.6.0 (2026-10-21)

### Continuous Integration

- Automate PyPI publishing via python-semantic-release + Trusted Publishing
  ([`a00094a`](https://github.com/racehooks/racehooks-python/commit/a00094afde4fbebd0885b1f24c8d464cd22e2f30))

Every push to main now runs python-semantic-release: it reads conventional-commit messages, bumps
  [project].version, commits it back, tags, builds sdist+wheel, and cuts a GitHub release. The dist
  is published to PyPI via Trusted Publishing (OIDC, id-token: write) with no API token. Commits
  with no releasable changes publish nothing.

### Documentation

- Link to racehooks.io docs; fix repository/bugs URLs
  ([`1c6b01a`](https://github.com/racehooks/racehooks-python/commit/1c6b01aeaeea1d0a53451d9373e7504e97abad1b))

### Features

- **simulate**: Session-replay endpoints
  ([`19863e0`](https://github.com/racehooks/racehooks-python/commit/19863e05a0d7249763dd536e26153aebbfa1649f))


## v0.5.0 (2026-07-13)

### Bug Fixes

- Code review corrections
  ([`771815d`](https://github.com/racehooks/racehooks-python/commit/771815df939d74553e566e1a17c51b77096659ae))

- webhook.py: replace ambiguous truthiness guard (`if tolerance_seconds and …`) with explicit `is
  not None and > 0`; clarify docstring to state that None/0 disable replay protection - events.py:
  add `bytearray` to `parse_event` type annotation to match the existing isinstance check
  (annotation and implementation were inconsistent) - events.py: remove redundant `model_config`
  re-declarations from RaceEvent, SessionTimingEvent, and RaceSummaryEvent — Pydantic v2 merges
  config from the parent, so the identical ConfigDict on each subclass was dead code

- **sdk**: Rename type→feed throughout, fix domain, add trademark disclaimer
  ([`a9173c2`](https://github.com/racehooks/racehooks-python/commit/a9173c2ae88adbb36a36d14c92784011b3560360))

Renames the `type` envelope field to `feed` across all source, tests, and docs to match the server
  payload shape. Fixes `racehooks-ai.com` → `racehooks.io` in README and pyproject.toml. Adds the
  required trademark disclaimer below the opening description paragraph in the README.

### Documentation

- Remove raw F1 SignalR feed reference from models docstring
  ([`2af914f`](https://github.com/racehooks/racehooks-python/commit/2af914f5decc4a8acf7e49c3b90bda88c012ffe0))

Replace "These mirror the raw F1 SignalR feed shapes" with neutral RaceHooks webhook payload
  framing. Remove cross-reference to @racehooks/f1-telemetry-schema (not published). The models
  describe what RaceHooks delivers, not how it is sourced.

### Features

- Add REST client with fantasy + core endpoints
  ([`0e34eb1`](https://github.com/racehooks/racehooks-python/commit/0e34eb17698cea4e351c8f4437d737948c6cfc46))

Add a synchronous REST client (RaceHooks) at parity with the Go/Ruby SDKs: OAuth 2
  client-credentials with automatic token refresh, a typed request helper with 401-refresh retry and
  typed errors, and namespaces for fantasy
  (get_race_scores/get_session_scores/get_session_pit_times), webhooks
  (create/list/get/update/delete/test/logs/get_secret/rotate_secret), feeds, events, and live
  context.

Add Pydantic models for the fantasy responses (RaceScores, SessionScores, SessionPitTimes with
  pit_stop_time_sec aliased to pitStopTimeSec, plus score breakdown) and REST list/create/log/test
  envelopes. Depend on httpx, export the client and new models, and add PyPI trusted-publishing
  (OIDC) workflow, AGENTS.md, and a README REST + fantasy quickstart.

Also ships the in-progress derived-feed and gRPC client work.

- Type all 18 derived analytics feeds + analytics-first README
  ([`a29252f`](https://github.com/racehooks/racehooks-python/commit/a29252f37ce054336993b10cb0fe3b35e578d30d))

Mirrors the Node SDK's feed coverage. Adds Pydantic v2 models for the 11 previously-untyped derived
  feeds and registers them with parse_event:

- analytics.sector-pace, .battle, .pit-window, .track-conditions, .pit-quality -
  weather.rain_onset/.rain_cleared (shared model), .forecast_update, .tyre_mismatch,
  .strategy_divergence, .compound_crossover_alert

Flat weather feeds type their top-level fields with correct wire-key aliases (camelCase for
  forecast/tyre_mismatch, snake_case direct for crossover); the forecast `model` field uses
  protected_namespaces=() to avoid the pydantic clash.

README leads with the motorsports analytics platform (50+ live feeds, twelve production ML models)
  and documents all 18 derived feed models. 31 tests pass. Bump 0.1.0 → 0.2.0.

- **models**: Add typed models for all 7 analytics feeds
  ([`011ea4a`](https://github.com/racehooks/racehooks-python/commit/011ea4a2011aa02992d46669a680e307c7754e18))

Analytics feeds are now standalone deliveries, not enrichment on timingdata. Adds Pydantic models
  for analytics.strategy, analytics.race-odds, analytics.gap-projection, analytics.tire-strategy,
  analytics.constructor, analytics.championship-probability, and analytics.qualifying. All 7 are
  registered in _EVENT_MODELS so parse_event returns a typed instance.
