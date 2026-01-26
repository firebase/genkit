# Genkit Chat Demo

This sample demonstrates how to build a multi-provider, multi-session chat application using Genkit and Streamlit.

## Features Demonstrated

*   **Multi-Model Support**: Switch seamlessly between models from Google (Gemini), Anthropic (Claude), DeepSeek, xAI (Grok), OpenAI, and Ollama.
*   **Multiple Conversations**: Create and manage multiple parallel chat threads.
*   **Persistent Sessions**: Conversation history is maintained for each thread.
*   **Rich UI**: Built with Streamlit for a web-based chat experience.
*   **Dynamic Configuration**: Configure API keys and models directly in the UI.

## Prerequisites

*   Python 3.12+
*   `uv` (recommended)

## Setup

1.  (Optional) Set your API keys as environment variables for convenience:
    *   `GEMINI_API_KEY`
    *   `ANTHROPIC_API_KEY`
    *   `DEEPSEEK_API_KEY`
    *   `XAI_API_KEY`
    *   `OPENAI_API_KEY`
2.  If using Ollama, ensure your Ollama server is running locally.

## Running

```bash
./run.sh
```

This will launch the Streamlit app in your default browser. You can configure any missing API keys directly in the sidebar.
