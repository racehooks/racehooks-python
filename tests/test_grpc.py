"""Tests for the gRPC streaming client.

These run a real in-process gRPC server on an ephemeral port (the standard way to
test gRPC clients in Python) and drive the real client against it. Iteration is
blocking, so each subscription is consumed in a background thread that feeds a
queue the test reads with a timeout.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from concurrent import futures
from contextlib import contextmanager
from typing import Callable, Iterator

import grpc
import pytest

from racehooks.grpc import FeedStreamClient, Filters
from racehooks.grpc._gen.racehooks.v1 import feed_pb2, feed_pb2_grpc

SubscribeHandler = Callable[
    [feed_pb2.SubscribeRequest, grpc.ServicerContext], Iterator[feed_pb2.FeedMessage]
]


class _Servicer(feed_pb2_grpc.FeedStreamServicer):
    def __init__(self, handler: SubscribeHandler) -> None:
        self._handler = handler

    def Subscribe(self, request, context):  # noqa: N802 - gRPC method name
        yield from self._handler(request, context)


@contextmanager
def serve(handler: SubscribeHandler):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    feed_pb2_grpc.add_FeedStreamServicer_to_server(_Servicer(handler), server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        yield f"127.0.0.1:{port}"
    finally:
        server.stop(grace=0)


def msg(
    feed: str, *, seq: int = 0, session: str = "", body=None
) -> feed_pb2.FeedMessage:
    payload = json.dumps(body).encode() if body is not None else b""
    return feed_pb2.FeedMessage(
        feed=feed, session_id=session, utc="t", seq=seq, json_payload=payload
    )


def hold(context: grpc.ServicerContext) -> None:
    """Block the handler until the client cancels (keeps the stream open)."""
    while context.is_active():
        time.sleep(0.01)


class Consumer:
    """Consumes a blocking subscription in a background thread."""

    def __init__(self, stream) -> None:
        self._stream = stream
        self._q: "queue.Queue[tuple[str, object]]" = queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            for ev in self._stream:
                self._q.put(("event", ev))
            self._q.put(("end", None))
        except Exception as exc:  # noqa: BLE001 - surfaced to the test
            self._q.put(("error", exc))

    def next(self, timeout: float = 3.0):
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            raise AssertionError("timed out waiting for a stream item")


@contextmanager
def client_for(target: str):
    client = FeedStreamClient(target, tls=False, token="tok-123")
    try:
        yield client
    finally:
        client.close()


def test_delivers_messages():
    def handler(_req, ctx):
        yield msg("_connected")
        yield msg(
            "timingdata", seq=1, session="s1", body={"drivers": [{"number": "1"}]}
        )
        hold(ctx)

    with serve(handler) as target, client_for(target) as client:
        c = Consumer(client.subscribe(["timingdata"]))
        kind, ev = c.next()
        assert kind == "event"
        assert ev.feed == "timingdata" and ev.seq == 1 and ev.session_id == "s1"
        assert ev.json() == {"drivers": [{"number": "1"}]}


def test_forwards_token_feeds_and_resume():
    seen = {}

    def handler(req, ctx):
        seen["auth"] = dict(ctx.invocation_metadata()).get("authorization")
        seen["feeds"] = list(req.feeds)
        seen["resume"] = req.resume_from
        yield msg("timingdata", seq=1, body={"x": 1})
        hold(ctx)

    with serve(handler) as target, client_for(target) as client:
        c = Consumer(client.subscribe(["timingdata", "racecontrol"]))
        c.next()  # one event proves the server processed the request
        assert seen["auth"] == "Bearer tok-123"
        assert seen["feeds"] == ["timingdata", "racecontrol"]
        assert seen["resume"] == 0


def test_filters_are_sent():
    seen = {}

    def handler(req, ctx):
        seen["drivers"] = list(req.filters.driver_numbers)
        seen["constructors"] = list(req.filters.constructors)
        yield msg("timingdata", seq=1, body={"x": 1})
        hold(ctx)

    with serve(handler) as target, client_for(target) as client:
        c = Consumer(
            client.subscribe(
                ["*"], filters=Filters(driver_numbers=[1, 16], constructors=["ferrari"])
            )
        )
        c.next()
        assert seen["drivers"] == [1, 16]
        assert seen["constructors"] == ["ferrari"]


def test_dedupes_by_seq():
    def handler(_req, ctx):
        yield msg("_connected")
        yield msg("timingdata", seq=5, body={"x": 1})
        yield msg("timingdata", seq=5, body={"x": 1})  # duplicate
        yield msg("timingdata", seq=6, body={"x": 1})
        hold(ctx)

    with serve(handler) as target, client_for(target) as client:
        c = Consumer(client.subscribe(["*"]))
        assert c.next()[1].seq == 5
        assert c.next()[1].seq == 6  # duplicate 5 dropped


def test_reconnect_resumes_from_last_seq():
    calls = Counter()
    seen = {}

    def handler(req, ctx):
        n = calls.next()
        if n == 0:
            yield msg("_connected")
            yield msg("timingdata", seq=1, body={"x": 1})
            return  # end stream → client reconnects
        seen["resume"] = req.resume_from
        yield msg("timingdata", seq=2, body={"x": 2})
        hold(ctx)

    with serve(handler) as target, client_for(target) as client:
        c = Consumer(client.subscribe(["*"], max_backoff=0.1))
        assert c.next()[1].seq == 1
        assert c.next()[1].seq == 2
        assert seen["resume"] == 1


def test_server_reconnect_frame_resubscribes():
    calls = Counter()

    def handler(_req, ctx):
        n = calls.next()
        if n == 0:
            yield msg("_connected")
            yield msg("_reconnect")
            hold(ctx)
        else:
            yield msg("timingdata", seq=9, body={"x": 1})
            hold(ctx)

    with serve(handler) as target, client_for(target) as client:
        c = Consumer(client.subscribe(["*"]))
        assert c.next()[1].seq == 9


def test_disable_reconnect_ends_on_server_end():
    def handler(_req, _ctx):
        yield msg("timingdata", seq=1, body={"x": 1})
        # generator returns → clean server end

    with serve(handler) as target, client_for(target) as client:
        c = Consumer(client.subscribe(["*"], reconnect=False))
        assert c.next()[1].seq == 1
        assert c.next()[0] == "end"  # iterator ends, no error


def test_close_stops_stream():
    def handler(_req, ctx):
        yield msg("_connected")
        yield msg("timingdata", seq=1, body={"x": 1})
        hold(ctx)

    with serve(handler) as target, client_for(target) as client:
        stream = client.subscribe(["*"])
        c = Consumer(stream)
        assert c.next()[1].seq == 1
        stream.close()
        assert c.next()[0] == "end"


class Counter:
    """Thread-safe call counter (the gRPC server runs handlers in a thread pool,
    and a reconnect overlap can run two handlers concurrently)."""

    def __init__(self) -> None:
        self._n = -1
        self._lock = threading.Lock()

    def next(self) -> int:
        with self._lock:
            self._n += 1
            return self._n


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
