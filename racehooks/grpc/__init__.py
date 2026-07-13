"""RaceHooks gRPC streaming client.

This subpackage requires the optional ``grpc`` dependency group::

    pip install 'racehooks[grpc]'

Then::

    from racehooks.grpc import FeedStreamClient
"""

from __future__ import annotations

try:
    import grpc as _grpc  # noqa: F401
except (
    ModuleNotFoundError
) as exc:  # pragma: no cover - exercised only without the extra
    raise ModuleNotFoundError(
        "The RaceHooks gRPC streaming client requires grpcio. "
        "Install it with: pip install 'racehooks[grpc]'"
    ) from exc

from .client import FeedEvent, FeedStream, FeedStreamClient, Filters

__all__ = ["FeedStreamClient", "FeedStream", "FeedEvent", "Filters"]
