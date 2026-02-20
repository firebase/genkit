from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor, message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class JokeRequest(_message.Message):
    __slots__ = ("name", "username")
    NAME_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    username: str
    def __init__(self, name: str | None = ..., username: str | None = ...) -> None: ...

class JokeResponse(_message.Message):
    __slots__ = ("joke", "username")
    JOKE_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    joke: str
    username: str
    def __init__(self, joke: str | None = ..., username: str | None = ...) -> None: ...

class TranslateRequest(_message.Message):
    __slots__ = ("text", "target_language")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    TARGET_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    text: str
    target_language: str
    def __init__(self, text: str | None = ..., target_language: str | None = ...) -> None: ...

class TranslationResponse(_message.Message):
    __slots__ = ("original_text", "translated_text", "target_language", "confidence")
    ORIGINAL_TEXT_FIELD_NUMBER: _ClassVar[int]
    TRANSLATED_TEXT_FIELD_NUMBER: _ClassVar[int]
    TARGET_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    original_text: str
    translated_text: str
    target_language: str
    confidence: str
    def __init__(self, original_text: str | None = ..., translated_text: str | None = ..., target_language: str | None = ..., confidence: str | None = ...) -> None: ...

class ImageRequest(_message.Message):
    __slots__ = ("image_url",)
    IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    image_url: str
    def __init__(self, image_url: str | None = ...) -> None: ...

class ImageResponse(_message.Message):
    __slots__ = ("description", "image_url")
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    description: str
    image_url: str
    def __init__(self, description: str | None = ..., image_url: str | None = ...) -> None: ...

class CharacterRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: str | None = ...) -> None: ...

class Skills(_message.Message):
    __slots__ = ("strength", "charisma", "endurance")
    STRENGTH_FIELD_NUMBER: _ClassVar[int]
    CHARISMA_FIELD_NUMBER: _ClassVar[int]
    ENDURANCE_FIELD_NUMBER: _ClassVar[int]
    strength: int
    charisma: int
    endurance: int
    def __init__(self, strength: int | None = ..., charisma: int | None = ..., endurance: int | None = ...) -> None: ...

class RpgCharacter(_message.Message):
    __slots__ = ("name", "back_story", "abilities", "skills")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BACK_STORY_FIELD_NUMBER: _ClassVar[int]
    ABILITIES_FIELD_NUMBER: _ClassVar[int]
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    name: str
    back_story: str
    abilities: _containers.RepeatedScalarFieldContainer[str]
    skills: Skills
    def __init__(self, name: str | None = ..., back_story: str | None = ..., abilities: _Iterable[str] | None = ..., skills: Skills | _Mapping | None = ...) -> None: ...

class ChatRequest(_message.Message):
    __slots__ = ("question",)
    QUESTION_FIELD_NUMBER: _ClassVar[int]
    question: str
    def __init__(self, question: str | None = ...) -> None: ...

class ChatResponse(_message.Message):
    __slots__ = ("answer", "persona")
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    PERSONA_FIELD_NUMBER: _ClassVar[int]
    answer: str
    persona: str
    def __init__(self, answer: str | None = ..., persona: str | None = ...) -> None: ...

class StoryRequest(_message.Message):
    __slots__ = ("topic",)
    TOPIC_FIELD_NUMBER: _ClassVar[int]
    topic: str
    def __init__(self, topic: str | None = ...) -> None: ...

class StoryChunk(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: str | None = ...) -> None: ...

class StoryResponse(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: str | None = ...) -> None: ...

class CodeRequest(_message.Message):
    __slots__ = ("description", "language")
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    description: str
    language: str
    def __init__(self, description: str | None = ..., language: str | None = ...) -> None: ...

class CodeResponse(_message.Message):
    __slots__ = ("code", "language", "explanation", "filename")
    CODE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    EXPLANATION_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    code: str
    language: str
    explanation: str
    filename: str
    def __init__(self, code: str | None = ..., language: str | None = ..., explanation: str | None = ..., filename: str | None = ...) -> None: ...

class CodeReviewRequest(_message.Message):
    __slots__ = ("code", "language")
    CODE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    code: str
    language: str
    def __init__(self, code: str | None = ..., language: str | None = ...) -> None: ...

class CodeReviewResponse(_message.Message):
    __slots__ = ("review",)
    REVIEW_FIELD_NUMBER: _ClassVar[int]
    review: str
    def __init__(self, review: str | None = ...) -> None: ...

class HealthRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: str
    def __init__(self, status: str | None = ...) -> None: ...
