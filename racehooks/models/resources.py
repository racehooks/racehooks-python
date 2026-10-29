"""Pydantic models for RaceHooks REST resources (``/v1/*`` responses).

These mirror the canonical REST shapes from the published Node SDK
``types.ts``. Wire format is camelCase; every model exposes snake_case
attributes via pydantic aliases and tolerates unknown fields
(``extra="allow"``) so new fields never break parsing.
"""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Resource(BaseModel):
    """Base for REST resource models — tolerant of unknown fields."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class EventSession(_Resource):
    """A single session within an :class:`Event` (practice/qualifying/race)."""

    session_id: Optional[str] = Field(default=None, alias="sessionId")
    type: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = Field(default=None, alias="startDate")
    end_date: Optional[str] = Field(default=None, alias="endDate")
    gmt_offset: Optional[str] = Field(default=None, alias="gmtOffset")
    path: Optional[str] = None


class Event(_Resource):
    """A race-weekend event (``GET /v1/events``)."""

    event_id: Optional[str] = Field(default=None, alias="eventId")
    name: Optional[str] = None
    official_name: Optional[str] = Field(default=None, alias="officialName")
    country_code: Optional[str] = Field(default=None, alias="countryCode")
    country_name: Optional[str] = Field(default=None, alias="countryName")
    location: Optional[str] = None
    circuit_name: Optional[str] = Field(default=None, alias="circuitName")
    state: Optional[str] = None
    type: Optional[str] = None
    round_text: Optional[str] = Field(default=None, alias="roundText")
    sessions: Optional[List[EventSession]] = None


class Feed(_Resource):
    """A feed entry in the RaceHooks feed catalog (``GET /v1/feeds``)."""

    feed_id: Optional[str] = Field(default=None, alias="feedId")
    name: Optional[str] = None
    path: Optional[str] = None
    availability: Optional[str] = None


class WebhookFilters(_Resource):
    """Delivery filters attached to a :class:`Webhook`."""

    drivers: Optional[List[str]] = None
    driver_numbers: Optional[List[str]] = Field(default=None, alias="driverNumbers")
    constructors: Optional[List[str]] = None
    positions: Optional[Any] = None
    event_types: Optional[List[str]] = Field(default=None, alias="eventTypes")


class Webhook(_Resource):
    """A webhook subscription (``GET /v1/webhooks``)."""

    webhook_id: Optional[str] = Field(default=None, alias="webhookId")
    feed_id: Optional[str] = Field(default=None, alias="feedId")
    webhook_url: Optional[str] = Field(default=None, alias="webhookUrl")
    webhook_method: Optional[str] = Field(default=None, alias="webhookMethod")
    active: Optional[bool] = None
    subscription_tier: Optional[str] = Field(default=None, alias="subscriptionTier")
    filters: Optional[WebhookFilters] = None
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")


class WebhookSubscription(_Resource):
    """One feed subscription on a :class:`WebhookEndpoint`."""

    feed_id: Optional[str] = Field(default=None, alias="feedId")
    series_id: Optional[str] = Field(default=None, alias="seriesId")
    filters: Optional[WebhookFilters] = None
    active: Optional[bool] = None
    subscription_tier: Optional[str] = Field(default=None, alias="subscriptionTier")
    consecutive_failures: Optional[int] = Field(default=None, alias="consecutiveFailures")
    auto_disabled_at: Optional[str] = Field(default=None, alias="autoDisabledAt")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")


class WebhookEndpoint(_Resource):
    """A webhook endpoint: one URL + signing secret grouping several feeds."""

    webhook_id: Optional[str] = Field(default=None, alias="webhookId")
    webhook_url: Optional[str] = Field(default=None, alias="webhookUrl")
    webhook_method: Optional[str] = Field(default=None, alias="webhookMethod")
    series_id: Optional[str] = Field(default=None, alias="seriesId")
    active: Optional[bool] = None
    subscription_tier: Optional[str] = Field(default=None, alias="subscriptionTier")
    feed_count: Optional[int] = Field(default=None, alias="feedCount")
    subscriptions: List[WebhookSubscription] = Field(default_factory=list)
    stats: Optional[Any] = None
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")


class Simulation(_Resource):
    """Deprecated: the retired per-request replay run.

    Use ``rh.simulate`` (sessions / prepare / status) instead.
    """

    simulation_id: Optional[str] = Field(default=None, alias="simulationId")
    client_id: Optional[str] = Field(default=None, alias="clientId")
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    session_name: Optional[str] = Field(default=None, alias="sessionName")
    session_path: Optional[str] = Field(default=None, alias="sessionPath")
    status: Optional[str] = None
    speed: Optional[str] = None
    feeds_requested: Optional[str] = Field(default=None, alias="feedsRequested")
    events_dispatched: Optional[int] = Field(default=None, alias="eventsDispatched")
    delivery_count: Optional[int] = Field(default=None, alias="deliveryCount")
    error_count: Optional[int] = Field(default=None, alias="errorCount")
    log_entries: Optional[str] = Field(default=None, alias="logEntries")
    started_at: Optional[str] = Field(default=None, alias="startedAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")


class SubscriptionData(_Resource):
    """Subscription tier, limits and usage (``GET /v1/subscription``)."""

    tier: Optional[str] = None
    active: Optional[bool] = None
    limits: Optional[Any] = None
    usage: Optional[Any] = None
    upgrade: Optional[Any] = None


class LiveDriverRow(_Resource):
    """A single driver row in the :class:`LiveContext` live-session snapshot."""

    pos: Optional[int] = None
    num: Optional[str] = None
    tla: Optional[str] = None
    name: Optional[str] = None
    team: Optional[str] = None
    gap: Optional[str] = None
    interval: Optional[str] = None
    last_lap: Optional[str] = Field(default=None, alias="lastLap")
    s1: Optional[str] = None
    s2: Optional[str] = None
    s3: Optional[str] = None
    compound: Optional[str] = None
    tyre_age: Optional[int] = Field(default=None, alias="tyreAge")
    pits: Optional[int] = None
    status: Optional[str] = None


class LiveContext(_Resource):
    """The current live-session context snapshot (``GET /v1/live/context``)."""

    active: Optional[bool] = None
    session_name: Optional[str] = Field(default=None, alias="sessionName")
    session_type: Optional[str] = Field(default=None, alias="sessionType")
    current_lap: Optional[int] = Field(default=None, alias="currentLap")
    total_laps: Optional[int] = Field(default=None, alias="totalLaps")
    flag: Optional[str] = None
    drivers: Optional[List[LiveDriverRow]] = None
    rc_messages: Optional[List[Any]] = Field(default=None, alias="rcMessages")
    updated_at: Optional[int] = Field(default=None, alias="updatedAt")


class DeliveryLog(_Resource):
    """A single webhook delivery-attempt log entry (``GET /v1/webhooks/:id/logs``)."""

    log_id: Optional[str] = Field(default=None, alias="logId")
    webhook_id: Optional[str] = Field(default=None, alias="webhookId")
    status_code: Optional[int] = Field(default=None, alias="statusCode")
    retry_count: Optional[int] = Field(default=None, alias="retryCount")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    payload: Optional[str] = None
    mode: Optional[str] = None
    feed_id: Optional[str] = Field(default=None, alias="feedId")
    dead: Optional[bool] = None
    duration_ms: Optional[int] = Field(default=None, alias="durationMs")
    created_at: Optional[str] = Field(default=None, alias="createdAt")


class CreateWebhookResult(_Resource):
    """Envelope returned on successful webhook creation (``POST /v1/webhooks``).

    ``webhook_secret`` is returned **only once** at creation — store it
    immediately to verify signatures. It can later be retrieved via
    :meth:`WebhooksNamespace.get_secret` or rotated with
    :meth:`WebhooksNamespace.rotate_secret`.
    """

    webhook: Optional[Webhook] = None
    # Set instead of ``webhook`` when created with feed_ids / subscriptions.
    webhook_id: Optional[str] = Field(default=None, alias="webhookId")
    webhook_url: Optional[str] = Field(default=None, alias="webhookUrl")
    webhook_method: Optional[str] = Field(default=None, alias="webhookMethod")
    subscriptions: Optional[List[WebhookSubscription]] = None
    webhook_secret: Optional[str] = Field(default=None, alias="webhookSecret")
    tier: Optional[str] = None


class WebhookTestResult(_Resource):
    """Result of firing a test delivery (``POST /v1/webhooks/:id/test``)."""

    delivered: Optional[bool] = None
    status_code: Optional[int] = Field(default=None, alias="statusCode")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")


class WebhookList(_Resource):
    """Paginated webhook list (``GET /v1/webhooks``)."""

    webhooks: List[Webhook] = Field(default_factory=list)
    total: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class WebhookEndpointList(_Resource):
    """Paginated grouped endpoint list (``GET /v1/webhooks``)."""

    endpoints: List[WebhookEndpoint] = Field(default_factory=list)
    total: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class WebhookLogList(_Resource):
    """Paginated delivery-log list (``GET /v1/webhooks/:id/logs``)."""

    logs: List[DeliveryLog] = Field(default_factory=list)
    total: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class FeedList(_Resource):
    """Paginated feed catalog (``GET /v1/feeds``)."""

    feeds: List[Feed] = Field(default_factory=list)
    total: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class EventList(_Resource):
    """Event calendar response (``GET /v1/events``)."""

    events: List[Event] = Field(default_factory=list)
    total: Optional[int] = None


__all__ = [
    "Event",
    "EventSession",
    "EventList",
    "Feed",
    "FeedList",
    "WebhookFilters",
    "Webhook",
    "WebhookList",
    "CreateWebhookResult",
    "WebhookTestResult",
    "DeliveryLog",
    "WebhookLogList",
    "Simulation",
    "SubscriptionData",
    "LiveDriverRow",
    "LiveContext",
]
