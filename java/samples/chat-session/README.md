# Chat Session Sample

This sample demonstrates session-based multi-turn chat with persistence in Genkit Java.

## Features

- **Multi-turn conversations** - Automatic conversation history management
- **Session state** - Track user preferences and conversation context
- **Session persistence** - Save and load sessions across interactions
- **Tool integration** - Using tools (note-taking) within chat sessions
- **Multiple personas** - Choose between assistant, tutor, and creative modes

## Prerequisites

1. Java 17 or later
2. Maven
3. OpenAI API key

## Setup

Set your OpenAI API key:

```bash
export OPENAI_API_KEY=your-api-key-here
```

## Running

### Interactive Mode

Start an interactive chat session:

```bash
cd java
mvn exec:java -pl samples/chat-session
```

### Demo Mode

Run the automated demo to see all features:

```bash
cd java
mvn exec:java -pl samples/chat-session -Dexec.args="--demo"
```

## Commands

During interactive chat, you can use these commands:

| Command | Description |
|---------|-------------|
| `/history` | Show conversation history |
| `/notes` | Show saved notes |
| `/state` | Show session state |
| `/topic X` | Set conversation topic to X |
| `/quit` | Exit the chat |

## Example Session

```
What's your name? Alice

Choose a chat persona:
  1. Assistant (general help)
  2. Tutor (learning & education)
  3. Creative (storytelling & ideas)
Enter choice (1-3): 2

✓ Session created: a1b2c3d4-e5f6-...
✓ Persona: tutor

You: What is photosynthesis?