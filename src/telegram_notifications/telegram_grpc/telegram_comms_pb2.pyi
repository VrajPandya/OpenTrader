from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class NotificationMessage(_message.Message):
    __slots__ = ["message_str"]
    MESSAGE_STR_FIELD_NUMBER: _ClassVar[int]
    message_str: str
    def __init__(self, message_str: _Optional[str] = ...) -> None: ...

class ServerReply(_message.Message):
    __slots__ = ["success"]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...
