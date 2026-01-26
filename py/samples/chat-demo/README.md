# Genkit Chat Demo

This sample demonstrates how to build a full-featured web chat application using Genkit's session and chat APIs with Streamlit.

## Features

* **Multi-Model Support**: Switch between Google (Gemini), Anthropic (Claude), DeepSeek, xAI (Grok), OpenAI, and Ollama.
* **Multiple Conversations**: Create and manage parallel chat threads.
* **Persistent Sessions**: Conversation history maintained per thread.
* **Streaming**: Real-time response streaming.
* **Rich UI**: Built with Streamlit for a web-based experience.

## Running

```bash
./run.sh
```

This launches the Streamlit app. Configure API keys in the sidebar.

## Key APIs Demonstrated

| API | Description | Example |
|-----|-------------|---------|
| `ai.chat()` | Create a chat with thread support | `chat = ai.chat(thread='conv1')` |
| `chat.send()` | Send message, get complete response | `response = await chat.send('Hi')` |
| `chat.send_stream()` | Send message, stream response | `result = chat.send_stream('Hi')` |
| `chat.thread` | Get the thread name | `print(chat.thread)` |

## Prerequisites

* Python 3.12+
* `uv` (recommended)

## Setup

Set your API keys as environment variables:

```bash
export GEMINI_API_KEY=your-key          # For Google Gemini
export ANTHROPIC_API_KEY=your-key       # For Anthropic Claude
export DEEPSEEK_API_KEY=your-key        # For DeepSeek
export XAI_API_KEY=your-key             # For xAI Grok
export OPENAI_API_KEY=your-key          # For OpenAI
```

For Vertex AI, also set:

```bash
export VERTEX_AI_PROJECT_ID=your-project
export VERTEX_AI_LOCATION=us-central1
```

For Ollama, ensure your Ollama server is running locally.

## Related Samples

* `session-demo/` - Lower-level session management examples
