# Genkit Session Management Demo

This sample demonstrates how to use Genkit's advanced session management features to create stateful conversations with structured state updates.

## Features Demonstrated

*   **Interactive Flow**: A guided step-by-step interactive flow using Streamlit.
*   **Session Creation**: Initializing sessions with initial state (e.g., `user_name`, `preference`).
*   **State Updates**: Updating session state dynamically during the conversation (e.g., changing `topic`).
*   **Multi-Provider Support**: Switch between models from Google, Anthropic, DeepSeek, xAI, OpenAI, and Ollama.
*   **State Visualization**: Real-time view of the session's internal stateJSON.

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

This will launch the Streamlit app. Follow the interactive buttons to step through the session flow and watch the state update in real-time.

## Testing This Demo

1. **Open the Streamlit UI** at http://localhost:8501

2. **Test the following**:
   - [ ] Create a new session and note the session ID
   - [ ] Send messages and verify they're stored in session
   - [ ] Check that session state is displayed/updated
   - [ ] Reload the page and verify session persists (in-memory)
   - [ ] Create multiple sessions and switch between them
   - [ ] Test with different model providers

3. **Expected behavior**:
   - Sessions maintain conversation history
   - State changes persist within session lifetime
   - Each session has unique ID for identification
