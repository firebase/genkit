# Building multi-agent systems

A powerful application of large language models are LLM-powered agents. An agent
is a system that can carry out complex tasks by planning how to break tasks into
smaller ones, and (with the help of [tool calling](tool-calling)) execute tasks
that interact with external resources such as databases or even physical
devices.

Here are some excerpts from a very simple customer service agent built using a
single prompt and several tools:

```ts
const menuLookupTool = ai.defineTool(
  {
    name: 'menuLookupTool',
    description: 'use this tool to look up the menu for a given date',
    inputSchema: z.object({
      date: z.string().describe('the date to look up the menu for'),
    }),
    outputSchema: z.string().describe('the menu for a given date'),
  },
  async (input): Promise<string> => {
    // Retrieve the menu from a database, website, etc.
  }
);

const reservationTool = ai.defineTool(
  {
    name: 'reservationTool',
    description: 'use this tool to try to book a reservation',
    inputSchema: z.object({
      partySize: z.coerce.number().describe('the number of guests'),
      date: z.string().describe('the date to book for'),
    }),
    outputSchema: z
      .string()
      .describe(
        "true if the reservation was successfully booked and false if there's" +
        " no table available for the requested time"
      ),
  },
  async (input): Promise<string> => {
    // Access your database to try to make the reservation.
  }
);

const chat = ai.chat({
  model: gemini15Pro,
  system:
    "You are an AI customer service agent for Pavel's Cafe. Use the tools " +
    'available to you to help the customer. If you cannot help the ' +
    'customer with the available tools, politely explain so.',
  tools: [menuLookupTool, reservationTool],
});
```

A simple architecture like the one shown above can be sufficient when your agent
only has a few capabilities. However, even for the limited example above, you
can see that there are some capabilities that customers would likely expect: for
example, listing the customer's current reservations, canceling a reservation,
and so on. As you build more and more tools to implement these additional
capabilities, you start to run into some problems:

*   The more tools you add, the more you stretch the model's ability to
    consistently and correctly employ the right tool for the job.
*   Some tasks might best be served through a more focused back and forth
    between the user and the agent, rather than by a single tool call.
*   Some tasks might benefit from a specialized prompt. For example, if your
    agent is responding to an unhappy customer, you might want its tone to be
    more business-like, whereas the agent that greets the customer initially can
    have a more friendly and lighthearted tone.

One approach you can use to deal with these issues that arise when building
complex agents is to create many specialized agents and use a general purpose
agent to delegate tasks to them. Genkit supports this architecture by allowing
you to specify prompts as tools. Each prompt represents a single specialized
agent, with its own set of tools available to it, and those agents are in turn
available as tools to your single orchestration agent, which is the primary
interface with the user.

Here's what an expanded version of the previous example might look like as a
multi-agent system:

```ts
// Define a prompt that represents a specialist agent
const reservationAgent = ai.definePrompt(
  {
    name: 'reservationAgent',
    description: 'Reservation Agent can help manage guest reservations',
    tools: [reservationTool, reservationCancelationTool, reservationListTool],
  },
  '{{role "system"}} Help guests make and manage reservations'
);

// Or load agents from .prompt files
const menuInfoAgent = ai.prompt("menuInfoAgent");
const complaintAgent = ai.prompt("complaintAgent");

// The triage agent is the agent that users interact with initially 
const triageAgent = ai.definePrompt(
  {
    name: 'triageAgent',
    description: 'Triage Agent',
    tools: [reservationAgent, menuInfoAgent, complaintAgent],
  },
  `{{role "system"}} You are an AI customer service agent for Pavel's Cafe.
  Greet the user and ask them how you can help. If appropriate, transfer to an
  agent that can better handle the request. If you cannot help the customer with
  the available tools, politely explain so.`
);

// Start a chat session, initially with the triage agent
const chat = ai.chat({ prompt: triageAgent });
```
