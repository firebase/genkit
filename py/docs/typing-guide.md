# Type-Safe Development with Genkit Python

Genkit Python provides full type safety, giving you IDE autocomplete, inline documentation, and compile-time error detection. This guide shows what's possible with proper typing.

## Why Types Matter

```
 Without Types                          With Types
 ─────────────────────────────────────────────────────────────────
 
 result = my_flow(data)                 result = my_flow(data)
         │                                       │
         ▼                                       ▼
 result.???                              result.name ✓
 # No autocomplete                       result.age ✓  
 # No error detection                    result.email ✓
 # Runtime surprises                     # Full autocomplete!
```

## Flows: Full Type Preservation

### Defining Typed Flows

```python
from pydantic import BaseModel
from genkit import Genkit

ai = Genkit()

# Define your input/output types
class UserQuery(BaseModel):
    question: str
    context: list[str] | None = None

class Answer(BaseModel):
    response: str
    confidence: float
    sources: list[str]

# The decorator preserves types!
@ai.flow()
async def answer_question(query: UserQuery) -> Answer:
    result = await ai.generate(
        model="googleai/gemini-2.0-flash",
        prompt=query.question,
    )
    return Answer(
        response=result.text,
        confidence=0.95,
        sources=query.context or [],
    )
```

### What You Get

```python
# ✅ IDE knows input type
query = UserQuery(question="What is Genkit?")

# ✅ IDE knows output type  
answer = await answer_question(query)

# ✅ Full autocomplete on result
print(answer.response)    # ✓ string
print(answer.confidence)  # ✓ float
print(answer.sources)     # ✓ list[str]

# ❌ Caught at development time!
print(answer.wrongfield)  # IDE error: "Answer" has no attribute "wrongfield"
```

## Tools: Type-Safe Function Calling

```python
class WeatherRequest(BaseModel):
    city: str
    units: Literal["celsius", "fahrenheit"] = "celsius"

class WeatherResponse(BaseModel):
    temperature: float
    conditions: str
    humidity: int

@ai.tool()
def get_weather(request: WeatherRequest) -> WeatherResponse:
    """Get current weather for a city."""
    return WeatherResponse(
        temperature=22.5,
        conditions="Sunny",
        humidity=45,
    )
```

## IDE Experience: Before vs After

### Autocomplete

```
┌─────────────────────────────────────────────────────────────┐
│  WITHOUT TYPES                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  result = await my_flow(data)                               │
│  result.█                                                   │
│         │                                                   │
│         └─ No suggestions available                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  WITH TYPES                                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  result = await my_flow(data)                               │
│  result.█                                                   │
│         ├─────────────────────────┐                         │
│         │ ▶ response      str     │                         │
│         │ ▶ confidence    float   │                         │
│         │ ▶ sources       list    │                         │
│         │ ▶ model_dump()  method  │                         │
│         └─────────────────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Inline Error Detection

```
┌─────────────────────────────────────────────────────────────┐
│  WITHOUT TYPES: Error at runtime                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  @ai.flow()                                                 │
│  async def process(data: dict) -> dict:                     │
│      return {"result": data["naem"]}  # Typo not caught!    │
│                                                             │
│  # Crashes at runtime with KeyError                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  WITH TYPES: Error caught immediately                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  class Input(BaseModel):                                    │
│      name: str                                              │
│                                                             │
│  @ai.flow()                                                 │
│  async def process(data: Input) -> Output:                  │
│      return Output(result=data.naem)                        │
│                              ════                           │
│                              └─ Error: "Input" has no       │
│                                 attribute "naem". Did you   │
│                                 mean "name"?                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Best Practices

### 1. Always Use Pydantic Models

```python
# ❌ Avoid: dict types lose structure
@ai.flow()
async def process(data: dict) -> dict:
    ...

# ✅ Prefer: Pydantic models preserve structure
@ai.flow()
async def process(data: UserInput) -> ProcessedOutput:
    ...
```

### 2. Define Output Schemas for Structured Output

```python
# ❌ Avoid: Parsing JSON manually
response = await ai.generate(prompt="Return JSON...")
data = json.loads(response.text)  # No type info!

# ✅ Prefer: Use output_schema
response = await ai.generate(
    prompt="...",
    output_schema=MyOutputType,
    output_format="json",
)
data: MyOutputType = response.output  # Fully typed!
```

### 3. Use Literal Types for Constrained Values

```python
from typing import Literal

class Config(BaseModel):
    mode: Literal["fast", "accurate", "balanced"]
    format: Literal["json", "text", "markdown"]
```

### 4. Enable Strict Type Checking

Add to your `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.10"
strict = true
plugins = ["pydantic.mypy"]

[tool.pyright]
typeCheckingMode = "strict"
```

## Summary

| Feature | Without Types | With Types |
|---------|---------------|------------|
| IDE Autocomplete | None | Full support |
| Error Detection | Runtime | Development time |
| Documentation | Manual lookup | Inline hover |
| Refactoring | Error-prone | Safe |
| Code Navigation | Limited | Go to definition |

Genkit's type system helps you write correct code faster, catch bugs before production, and make your codebase self-documenting.
