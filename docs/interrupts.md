# Interrupts

_Interrupts_ are a special kind of [tool](tool-calling) that can pause the
LLM generation and tool calling loop to return control back to you. When
you're ready, generation can then be *resumed* with *replies* that will be
processed by the LLM for further generation.

The most common uses for interruptions fall into a few categories:

*  **Human-in-the-Loop:** Allowing the user of an interactive AI application
   to clarify needed informatino or confirm the LLM's action before it is
   completed, providing a measure of safety and confidence.
*  **Async Processing:** Starting an asynchronous task that can only be
   completed out-of-band, such as sending an approval notification to
   a human reviewer or kicking off a long-running background process.
*  **Exiting Autonomous Task:** In workflows that might iterate through
   a long series of tool calls, an interrupt can provide the model a way
   to mark the task as complete.

## Before you begin {:#you-begin}

If you want to run the code examples on this page, first complete the steps in
the [Getting started](get-started) guide. All of the examples assume that you
have already set up a project with Genkit dependencies installed.

This page discusses one of the advanced features of Genkit model abstraction, so
before you dive too deeply, you should be familiar with the content on the
[Generating content with AI models](models) page. You should also be familiar
with Genkit's system for defining input and output schemas, which is discussed
on the [Flows](flows) page and the general methods of tool calling discussed
on the [Tool Calling](tool-calling) page.

## Overview of interrupts {:#overview-interrupts}

At a high level, this is what an interrupt looks like when interacting with an LLM:

1. The calling application prompts the LLM with a request and also includes in
   the prompt a list of tools including at least one interrupt tool that the LLM
   can use to generate a response.
2. The LLM either generates a complete response or generates a tool call request
   in a specific format. To the LLM, an interrupt looks like any other tool call.
3. If the LLM selects the interrupt among the tool calls it generates, the Genkit
   library will automatically halt generation rather than immediately passing
   responses back to the model for additional processing.
4. The developer checks if an interrupt is called and  performs whatever task is
   needed to collect the information needed for the interrupt reply.
5. The developer resumes generation by passing an interrupt reply to the model,
   returning to Step 2.

## Triggering interrupts with Genkit {:#tool-calling}

Interrupts can be triggered from any tool or by using the `defineInterrupt` method.

### Defining interrupts

The most common kind of interrupt is providing a tool that allows the LLM to 
request clarification from the user, for example by asking a multiple choice
question.

For this use case, use the Genkit instance's `defineInterrupt()` method:

```ts
import { genkit, z } from 'genkit';
import { googleAI, gemini15Flash } from '@genkitai/google-ai';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

const askQuestion = ai.defineInterrupt({
  name: 'askQuestion',
  description: 'use this to ask the user a clarifying question',
  inputSchema: z.object({
    choices: z.array(z.string()).describe('the choices to display to the user'),
    allowOther: z.boolean().optional().describe('when true, allow write-ins')
  }),
  replySchema: z.string()
});
```

Note that interrupts have a `replySchema` instead of an output schema, although
they are treated as equivalent when passing data to the model.

### Using interrupts

Interrupts are passed into the `tools` array when generating content, just like
other types of tools. You can pass both normal tools and interrupts to the same
generate call:

*   {Generate}

    ```ts
    const response = await ai.generate({
      prompt: 'Ask me a movie trivia question.',
      tools: [askQuestion],
    });
    ```

*   {definePrompt}

    ```ts
    const triviaPrompt = ai.definePrompt(
      {
        name: 'triviaPrompt',
        tools: [askQuestion],
        input: {
          schema: z.object({subject: z.string()})
        },
        prompt: 'Ask me a trivia question about {{subject}}.',
      }
    );

    const response = await triviaPrompt({ subject: 'computer history' });
    ```

*   {Prompt file}

    ```none
    ---
    tools: [askQuestion]
    input:
      schema:
        partyType: string
    ---
    {{role "system}}
    Use the askQuestion tool if you need to clarify something.

    {{role "user"}}
    Help me plan a {{partyType}} party next week.
    ```

    Then you can execute the prompt in your code as follows:

    ```ts
    // assuming prompt file is named partyPlanner.prompt
    const partyPlanner = ai.prompt('partyPlanner');

    const response = await partyPlanner({ partyType: 'birthday' });
    ```

*   {Chat}

    ```ts
    const chat = ai.chat({
      system: 'Use the askQuestion tool if you need to clarify something.',
      tools: [askQuestion],
    });

    const response = await chat.send('make a plan for my birthday party');
    ```

Genkit will immediately return a response once an interrupt tool is triggered.

### Replying to interrupts

If you've passed one or more interrupt tools to your generate call, you will
need to check the response for interrupts so that you can handle them:

```ts
// you can check the 'finishReason' of the response
response.finishReason === 'interrupted'
// or you can check to see if any interrupt requests are on the response
response.interrupts.length > 0
```

Replying to an interrupt is done using the `resume` option on a subsequent
generate call, making sure to pass in the existing history. Each tool has
a `.reply()` method on it to help construct the reply.

Once resumed, the model will re-enter the generation loop including tool
execution until it either completes or another interrupt is triggered:

```ts
let response = await ai.generate({
  tools: [askQuestion],
  system: 'ask clarifying questions until you have a complete solution',
  prompt: 'help me plan a backyard BBQ',
});

while (response.interrupts.length) {
  const answers = [];
  // multiple interrupts can be called at once, so we handle them all
  for (const question in response.interrupts) {
    answers.push(
      // use the 'reply' method on our tool to populate answers
      askQuestion.reply(
        question,
        // send the tool request input to the user to respond
        await askUser(question.toolRequest.input)
      )
    );
  }

  response = await ai.generate({
    tools: [askQuestion],
    messages: response.messages,
    resume: {
      reply: answers
    }
  })
}

// no more interrupts, we can see the final response
console.log(response.text);
```