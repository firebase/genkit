# Tool interrupts

_Interrupts_ are a special kind of [tool](./tools.md) that can pause the
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

## Before you begin

All of the examples documented here assume that you have already set up a
project with Genkit dependencies installed. If you want to run the code
examples on this page, first complete the steps in the
[Get started](../get-started.md) guide.

Before diving too deeply, you should also be familiar with the following
concepts:

* [Generating content](./models.md) with AI models.
* Genkit's system for [defining input and output schemas](./flows.md).
* General methods of [tool-calling](./tools.md).

## Overview of interrupts

At a high level, this is what an interrupt looks like when
interacting with an LLM:

1. The calling application prompts the LLM with a request. The prompt includes
   a list of tools, including at least one for an interrupt that the LLM
   can use to generate a response.
2. The LLM either generates either a complete response or a tool call request
   in a specific format. To the LLM, an interrupt call looks like any
   other tool call.
3. If the LLM calls an interrupting tool,
   the Genkit library automatically pauses generation rather than immediately
   passing responses back to the model for additional processing.
4. The developer checks whether an interrupt call is made, and performs whatever
   task is needed to collect the information needed for the interrupt response.
5. The developer resumes generation by passing an interrupt response to the
   model. This action triggers a return to Step 2.

## Define manual-response interrupts

The most common kind of interrupt allows the LLM to request clarification from
the user, for example by asking a multiple-choice question.

For this use case, use the Genkit instance's `tool()` decorator:

```py
class Questions(BaseModel):
    choices: list[str] = Field(description='the choices to display to the user')
    allow_other: bool = Field(description='when true, allow write-ins')


@ai.tool()
def ask_question(input: Questions, ctx) -> str:
    """Use this to ask the user a clarifying question"""
    ctx.interrupt()
```

Note that the `outputSchema` of an interrupt corresponds to the response data
you will provide as opposed to something that will be automatically populated
by a tool function.

### Use interrupts

Interrupts are passed into the `tools` array when generating content, just like
other types of tools. You can pass both normal tools and interrupts to the
same `generate` call:

```py
interrupted_response = await ai.generate(
    prompt='Ask me a movie trivia question.',
    tools=['ask_question'],
)
```

Genkit immediately returns a response on receipt of an interrupt tool call.

### Respond to interrupts

If you've passed one or more interrupts to your generate call, you
need to check the response for interrupts so that you can handle them:

```py
// you can check the 'finishReason' of the response
interrupted_response.finishReason === 'interrupted'
// or you can check to see if any interrupt requests are on the response
len(interrupted_response.interrupts) > 0
```

Responding to an interrupt is done using the `tool_responses` option on a subsequent
`generate` call, making sure to pass in the existing history. There's a `tool_response`
helper function to help you constract the response.

Once resumed, the model re-enters the generation loop, including tool
execution, until either it completes or another interrupt is triggered:

```py
response = await ai.generate(
    messages=interrupted_response.messages,
    tool_responses=[tool_response(interrupted_response.interrupts[0], 'b')],
    tools=['ask_question'],
)
```
