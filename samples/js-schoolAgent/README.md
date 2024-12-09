# School Agent Sample

A demonstration of a conversational AI assistant for a school system using GenKit and Google's Gemini Pro. This agent helps parents with attendance reporting and school information queries.

This multi-agent demo works best on Gemini 1.5 Pro. It also works with Gemini 1.0 Pro but is sometimes more prone to errors / not fully recognizing that the specialized agents come equipped with certain actiions.

## Features

- **Prompt-as-Tool Architecture**:

  - Main InfoAgent uses specialized agents as tools
  - Seamless transitions between agents without explicit routing
  - Each agent has focused responsibilities and specialized tools

- **Agent Structure**:
  - `InfoAgent`: Main entry point with access to general tools and specialized agents
  - `AttendanceAgent`: Specialized agent for absence/tardy reporting

## Prerequisites

- Node.js installed
- Google AI API key

## Getting Started

1. Install dependencies:

```bash
npm install
```

2. Set up your Google AI API key:

```bash
export GOOGLE_GENAI_API_KEY=your_api_key_here
```

3. Start the development server in watch mode:

```bash
npm run genkit:dev
```

In your terminal, a commandline chat interface should show up:

```
Telemetry API running on http://localhost:4033
Genkit Developer UI: http://localhost:4000

> school-agent@1.0.0 dev
> tsx --no-warnings --watch src/terminal.ts

bell> Hi there, my name is Bell and I'm here to help! 👋🎉 I'm your friendly AI assistant for parents of Sparkyville High School. I can answer your questions about the school, events, grades, and more. Just ask me! 😊

prompt> [insert your chats here]
```

Any changes to the sample will be reflected immediately and should restart the chat agent.

## Usage

The agent uses a multi-agent architecture:

- Information Agent: Acts as the main entry point and router, handling general queries directly while delegating specialized requests to appropriate agents
- Attendance Agent: Specialized agent focused on absence and tardy reporting

Example queries:

- "Mark Evenlyn Smith as absent please"
- "What are the upcoming holidays I should be aware of?"
- "What are Evelyn's grades?"

## Project Structure

- `src/`
  - `agents/`
    - `infoAgent.ts` - Main agent that uses other agents as tools, and has additional tools for general-purpose QA
    - `attendanceAgent.ts` - Specialized attendance agent
    - `gradesAgent.ts` - Specialized grades agent
  - `tools.ts` - Tool definitions
  - `types.ts` - TypeScript types
  - `data.ts` - Sample data
