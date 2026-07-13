"""racehooks — official RaceHooks client library for Python.

Call the RaceHooks REST API (fantasy scores, feeds, events, webhooks, live
context), verify F1 live-timing webhooks signed by RaceHooks, and work with
typed event models.

    from racehooks import RaceHooks, WebhookHandler

    # REST client
    rh = RaceHooks(client_id="...", client_secret="...")
    scores = rh.fantasy.get_race_scores("2026-bahrain-r1")

    # Webhook verification
    handler = WebhookHandler(secret="whsec_...")
    event = handler.construct_event(raw_body, signature_header)
    if event.feed == "events.race":
        print(event.event, event.data)
"""

from .client import (
    DEFAULT_BASE_URL,
    RaceHooks,
    RaceHooksAPIError,
    RaceHooksAuthError,
    RaceHooksError,
)
from .models import (
    AnalyticsBattle,
    AnalyticsChampionshipProbability,
    AnalyticsGapProjection,
    AnalyticsPitQuality,
    AnalyticsPitWindow,
    AnalyticsQualifying,
    AnalyticsRaceDuration,
    AnalyticsRaceOdds,
    AnalyticsRacePreview,
    AnalyticsSectorPace,
    AnalyticsStrategy,
    AnalyticsTeamPoints,
    AnalyticsTireStrategy,
    AnalyticsTrackConditions,
    AnalyticsTruePace,
    AnalyticsWinningMargin,
    AnyEvent,
    CreateWebhookResult,
    CurrentTyres,
    DeliveryLog,
    DriverEntry,
    DriverList,
    DriverRef,
    Event,
    EventList,
    EventSession,
    FantasyScoreBreakdown,
    FantasyScoreEntry,
    Feed,
    FeedList,
    LapCount,
    LiveContext,
    LiveDriverRow,
    PitTimeStop,
    QualifyingEvent,
    RaceControlMessages,
    RaceEvent,
    RaceScores,
    RaceSummaryEvent,
    ReplayMeta,
    SessionPitTimes,
    SessionScores,
    SessionStatus,
    SessionTimingEvent,
    Simulation,
    SubscriptionData,
    TimingData,
    TrackStatus,
    WeatherCompoundCrossover,
    WeatherData,
    WeatherForecastUpdate,
    WeatherRainEvent,
    WeatherStrategyDivergence,
    WeatherTireMismatch,
    Webhook,
    WebhookEvent,
    WebhookFilters,
    WebhookList,
    WebhookLogList,
    WebhookTestResult,
    WinningMarginLeadBattle,
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

__version__ = "0.5.0"

__all__ = [
    "__version__",
    # REST client
    "RaceHooks",
    "RaceHooksError",
    "RaceHooksAuthError",
    "RaceHooksAPIError",
    "DEFAULT_BASE_URL",
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
    "QualifyingEvent",
    "SessionTimingEvent",
    "RaceSummaryEvent",
    "AnyEvent",
    # shared
    "DriverRef",
    "ReplayMeta",
    # raw feed data models
    "WeatherData",
    "TrackStatus",
    "SessionStatus",
    "LapCount",
    "DriverEntry",
    "DriverList",
    "TimingData",
    "CurrentTyres",
    "RaceControlMessages",
    # analytics feed models
    "AnalyticsStrategy",
    "AnalyticsRaceOdds",
    "AnalyticsTruePace",
    "AnalyticsGapProjection",
    "AnalyticsWinningMargin",
    "AnalyticsRaceDuration",
    "AnalyticsRacePreview",
    "AnalyticsTireStrategy",
    "AnalyticsTeamPoints",
    "AnalyticsChampionshipProbability",
    "AnalyticsQualifying",
    "AnalyticsSectorPace",
    "AnalyticsBattle",
    "AnalyticsPitWindow",
    "AnalyticsTrackConditions",
    "AnalyticsPitQuality",
    "WinningMarginLeadBattle",
    # weather feed models
    "WeatherRainEvent",
    "WeatherForecastUpdate",
    "WeatherTireMismatch",
    "WeatherStrategyDivergence",
    "WeatherCompoundCrossover",
    # REST resources
    "Event",
    "EventList",
    "EventSession",
    "Feed",
    "FeedList",
    "Webhook",
    "WebhookFilters",
    "WebhookList",
    "CreateWebhookResult",
    "WebhookTestResult",
    "DeliveryLog",
    "WebhookLogList",
    "Simulation",
    "SubscriptionData",
    "LiveContext",
    "LiveDriverRow",
    # fantasy
    "PitTimeStop",
    "SessionPitTimes",
    "FantasyScoreBreakdown",
    "FantasyScoreEntry",
    "RaceScores",
    "SessionScores",
]
