# Passing information through context

There are different categories of information that a developer working
with an LLM may be handling simultaneously:

- **Input:** Information that is directly relevant to guide the LLM's response
  for a particular call. An example of this is the text that needs to be
  summarized.
- **Generation Context:** Information that is relevant to the LLM, but isn't
  specific to the call. An example of this is the current time or a user's name.
- **Execution Context:** Information that is important to the code surrounding
  the LLM call but not to the LLM itself. An example of this is  a user's
  current auth token.

Genkit provides a consistent `context` object that can propagate generation and
execution context throughout the process. This context is made available to all
actions including [flows](flows), [tools](tool-calling), and
[prompts](dotprompt).

Context is automatically propagated to all actions called within the scope of
execution: Context passed to a flow is made available to prompts executed
within the flow. Context passed to the `generate()` method is available to
tools called within the generation loop.

## Why is context important?

As a best practice, you should provide the minimum amount of information to the
LLM that it needs to complete a task. This is important for multiple reasons:

- The less extraneous information the LLM has, the more likely it is to perform
  well at its task.
- If an LLM needs to pass around information like user or account IDs to tools,
  it can potentially be tricked into leaking information.

Context gives you a side channel of information that can be used by any of your
code but doesn't necessarily have to be sent to the LLM. As an example, it can
allow you to restrict tool queries to the current user's available scope.

## Context structure

Context must be an object, but its properties are yours to decide. In some
situations Genkit automatically populates context. For example, when using
[persistent sessions](chat) the `state` property is automatically added to 
context.

One of the most common uses of context is to store information about the current
user. We recommend adding auth context in the following format:

```js
{
  auth: {
    uid: "...", // the user's unique identifier
    token: {...}, // the decoded claims of a user's id token
    rawToken: "...", // the user's raw encoded id token
    // ...any other fields
  }
}
```

The context object can store any information that you might need to know
somewhere else in the flow of execution.

## Use context in an action

To use context within an action, you can access the context helper
that is automatically supplied to your function definition:

*   {Flow}

    ```ts
    const summarizeHistory = ai.defineFlow({
      name: 'summarizeMessages',
      inputSchema: z.object({friendUid: z.string()}),
      outputSchema: z.string();
    }, async ({friendUid}, {context}) => {
      if (!context.auth?.uid) throw new Error("Must supply auth context.");
      const messages = await listMessagesBetween(friendUid, context.auth.uid);
      const {text} = await ai.generate({
        prompt:
          `Summarize the content of these messages: ${JSON.stringify(messages)}`,
      });
      return text;
    });
    ```

*   {Tool}

    ```ts
    const searchNotes = ai.defineTool({
      name: 'searchNotes',
      description: "search the current user's notes for info",
      inputSchema: z.object({query: z.string()}),
      outputSchmea: z.array(NoteSchema);
    }, async ({query}, {context}) => {
      if (!context.auth?.uid) throw new Error("Must be called by a signed-in user.");
      return searchUserNotes(context.auth.uid, query);
    });
    ```
*   {Prompt file}
    
    When using [Dotprompt templates](dotprompt), context is made available with the
    `@` variable prefix. For example, a context object of
    `{auth: {name: 'Michael'}}` could be accessed in the prompt template like so:

    ```none
    ---
    input:
      schema:
        pirateStyle?: boolean
    ---

    {{#if pirateStyle}}
    Avast, {{@auth.name}}, how be ye today?
    {{else}}
    Hello, {{@auth.name}}, how are you today?
    {{/if}}
    ```

## Provide context at runtime

To provide context to an action, you pass the context object as an option
when calling the action. 

*   {Flows}

    ```ts
    const summarizeHistory = ai.defineFlow(/* ... */);

    const summary = await summarizeHistory(friend.uid, {context: {auth: currentUser}});
    ```

*   {Generation}

    ```ts
    const {text} = await ai.generate({
      prompt: "Find references to ocelots in my notes.",
      // the context will propagate to tool calls
      tools: [searchNotes],
      context: {auth: currentUser},
    });
    ```

*   {Prompts}

    ```ts
    const helloPrompt = ai.prompt('sayHello');
    helloPrompt({pirateStyle: true}, {context: {auth: currentUser}});
    ```

## Context propagation and overrides

By default, when you provide context it is automatically propagated to all
actions called as a result of your original call. If your flow calls other
flows, or your generation calls tools, the same context is provided.

If you wish to override context within an action, you can pass a different
context object to replace the existing one:

```ts
const otherFlow = ai.defineFlow(/* ... */);

const myFlow = ai.defineFlow({
  // ...
}, (input, {context}) => {
  // override the existing context completely
  otherFlow({/*...*/}, {context: {newContext: true}});
  // or selectively override
  otherFlow({/*...*/}, {context: {...context, updatedContext: true}});
}); 
```

When context is replaced, it propagates the same way. In this example,
any actions that `otherFlow` called during its execution would inherit the
overridden context.
