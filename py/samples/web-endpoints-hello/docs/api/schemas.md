# Schemas

All request and response bodies use [Pydantic](https://docs.pydantic.dev/)
models defined in `src/schemas.py`. The same models are shared between
REST validation and Genkit flow `Input`/`Output` schemas.

## Input validation

Every input model includes `Field` constraints so that Pydantic rejects
malformed input **before** it reaches any flow or LLM call:

| Constraint | Example | Effect |
|------------|---------|--------|
| `max_length` | `name: str = Field(max_length=200)` | Rejects strings over 200 chars |
| `min_length` | `text: str = Field(min_length=1)` | Rejects empty strings |
| `ge` / `le` | `strength: int = Field(ge=0, le=100)` | Range check |
| `pattern` | `language: str = Field(pattern=r"^[a-zA-Z#+]+$")` | Regex validation |

This is a defense-in-depth layer on top of `MaxBodySizeMiddleware`
(which rejects oversized HTTP bodies at the ASGI level).

## Models

### JokeInput

```python
class JokeInput(BaseModel):
    name: str = Field(default="Mittens", max_length=200)
    username: str | None = Field(default=None, max_length=200)
```

### JokeResponse

```python
class JokeResponse(BaseModel):
    joke: str
    username: str | None = None
```

### TranslateInput

```python
class TranslateInput(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    target_language: str = Field(default="French", max_length=100)
```

### TranslationResult

Returned directly by the LLM via structured output:

```python
class TranslationResult(BaseModel):
    original_text: str
    translated_text: str
    target_language: str
    confidence: str  # "high", "medium", or "low"
```

### ImageInput

```python
class ImageInput(BaseModel):
    image_url: str = Field(max_length=2048)
```

### ImageResponse

```python
class ImageResponse(BaseModel):
    description: str
    image_url: str
```

### CharacterInput / RpgCharacter

```python
class CharacterInput(BaseModel):
    name: str = Field(default="Luna", min_length=1, max_length=200)

class Skills(BaseModel):
    strength: int = Field(ge=0, le=100)
    charisma: int = Field(ge=0, le=100)
    endurance: int = Field(ge=0, le=100)

class RpgCharacter(BaseModel):
    name: str
    back_story: str = Field(alias="backStory")
    abilities: list[str] = Field(max_length=10)
    skills: Skills
```

### ChatInput / ChatResponse

```python
class ChatInput(BaseModel):
    question: str = Field(min_length=1, max_length=5_000)

class ChatResponse(BaseModel):
    answer: str
    persona: str = "pirate captain"
```

### StoryInput

```python
class StoryInput(BaseModel):
    topic: str = Field(default="a brave cat", min_length=1, max_length=1_000)
```

### CodeInput / CodeOutput

```python
class CodeInput(BaseModel):
    description: str = Field(min_length=1, max_length=10_000)
    language: str = Field(default="python", max_length=50, pattern=r"^[a-zA-Z#+]+$")

class CodeOutput(BaseModel):
    code: str
    language: str
    explanation: str
    filename: str
```

### CodeReviewInput

```python
class CodeReviewInput(BaseModel):
    code: str = Field(min_length=1, max_length=50_000)
    language: str | None = Field(default=None, max_length=50)
```

## Schema → endpoint mapping

| Schema | Used by | Protocol |
|--------|---------|----------|
| `JokeInput` → `JokeResponse` | `/tell-joke`, `TellJoke` | REST, gRPC |
| `TranslateInput` → `TranslationResult` | `/translate`, `TranslateText` | REST, gRPC |
| `ImageInput` → `ImageResponse` | `/describe-image`, `DescribeImage` | REST, gRPC |
| `CharacterInput` → `RpgCharacter` | `/generate-character`, `GenerateCharacter` | REST, gRPC |
| `ChatInput` → `ChatResponse` | `/chat`, `PirateChat` | REST, gRPC |
| `StoryInput` → SSE chunks | `/tell-story/stream`, `TellStory` | REST, gRPC |
| `CodeInput` → `CodeOutput` | `/generate-code`, `GenerateCode` | REST, gRPC |
| `CodeReviewInput` → response | `/review-code`, `ReviewCode` | REST, gRPC |
