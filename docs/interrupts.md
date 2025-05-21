Beta: This feature of Genkit is in **Beta,** which means it is not yet
part of Genkit's stable API. APIs of beta features may change in minor
version releases.

# Pause generation using interrupts

_Interrupts_ are a special kind of [tool](tool-calling) that can pause the
LLM generation-and-tool-calling loop to return control back to you. When
you're ready, you can then *resume* generation by sending *replies* that the LLM
processes for further generation.

The most common uses for interrupts fall into a few categories:

*  **Human-in-the-Loop:** Enabling the user of an interactive AI
   to clarify needed information or confirm the LLM's action
   before it is completed, providing a measure of safety and confidence.
*  **Async Processing:** Starting an asynchronous task that can only be
   completed out-of-band, such as sending an approval notification to
   a human reviewer or kicking off a long-running background process.
*  **Exit from an Autonomous Task:** Providing the model a way
   to mark a task as complete, in a workflow that might iterate through
   a long series of tool calls.

## Before you begin {:#you-begin}

All of the examples documented here assume that you have already set up a
project with Genkit dependencies installed. If you want to run the code
examples on this page, first complete the steps in the
[Get started](get-started) guide.

Before diving too deeply, you should also be familiar with the following
concepts:

* [Generating content](models) with AI models.
* Genkit's system for [defining input and output schemas](flows).
* General methods of [tool-calling](tool-calling).

## Overview of interrupts {:#overview-interrupts}

At a high level, this is what an interrupt looks like when
interacting with an LLM:

1. The calling application prompts the LLM with a request. The prompt includes
   a list of tools, including at least one for an interrupt that the LLM
   can use to generate a response.
2. The LLM either generates either a complete response or a tool call request
   in a specific format. To the LLM, an interrupt call looks like any
   other tool call.
3. If the LLM calls an interrupt tool,
   the Genkit library automatically pauses generation rather than immediately
   passing responses back to the model for additional processing.
4. The developer checks whether an interrupt call is made, and performs whatever
   task is needed to collect the information needed for the interrupt response.
5. The developer resumes generation by passing an interrupt response to the
   model. This action triggers a return to Step 2.

## Define manual-response interrupts {:#manual-response}

The most common kind of interrupt allows the LLM to request clarification from
the user, for example by asking a multiple-choice question.

For this use case, use the Genkit instance's `defineInterrupt()` method:

```ts
import { genkit, z } from 'genkit';
import { googleAI, gemini15Flash } from '@genkit-ai/googleai';

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
  outputSchema: z.string()
});
```

Note that the `outputSchema` of an interrupt corresponds to the response data
you will provide as opposed to something that will be automatically populated
by a tool function.

### Use interrupts

Interrupts are passed into the `tools` array when generating content, just like
other types of tools. You can pass both normal tools and interrupts to the
same `generate` call:

*   {generate}

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
        prompt: 'Ask me a trivia question about {% verbatim %}{{subject}}{% endverbatim %}.',
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
    {% verbatim %}{{role "system"}}{% endverbatim %}
    Use the askQuestion tool if you need to clarify something.

    {% verbatim %}{{role "user"}}{% endverbatim %}
    Help me plan a {% verbatim %}{{partyType}}{% endverbatim %} party next week.
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

Genkit immediately returns a response on receipt of an interrupt tool call.

### Respond to interrupts

If you've passed one or more interrupts to your generate call, you
need to check the response for interrupts so that you can handle them:

```ts
// you can check the 'finishReason' of the response
response.finishReason === 'interrupted'
// or you can check to see if any interrupt requests are on the response
response.interrupts.length > 0
```

Responding to an interrupt is done using the `resume` option on a subsequent
`generate` call, making sure to pass in the existing history. Each tool has
a `.respond()` method on it to help construct the response.

Once resumed, the model re-enters the generation loop, including tool
execution, until either it completes or another interrupt is triggered:

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
      // use the `respond` method on our tool to populate answers
      askQuestion.respond(
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
      respond: answers
    }
  })
}

// no more interrupts, we can see the final response
console.log(response.text);
```

## Tools with restartable interrupts {:#restartable-interrupts}

Another common pattern for interrupts is the need to *confirm* an action that
the LLM suggests before actually performing it. For example, a payments app
might want the user to confirm certain kinds of transfers.

For this use case, you can use the standard `defineTool` method to add custom
logic around when to trigger an interrupt, and what to do when an interrupt is
*restarted* with additional metadata.

### Define a restartable tool

Every tool has access to two special helpers in the second argument of its
implementation definition:

- `interrupt`: when called, this method throws a special kind of exception that
  is caught to pause the generation loop. You can provide additional metadata
  as an object.
- `resumed`: when a request from an interrupted generation is restarted using
  the `{resume: {restart: ...}}` option (see below), this helper contains the
  metadata provided when restarting.

If you were building a payments app, for example, you might want to confirm with
the user before making a transfer exceeding a certain amount:

```ts
const transferMoney = ai.defineTool({
  name: 'transferMoney',
  description: 'Transfers money between accounts.',
  inputSchema: z.object({
    toAccountId: z.string().describe('the account id of the transfer destination'),
    amount: z.number().describe('the amount in integer cents (100 = $1.00)'),
  }),
  outputSchema: z.object({
    status: z.string().describe('the outcome of the transfer'),
    message: z.string().optional(),
  })
}, async (input, {context, interrupt, resumed})) {
  // if the user rejected the transaction
  if (resumed?.status === "REJECTED") {
    return {status: 'REJECTED', message: 'The user rejected the transaction.'};
  }
  // trigger an interrupt to confirm if amount > $100
  if (resumed?.status !== "APPROVED" && input.amount > 10000) {
    interrupt({
      message: "Please confirm sending an amount > $100.",
    });
  }
  // complete the transaction if not interrupted
  return doTransfer(input);
}
```

In this example, on first execution (when `resumed` is undefined), the tool
checks to see if the amount exceeds $100, and triggers an interrupt if so. On
second execution, it looks for a status in the new metadata provided and
performs the transfer or returns a rejection response, depending on whether it
is approved or rejected.

### Restart tools after interruption

Interrupt tools give you full control over:

1. When an initial tool request should trigger an interrupt.
2. When and whether to resume the generation loop.
3. What additional information to provide to the tool when resuming.

In the example shown in the previous section, the application might ask the user
to confirm the interrupted request to make sure the transfer amount is okay:

```ts
let response = await ai.generate({
  tools: [transferMoney],
  prompt: "Transfer $1000 to account ABC123",
});

while (response.interrupts.length) {
  const confirmations = [];
  // multiple interrupts can be called at once, so we handle them all
  for (const interrupt in response.interrupts) {
    confirmations.push(
      // use the 'restart' method on our tool to provide `resumed` metadata
      transferMoney.restart(
        interrupt,
        // send the tool request input to the user to respond. assume that this
        // returns `{status: "APPROVED"}` or `{status: "REJECTED"}`
        await requestConfirmation(interrupt.toolRequest.input);
      )
    );
  }

  response = await ai.generate({
    tools: [transferMoney],
    messages: response.messages,
    resume: {
      restart: confirmations,
    }
  })
}

// no more interrupts, we can see the final response
console.log(response.text);
```
