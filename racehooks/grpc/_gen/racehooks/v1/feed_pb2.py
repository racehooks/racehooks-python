"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 0, '', 'racehooks/v1/feed.proto')
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x17racehooks/v1/feed.proto\x12\x0cracehooks.v1"^\n\x10SubscribeRequest\x12\r\n\x05feeds\x18\x01 \x03(\t\x12&\n\x07filters\x18\x02 \x01(\x0b2\x15.racehooks.v1.Filters\x12\x13\n\x0bresume_from\x18\x03 \x01(\x04"L\n\x07Filters\x12\x16\n\x0edriver_numbers\x18\x01 \x03(\x05\x12\x14\n\x0cconstructors\x18\x02 \x03(\t\x12\x13\n\x0bevent_types\x18\x03 \x03(\t"_\n\x0bFeedMessage\x12\x0c\n\x04feed\x18\x01 \x01(\t\x12\x12\n\nsession_id\x18\x02 \x01(\t\x12\x0b\n\x03utc\x18\x03 \x01(\t\x12\x14\n\x0cjson_payload\x18\x04 \x01(\x0c\x12\x0b\n\x03seq\x18\x05 \x01(\x04"Q\n\x0fPushFeedRequest\x12\x0c\n\x04feed\x18\x01 \x01(\t\x12\r\n\x05scope\x18\x02 \x01(\t\x12\x0b\n\x03seq\x18\x03 \x01(\x04\x12\x14\n\x0cjson_payload\x18\x04 \x01(\x0c"\x15\n\x07PushAck\x12\n\n\x02ok\x18\x01 \x01(\x082\x98\x01\n\nFeedStream\x12H\n\tSubscribe\x12\x1e.racehooks.v1.SubscribeRequest\x1a\x19.racehooks.v1.FeedMessage0\x01\x12@\n\x08PushFeed\x12\x1d.racehooks.v1.PushFeedRequest\x1a\x15.racehooks.v1.PushAckb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'racehooks.v1.feed_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SUBSCRIBEREQUEST']._serialized_start = 41
    _globals['_SUBSCRIBEREQUEST']._serialized_end = 135
    _globals['_FILTERS']._serialized_start = 137
    _globals['_FILTERS']._serialized_end = 213
    _globals['_FEEDMESSAGE']._serialized_start = 215
    _globals['_FEEDMESSAGE']._serialized_end = 310
    _globals['_PUSHFEEDREQUEST']._serialized_start = 312
    _globals['_PUSHFEEDREQUEST']._serialized_end = 393
    _globals['_PUSHACK']._serialized_start = 395
    _globals['_PUSHACK']._serialized_end = 416
    _globals['_FEEDSTREAM']._serialized_start = 419
    _globals['_FEEDSTREAM']._serialized_end = 571