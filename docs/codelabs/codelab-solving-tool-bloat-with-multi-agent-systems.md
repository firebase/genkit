# Solving Tool Bloat with a Multi-Agent Architecture in Genkit

As you build systems that rely more and more on LLMs, you might find more and more requirements that require LLMs to interact with the outside world. The primary way that agents do this today is with tool calling.

Initially, you might attach a few tools directly to a single agent. But as you scale beyond a handful (say 3-5 tools), challenges emerge:

- **Tool Overload**: With dozens of tools, the agent struggles to decide which to use.
- **Context Bloat**: Each tool adds prompt length, leading to higher costs and latency. Tools are particularly expensive because you need to describe the expected input as JSON schema, which can require many tokens.
- **Prompt Complexity**: A large toolset can confuse the model and degrade reliability.

**The Solution**: Adopt a multi-agent architecture with a routing agent. Instead of giving one agent 50 tools, you create multiple specialized agents—each focusing on a particular domain, like attendance, grades, or scheduling. Each specialized agent has just a few tools. A central routing agent then directs queries to the right specialized agent. This:

- **Reduces Complexity**: The routing agent decides which agent to consult, not which individual tool among many.
- **Improves Performance**: Specialized agents have fewer tools, making it easier for the model to pick the correct one.
- **Scales Cleanly**: Adding new capabilities just means adding a new specialized agent and referencing it in the routing agent.
- **Manages Context**: By isolating tool schemas to specialized agents, you reduce prompt token usage.

In this codelab, you’ll build a simple school assistant system with a routing agent and specialized agents for attendance and grades. You’ll learn how to structure the architecture, create specialized agents, and route queries effectively.

**Time**: ~45 minutes

**What You'll Learn**:
- How to structure a multi-agent system to avoid tool bloat
- How to create specialized agents with limited toolsets
- How to implement a routing agent that delegates tasks
- Best practices for scaling and agent communication

---

## Prerequisites

- npm
- [Google AI API key](https://makersuite.google.com/app/apikey)
- Basic TypeScript knowledge

---

## Step 1: Project Setup

Create and enter a new project directory:

```bash
mkdir school-agent
cd school-agent
```

Install required dependencies:

```bash
npm install genkit @genkit-ai/googleai
```

Export your API key:

```bash
export GOOGLE_GENAI_API_KEY=your_api_key_here
```

## Step 2: Initialize Genkit

Create `src/genkit.ts`:

```typescript
import { gemini15Pro, googleAI } from '@genkit-ai/googleai';
import { genkit } from 'genkit';

export const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Pro,
});
```

## Step 2a: Define a Helper Function

We’ll define a userContext helper that formats user and student info. This is a convenient way to ensure each agent sees consistent context.

Add this to `src/genkit.ts` (below the existing code):

```typescript
import { AgentState } from './types';

ai.defineHelper(
  'userContext',
  (state: AgentState) => `=== User Context

- The current parent user is ${state?.parentName}
- The current date and time is: ${new Date().toString()}

=== Registered students of the current user

${state?.students.map((s) => ` - ${s.name}, student id: ${s.id} grade: ${s.grade}, activities: \n${s.activities.map((a) => `   - ${a}`).join('\n')}`).join('\n\n')}`
);
```

## Step 3: Define Types

Create `src/types.ts`:

```typescript
export interface AgentState {
  parentId: number;
  parentName: string;
  students: {
    id: number;
    name: string;
    grade: number;
    activities: string[];
  }[];
}
```

## STEP 4: Create Tools

Tools are functions the agents can call to perform actions. Let’s define a few attendance and grade tools.

Create `src/tools.ts`:

```typescript
import { ai, z } from './genkit';
import { AgentState } from './types';

// Check that the requested student belongs to the current parent
function checkIsParent(studentId: number, state: AgentState) {
  const student = state.students.find((s) => s.id === studentId);
  if (!student) {
    throw new Error('Parents can only access their registered children');
  }
  return student;
}

// Attendance Tools
export const reportAbsence = ai.defineTool(
  {
    name: 'reportAbsence',
    description: 'Report a student absence',
    inputSchema: z.object({
      studentId: z.number(),
      date: z.string(),
      reason: z.string(),
      excused: z.boolean(),
    }),
  },
  async (input) => {
    const student = checkIsParent(
      input.studentId,
      ai.currentSession<AgentState>().state!
    );
    console.log(`[TOOL] Absence reported for ${student.name}`);
    return { success: true };
  }
);

// Grades Tools
export const getGrades = ai.defineTool(
  {
    name: 'getGrades',
    description: 'Retrieve student grades',
    inputSchema: z.object({
      studentId: z.number(),
      subject: z.string().optional(),
    }),
  },
  async ({ studentId, subject }) => {
    const student = checkIsParent(
      studentId,
      ai.currentSession<AgentState>().state!
    );
    return [
      { subject: 'Math', grade: 'A-' },
      { subject: 'English', grade: 'B+' },
      { subject: 'Science', grade: 'A' },
    ].filter(g => !subject || g.subject === subject);
  }
);
```

## STEP 5: Create Specialized Agents

Each specialized agent focuses on one domain. We’ll create an `attendanceAgent` and a `gradesAgent`.

### Attendance Agent

Create `src/attendanceAgent.ts`:

```typescript
import { ai } from './genkit';
import { reportAbsence } from './tools';

export const attendanceAgent = ai.definePrompt(
  {
    name: 'attendanceAgent',
    description: 'Handles student attendance and absence reporting',
    tools: [reportAbsence, 'routingAgent'],
  },
  `You are a helpful attendance assistant for Sparkyville High School.
   
   Guidelines:
   - Help parents report absences for their students
   - Only handle attendance-related queries
   - Verify student belongs to parent before taking action
   - Get all necessary details before reporting absence

   {{ userContext @state }}`
);
```

### Grades Agent
Create `src/gradesAgent.ts`:

```typescript
import { ai } from './genkit';
import { getGrades } from './tools';

export const gradesAgent = ai.definePrompt(
  {
    name: 'gradesAgent',
    description: 'Handles grade-related inquiries',
    tools: [getGrades, 'routingAgent'],
  },
  `You are a helpful academic assistant for Sparkyville High School.
   
   Guidelines:
   - Help parents check their students' grades
   - Only handle grade-related queries
   - Verify student belongs to parent before sharing grades
   - Be encouraging and positive when discussing grades

   {{ userContext @state }}`
);
```

Note: We reference `routingAgent` by name to avoid circular imports. We’ll define routingAgent next.

## STEP 6: Create the Routing Agent

The routing agent is the first point of contact. It routes queries to the appropriate specialized agent or answers general queries directly.

Create `src/routingAgent.ts`:

```typescript
import { ai } from './genkit';
import { attendanceAgent } from './attendanceAgent';
import { gradesAgent } from './gradesAgent';

export const routingAgent = ai.definePrompt(
  {
    name: 'routingAgent',
    description: 'Main entry point for parent inquiries',
    tools: [attendanceAgent, gradesAgent],
  },
  `You are Bell, a helpful assistant for Sparkyville High School parents.
   
   Your responsibilities:
   1. Route queries to specialized agents:
      - Attendance agent for absences and attendance
      - Grades agent for academic performance
   2. Answer general questions directly
   3. Maintain a friendly, helpful demeanor

   School Information:
   - Classes begin at 8am
   - Students are dismissed at 3:30pm
   - Lunch period is 12:00-12:45pm

   {{ userContext @state }}`
);
```
The routing agent can either handle the request or delegate it to a specialized agent. By doing this, we avoid tool overload in a single prompt.

## STEP 7: Create the Chat Interface

We’ll build a simple CLI for testing. The chat will always start with the routing agent.

Create `src/chat.ts`:

```typescript
import { createInterface } from 'node:readline';
import { ai } from './genkit';
import { routingAgent } from './routingAgent';

const rl = createInterface({
  input: process.stdin,
  output: process.stdout,
});

// Sample user context
const userContext = {
  parentId: 4112,
  parentName: 'Francis Smith',
  students: [
    {
      id: 3734,
      name: 'Evelyn Smith',
      grade: 9,
      activities: ['Choir', 'Drama Club'],
    },
    {
      id: 9433,
      name: 'Evan Smith',
      grade: 11,
      activities: ['Chess Club'],
    },
  ],
};

async function main() {
  // Create a chat session with the routing agent
  const chat = ai
    .createSession({ initialState: userContext })
    .chat(routingAgent);

  console.log('\nWelcome to Sparkyville High School Assistant!');
  console.log('\nTry these queries:');
  console.log('- "I need to report my child absent tomorrow"');
  console.log('- "What are Evelyn\'s current grades?"');
  console.log('- "What time does school start?"\n');

  // Chat loop
  while (true) {
    const input = await new Promise(resolve => 
      rl.question('> ', resolve)
    );
    const { text } = await chat.send(input as string);
    console.log('\nBell:', text, '\n');
  }
}

main().catch(console.error);
```

## STEP 8: Run your Multi-Agent System

Add this script to `package.json`:

```json
{
  "scripts": {
    "start": "tsx src/chat.ts"
  }
}
```

Run the application:
```bash
npm start
```

# Testing Your System

Asking for General Information:
```
> What time does school start?
> When is lunch period?
```

Attendance Reporting:
```
> I need to report Evelyn absent tomorrow
> My child will be late to school
```

Grade Queries:
```
> What are Evelyn's current grades?
> How is Evan doing in Math?
```

Error Handling
```
> Show me grades for another student
> Report someone else's child absent
```

# How It Works

1. The routing agent receives all queries.
2. If it’s a general question (e.g., school times), it answers directly.
3. If it’s about attendance, it calls the `attendanceAgent`.
4. If it’s about grades, it calls the `gradesAgent`.

This isolates complexity. Each specialized agent sees only a small subset of tools relevant to its domain, making it easier for the model to pick the right action. The routing agent only decides *which agent* to use, not which specific tool among a massive list.

The delegation is done through tool calls in Genkit. When you define a prompt using `ai.definePrompt()`, Genkit allows you to use that prompt as a tool in other agents. Let's annotate a simple example to make sure everything is crystal clear:

```typescript
// 1. Define a specialized agent
export const gradesAgent = ai.definePrompt(
  {
    name: 'gradesAgent',
    description: 'Handles grade-related inquiries',
    tools: [getGrades, 'routingAgent'], // Specialized tools
  },
  `You are a helpful academic assistant...`
);

// 2. Use it as a tool in the routing agent
export const routingAgent = ai.definePrompt(
  {
    name: 'routingAgent',
    tools: [gradesAgent], // The grades agent becomes a tool
  },
  `You are Bell...`
);
```

When the routing agent makes a tool call to a specialized agent:
1. The conversation history is preserved
2. The system prompt is swapped
3. Available tools are changed
4. The same model executes with the new configuration

### Example Flow

Let's trace a query through the system:

```typescript
// 1. User asks: "What are Evelyn's grades in Math?"

// 2. Routing agent recognizes this as a grades query
{
  name: "gradesAgent",
  input: "What are Evelyn's grades in Math?"
}

// 3. Grades agent activates with:
// - Same conversation history
// - New system prompt
// - Access to grades tools
// - Same model (gemini15Pro)

// 4. Grades agent uses its specialized tool
{
  name: "getGrades",
  input: { 
    studentId: 3734,
    subject: "Math"
  }
}

// 5. Tool returns grade data
{
  subject: "Math",
  grade: "A-"
}

// 6. Grades agent processes result and responds
"Evelyn is doing great in Math! She currently has an A-."

## Agent Specialization

### Tool Isolation

Each agent has access only to relevant tools:

```typescript
// Attendance agent tools
tools: [reportAbsence, reportTardy]

// Grades agent tools
tools: [getGrades, getTranscript]

// Routing agent tools
tools: [attendanceAgent, gradesAgent]
```