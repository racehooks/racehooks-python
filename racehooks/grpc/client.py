"""Synchronous RaceHooks gRPC streaming client.

Delivers F1 feed messages over a gRPC server-stream with automatic, lossless
reconnect. Iterate a subscription to receive events::

    from racehooks.grpc import FeedStreamClient

    with FeedStreamClient("grpc-gateway-xxxx.run.app:443", token=TOKEN) as client:
        for event in client.subscribe(["timingdata", "racecontrol"]):
            print(event.feed, event.seq, event.json())

Reconnects are handled for you: the server closes long streams with a reconnect
hint (~55 min Cloud Run cap), and transient drops retry with exponential backoff.
Both resume from the last seen sequence, so the gateway replays the gap and
duplicates are dropped by ``seq`` — no messages are lost across a reconnect on a
live instance. The stream is best-effort; webhooks remain the durable path.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from typing import Any, Iterator, List, Optional, Sequence, cast
from urllib.parse import urlparse

import grpc

from ._gen.racehooks.v1 import feed_pb2, feed_pb2_grpc

__all__ = ["FeedStreamClient", "FeedStream", "FeedEvent", "Filters"]

_CONTROL_CONNECTED = "_connected"
_CONTROL_RECONNECT = "_reconnect"
_INITIAL_BACKOFF = 1.0
_DEFAULT_MAX_BACKOFF = 30.0


@dataclass(frozen=True)
class Filters:
    """Optional per-subscription delivery filters (same semantics as webhooks)."""

    driver_numbers: Sequence[int] = field(default_factory=tuple)
    constructors: Sequence[str] = field(default_factory=tuple)
    event_types: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class FeedEvent:
    """One delivered feed message.

    ``payload`` is the raw JSON body (the same shape as the webhook/SSE payload).
    Call :meth:`json` to decode it.
    """

    feed: str
    session_id: str
    utc: str
    seq: int
    payload: bytes

    def json(self) -> Any:
        """Decode the JSON payload into Python objects."""
        return json.loads(self.payload)


def _normalize_target(target: str) -> str:
    """Accept a full https URL or a bare host[:port] and return host:port."""
    if target.startswith("http://") or target.startswith("https://"):
        parsed = urlparse(target)
        host = parsed.hostname or ""
        port = parsed.port or (80 if parsed.scheme == "http" else 443)
        return f"{host}:{port}"
    if ":" not in target:
        return f"{target}:443"
    return target


class FeedStreamClient:
    """A connection to a RaceHooks grpc-gateway.

    Create one and reuse it; it is safe to open multiple subscriptions. Use it as
    a context manager, or call :meth:`close` when done.
    """

    def __init__(
        self,
        target: str,
        *,
        token: Optional[str] = None,
        tls: bool = True,
        channel_options: Optional[Sequence[tuple[str, Any]]] = None,
    ) -> None:
        """Dial the gateway.

        :param target: ``host:443``, ``host:port``, or a full https URL.
        :param token: Bearer token from ``POST /v1/oauth``, sent as authorization
            metadata on every subscription.
        :param tls: transport security. Defaults to ``True`` (Cloud Run). Set
            ``False`` only for a local h2c gateway or in tests.
        :param channel_options: raw gRPC channel options (escape hatch).
        """
        addr = _normalize_target(target)
        opts = list(channel_options) if channel_options else None
        if tls:
            self._channel = grpc.secure_channel(
                addr, grpc.ssl_channel_credentials(), options=opts
            )
        else:
            self._channel = grpc.insecure_channel(addr, options=opts)
        self._stub = feed_pb2_grpc.FeedStreamStub(self._channel)
        self._token = token

    def subscribe(
        self,
        feeds: Sequence[str],
        *,
        filters: Optional[Filters] = None,
        reconnect: bool = True,
        max_backoff: float = _DEFAULT_MAX_BACKOFF,
    ) -> "FeedStream":
        """Open a feed subscription.

        Returns a :class:`FeedStream` that yields :class:`FeedEvent` objects when
        iterated. ``feeds`` may be ``["*"]`` for every feed your tier allows.
        """
        return FeedStream(
            stub=self._stub,
            token=self._token,
            feeds=list(feeds),
            filters=filters,
            reconnect=reconnect,
            max_backoff=max_backoff,
        )

    def close(self) -> None:
        """Close the underlying gRPC channel."""
        self._channel.close()

    def __enter__(self) -> "FeedStreamClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class FeedStream:
    """A live subscription. Iterate it to receive :class:`FeedEvent` objects.

    Reconnect, resume, and dedupe are handled internally. The iterator runs until
    the stream is closed (or, when ``reconnect=False``, until the server ends the
    stream or a transport error occurs — which is re-raised).
    """

    def __init__(
        self,
        *,
        stub: feed_pb2_grpc.FeedStreamStub,
        token: Optional[str],
        feeds: List[str],
        filters: Optional[Filters],
        reconnect: bool,
        max_backoff: float,
    ) -> None:
        self._stub = stub
        self._token = token
        self._feeds = feeds
        self._filters = filters
        self._reconnect = reconnect
        self._max_backoff = max_backoff

        self._max_seq = 0
        self._closed = threading.Event()
        self._call: Optional[grpc.Call] = None

    def __iter__(self) -> Iterator[FeedEvent]:
        return self._run()

    def close(self) -> None:
        """Stop the subscription. Idempotent; safe to call from another thread."""
        self._closed.set()
        call = self._call
        if call is not None:
            call.cancel()

    def __enter__(self) -> "FeedStream":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _metadata(self) -> Optional[Sequence[tuple[str, str]]]:
        if not self._token:
            return None
        return (("authorization", f"Bearer {self._token}"),)

    def _request(self) -> feed_pb2.SubscribeRequest:
        req = feed_pb2.SubscribeRequest(feeds=self._feeds, resume_from=self._max_seq)
        if self._filters is not None:
            req.filters.driver_numbers.extend(self._filters.driver_numbers)
            req.filters.constructors.extend(self._filters.constructors)
            req.filters.event_types.extend(self._filters.event_types)
        return req

    def _run(self) -> Iterator[FeedEvent]:
        attempt = 0
        try:
            while not self._closed.is_set():
                reconnect_now = False
                try:
                    prev = self._call
                    self._call = self._stub.Subscribe(
                        self._request(), metadata=self._metadata(), wait_for_ready=True
                    )
                    # Overlap handoff: the new stream is open before the old one is
                    # cancelled, so a server-reconnect leaves no gap. Any duplicate
                    # from the overlap is dropped by seq.
                    if prev is not None:
                        prev.cancel()
                    # The server-streaming call is iterable at runtime; grpc types
                    # it only as Call, so cast for the type checker.
                    for msg in cast("Iterator[feed_pb2.FeedMessage]", self._call):
                        if self._closed.is_set():
                            return
                        feed = msg.feed
                        if feed == _CONTROL_CONNECTED:
                            continue
                        if feed == _CONTROL_RECONNECT:
                            reconnect_now = True
                            break
                        seq = msg.seq
                        if seq and seq <= self._max_seq:
                            continue  # duplicate from a resume overlap
                        if seq > self._max_seq:
                            self._max_seq = seq
                        yield FeedEvent(
                            feed=feed,
                            session_id=msg.session_id,
                            utc=msg.utc,
                            seq=seq,
                            payload=bytes(msg.json_payload),
                        )
                except grpc.RpcError as err:
                    if self._closed.is_set() or err.code() == grpc.StatusCode.CANCELLED:
                        return
                    if not self._reconnect:
                        raise
                    # transient error → backoff then resume
                else:
                    if self._closed.is_set():
                        return
                    if reconnect_now:
                        attempt = 0
                        continue  # server reconnect hint → resume immediately
                    if not self._reconnect:
                        return  # clean server end, reconnect disabled

                # Exponential backoff with the close event as an interruptible wait.
                delay = min(
                    _INITIAL_BACKOFF * (2 ** min(attempt, 5)), self._max_backoff
                )
                attempt += 1
                if self._closed.wait(delay):
                    return
        finally:
            call = self._call
            if call is not None:
                call.cancel()
