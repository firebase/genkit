# Genkit Multi-Agent Sample

This sample demonstrates multi-agent orchestration patterns using Genkit Java, where specialized agents handle different domains and a triage agent routes requests.

## Features Demonstrated

- **Multi-Agent Architecture** - Triage agent routing to specialized agents
- **Specialized Agents** - Reservation, menu, and order agents
- **Agent-as-Tool Pattern** - Agents can be used as tools for delegation
- **Session Management** - Track customer state across interactions
- **Tool Integration** - Agents with domain-specific tools

## Prerequisites

- Java 17+
- Maven 3.6+
- OpenAI API key

## Running the Sample

### Option 1: Direct Run

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/multi-agent

# Run the sample
./run.sh
# Or: mvn compile exec:java
```

### Option 2: With Genkit Dev UI

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/multi-agent

# Run with Genkit CLI
genkit start -- ./run.sh
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Customer Request                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Triage Agent                            │
│  Routes requests to specialized agents based on intent       │
└─────────────────────────────────────────────────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Reservation     │ │ Menu            │ │ Order           │
│ Agent           │ │ Agent           │ │ Agent           │
│                 │ │                 │ │                 │
│ • makeRes       │ │ • getMenu       │ │ • placeOrder    │
│ • cancelRes     │ │ • getDietInfo   │ │ • getOrderStatus│
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Agents

### Triage Agent
The main entry point that analyzes customer requests and routes them to the appropriate specialized agent.

### Reservation Agent
Handles table reservations:
- Make new reservations
- Cancel existing reservations
- Check availability

### Menu Agent
Handles menu-related queries:
- Get menu items
- Dietary information
- Recommendations

### Order Agent
Handles food orders:
- Place orders
- Check order status
- Modify orders

## Available Tools

| Tool | Agent | Description |
|------|-------|-------------|
| `makeReservation` | Reservation | Makes a new reservation |
| `cancelReservation` | Reservation | Cancels an existing reservation |
| `getMenu` | Menu | Returns menu items |
| `placeOrder` | Order | Places a food order |

## Example Interactions

The sample runs as an interactive CLI application:

```
🍽️  Welcome to the Restaurant!
Type 'quit' to exit.

You: I'd like to make a reservation for 4 people tomorrow at 7pm

Agent: I'd be happy to help you with your reservation. Let me set that up for you.

[Reservation Agent handles the request]

Reservation confirmed! Your confirmation number is RES-1234.
- Date: 2024-01-16
- Time: 19:00
- Party size: 4

You: What's on the menu?

Agent: [Menu Agent handles the request]

Here's our current menu:
- Appetizers: ...
- Main Courses: ...
- Desserts: ...
```

## Session State

The sample tracks customer state across interactions:

```java
public class CustomerState {
    private String customerId;
    private String currentAgent;
    private List<String> reservations;
    private List<String> orders;
}
```

## Code Highlights

### Defining an Agent

```java
Agent reservationAgent = genkit.defineAgent(
    AgentConfig.builder()
        .name("reservationAgent")
        .model("openai/gpt-4o")
        .system("You are a helpful reservation agent for a restaurant...")
        .tools(List.of(makeReservationTool, cancelReservationTool))
        .build());
```

### Agent-as-Tool Pattern

```java
// Agents can be used as tools for delegation
Tool<String, String> reservationAgentTool = reservationAgent.asTool();

Agent triageAgent = genkit.defineAgent(
    AgentConfig.builder()
        .name("triageAgent")
        .model("openai/gpt-4o")
        .system("Route requests to the appropriate agent...")
        .tools(List.of(reservationAgentTool, menuAgentTool, orderAgentTool))
        .build());
```

### Session-Based Chat

```java
Session<CustomerState> session = genkit.createSession(
    SessionOptions.<CustomerState>builder()
        .sessionStore(sessionStore)
        .initialState(new CustomerState())
        .build());

Chat chat = session.chat(ChatOptions.builder()
    .model("openai/gpt-4o")
    .agent(triageAgent)
    .build());

String response = chat.send("I'd like to make a reservation");
```

## Development UI

When running with `genkit start`, access the Dev UI at http://localhost:4000 to:

- View registered agents and tools
- Test individual agents
- Inspect traces showing agent routing
- View tool calls and responses

## See Also

- [Genkit Java README](../../README.md)
- [Chat Sessions Sample](../chat-session/README.md)
- [Interrupts Sample](../interrupts/README.md)
