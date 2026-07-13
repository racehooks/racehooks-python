"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings
from ...racehooks.v1 import feed_pb2 as racehooks_dot_v1_dot_feed__pb2
GRPC_GENERATED_VERSION = '1.71.2'
GRPC_VERSION = grpc.__version__
_version_not_supported = False
try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True
if _version_not_supported:
    raise RuntimeError(f'The grpc package installed is at version {GRPC_VERSION},' + f' but the generated code in racehooks/v1/feed_pb2_grpc.py depends on' + f' grpcio>={GRPC_GENERATED_VERSION}.' + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}' + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.')

class FeedStreamStub(object):
    """RaceHooks streaming feed delivery over gRPC. See docs/GRPC_STREAMING_SPEC.md.

    Subscribe is the customer-facing server-streaming RPC: one request, an
    unbounded stream of feed messages. PushFeed is internal — the stream-gateway
    forwards each relayed feed message to the grpc-gateway, which fans it out to
    the matching Subscribe streams.
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Subscribe = channel.unary_stream('/racehooks.v1.FeedStream/Subscribe', request_serializer=racehooks_dot_v1_dot_feed__pb2.SubscribeRequest.SerializeToString, response_deserializer=racehooks_dot_v1_dot_feed__pb2.FeedMessage.FromString, _registered_method=True)
        self.PushFeed = channel.unary_unary('/racehooks.v1.FeedStream/PushFeed', request_serializer=racehooks_dot_v1_dot_feed__pb2.PushFeedRequest.SerializeToString, response_deserializer=racehooks_dot_v1_dot_feed__pb2.PushAck.FromString, _registered_method=True)

class FeedStreamServicer(object):
    """RaceHooks streaming feed delivery over gRPC. See docs/GRPC_STREAMING_SPEC.md.

    Subscribe is the customer-facing server-streaming RPC: one request, an
    unbounded stream of feed messages. PushFeed is internal — the stream-gateway
    forwards each relayed feed message to the grpc-gateway, which fans it out to
    the matching Subscribe streams.
    """

    def Subscribe(self, request, context):
        """Customer-facing: subscribe to one or more feeds; receive a stream of
        FeedMessage until the client cancels or the server closes for reconnect.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def PushFeed(self, request, context):
        """Internal: stream-gateway → grpc-gateway relay of one enriched feed message.
        Authenticated by the relay secret in metadata (x-racehooks-relay-secret).
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

def add_FeedStreamServicer_to_server(servicer, server):
    rpc_method_handlers = {'Subscribe': grpc.unary_stream_rpc_method_handler(servicer.Subscribe, request_deserializer=racehooks_dot_v1_dot_feed__pb2.SubscribeRequest.FromString, response_serializer=racehooks_dot_v1_dot_feed__pb2.FeedMessage.SerializeToString), 'PushFeed': grpc.unary_unary_rpc_method_handler(servicer.PushFeed, request_deserializer=racehooks_dot_v1_dot_feed__pb2.PushFeedRequest.FromString, response_serializer=racehooks_dot_v1_dot_feed__pb2.PushAck.SerializeToString)}
    generic_handler = grpc.method_handlers_generic_handler('racehooks.v1.FeedStream', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('racehooks.v1.FeedStream', rpc_method_handlers)

class FeedStream(object):
    """RaceHooks streaming feed delivery over gRPC. See docs/GRPC_STREAMING_SPEC.md.

    Subscribe is the customer-facing server-streaming RPC: one request, an
    unbounded stream of feed messages. PushFeed is internal — the stream-gateway
    forwards each relayed feed message to the grpc-gateway, which fans it out to
    the matching Subscribe streams.
    """

    @staticmethod
    def Subscribe(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_stream(request, target, '/racehooks.v1.FeedStream/Subscribe', racehooks_dot_v1_dot_feed__pb2.SubscribeRequest.SerializeToString, racehooks_dot_v1_dot_feed__pb2.FeedMessage.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)

    @staticmethod
    def PushFeed(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/racehooks.v1.FeedStream/PushFeed', racehooks_dot_v1_dot_feed__pb2.PushFeedRequest.SerializeToString, racehooks_dot_v1_dot_feed__pb2.PushAck.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)