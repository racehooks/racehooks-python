from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union
DESCRIPTOR: _descriptor.FileDescriptor

class SubscribeRequest(_message.Message):
    __slots__ = ('feeds', 'filters', 'resume_from')
    FEEDS_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    RESUME_FROM_FIELD_NUMBER: _ClassVar[int]
    feeds: _containers.RepeatedScalarFieldContainer[str]
    filters: Filters
    resume_from: int

    def __init__(self, feeds: _Optional[_Iterable[str]]=..., filters: _Optional[_Union[Filters, _Mapping]]=..., resume_from: _Optional[int]=...) -> None:
        ...

class Filters(_message.Message):
    __slots__ = ('driver_numbers', 'constructors', 'event_types')
    DRIVER_NUMBERS_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTORS_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPES_FIELD_NUMBER: _ClassVar[int]
    driver_numbers: _containers.RepeatedScalarFieldContainer[int]
    constructors: _containers.RepeatedScalarFieldContainer[str]
    event_types: _containers.RepeatedScalarFieldContainer[str]

    def __init__(self, driver_numbers: _Optional[_Iterable[int]]=..., constructors: _Optional[_Iterable[str]]=..., event_types: _Optional[_Iterable[str]]=...) -> None:
        ...

class FeedMessage(_message.Message):
    __slots__ = ('feed', 'session_id', 'utc', 'json_payload', 'seq')
    FEED_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    UTC_FIELD_NUMBER: _ClassVar[int]
    JSON_PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    SEQ_FIELD_NUMBER: _ClassVar[int]
    feed: str
    session_id: str
    utc: str
    json_payload: bytes
    seq: int

    def __init__(self, feed: _Optional[str]=..., session_id: _Optional[str]=..., utc: _Optional[str]=..., json_payload: _Optional[bytes]=..., seq: _Optional[int]=...) -> None:
        ...

class PushFeedRequest(_message.Message):
    __slots__ = ('feed', 'scope', 'seq', 'json_payload')
    FEED_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    SEQ_FIELD_NUMBER: _ClassVar[int]
    JSON_PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    feed: str
    scope: str
    seq: int
    json_payload: bytes

    def __init__(self, feed: _Optional[str]=..., scope: _Optional[str]=..., seq: _Optional[int]=..., json_payload: _Optional[bytes]=...) -> None:
        ...

class PushAck(_message.Message):
    __slots__ = ('ok',)
    OK_FIELD_NUMBER: _ClassVar[int]
    ok: bool

    def __init__(self, ok: bool=...) -> None:
        ...