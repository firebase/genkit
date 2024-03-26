# Durable flows (experimental)

Important: This feature is experimental, and subject to change or removal.

Durable flows (also called schedulable flows and persisted flows) are an
advanced feature that allows interrupting and resuming flow execution, as well
as scheduling executions. Schedulable flows don't support streaming, because
they are specifically designed for long-running background operations.

Here's an example:

```js
import { onScheduledFlow } from '@genkit-ai/plugin-firebase/functions/experimental';

export const jokeFlow = onScheduledFlow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
  async (subject) => {
    // ....
  }
);
```

To enable this durable behaviour, Genkit persists flow states in a flow state
store, which can be implemented by plugins.

You can use `configureGenkit()` to specify which persistence implementation to
use when running on a non-dev environment (when running locally during
development, Genkit uses local files to persist state):

```js
configureGenkit({
  plugins: [firebase({ projectId: getProjectId() })],
  flowStateStore: 'firebase',
  //...
});
```

### Scheduled invocation

The following example schedules a flow to be run at a later time. In this case,
the later time is almost immediately, but it's still guaranteed to be invoked
asynchronously by the scheduler.

```js
const operation = await scheduleFlow(jokeFlow, 'banana');
```

It is guaranteed that the returned operation won't be complete (`done=false`)
and you will have to use some kind of polling to wait for the flow to complete.

You can also schedule the flow to run with a delay (specified in seconds).

```js
const operation = await scheduleFlow(jokeFlow, 'banana', 10);
```

## Steps

Steps of a flow are wrapper functions that each offer specific capabilities;
universally, all steps have built-in memoization -- results of running each step
are memoized and if the step is executed again, it immediately returns the
memoized value. Universal memoization is a core feature because each flow
instance can run more than once for the following reasons:

- Flows are built on top of cloud task queues, which offer only a "deliver at
  least once" guarantee
- Some features (see below: interrupt, sleep, waitFor or various error retry
  feature) rely on the ability of the flow to be "interrupted" and then re-run
  again.

All logic that has side-effects or is expensive to perform must be defined as a
step within a flow to avoid unnecessary or undesirable repeated execution.

### run

This is the simplest way to define a step. Step has a name and function.
Memoization uses the run step name as a key.

```js
export const myFlow = onScheduledFlow(
  { name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const output = await run('step-name', async () => {
      return await doSomething(input);
    });
    return output;
  }
);
```

It's allowed (although not recommended) to use the same name more than once:

```javascript
export const myFlow = onScheduledFlow(
  { name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const output1 = await run('same-name', async () => {
      return await doSomething1(input);
    });
    const output2 = await run('same-name', async () => {
      return await doSomething2(input);
    });

    return output1 + output2;
  }
);
```

Retry behavior can be specified in the run step. In case of an error thrown
within the step function, the framework can retry executing the step as per the
provided retry configuration. By default, there's no retry -- if an error
occurs, the whole flow execution will result in an error.

```js
export const myFlow = onScheduledFlow(
  { name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const output = await run(
      {
        name: 'step-name',
        retryConfig: {
          maxAttempts: 3,
          minBackoffSeconds: 10,
        },
      },
      async () => {
        return await doSomething(input);
      }
    );
    return output;
  }
);
```

### runAction

An action is a self-describing function. It exposes metadata (self-describing):
name, description and input/output `zod` schema. `Action` is a shared type
across the Genkit framework: many AI primitives are implemented as actions.

You can build action factories with the `action()` helper:

```js
const greet = (greeting) =>
  action(
    { name: 'greet', input: z.string(), output: z.string() },
    async (name) => {
      return `${greeting}, ${name}!`;
    }
  );
```

`runAction()` is a wrapper around a `run` step that makes it easier to work with
actions. Because actions already have all the necessary metadata, it can be
omitted during step definition.

```javascript
export const greetingFlow = onScheduledFlow(
  { name: 'greetingFlow', input: z.string(), output: z.string() },
  async (name) => {
    const frenchGreeting = greet('Bonjour');
    const greeting = await runAction(frenchGreeting, name);

    return greeting;
  }
);
```

You can configure retry behavior for `runAction` in the same way as for `run`.

### interrupt

Use `interrupt` steps to interrupt the flow and request external input.

```js
export const myFlow = onScheduledFlow(
  { name: 'myFlow', input: z.void(), output: z.boolean() },
  async () => {
    const hoomanSaid = await interrupt(
      'approve-by-hooman',
      z.object({ approved: z.boolean() })
    );

    return hoomanSaid.approved;
  }
);

// Resume the interrupted flow
import { resumeFlow } from '@genkit-ai/flow/experimental';
await resumeFlow(myFlow, flowId, {
  approve: false,
});
```

`interrupt` will "interrupt" the flow by throwing an `InterruptError`, so you
need to be careful to rethrow the error when wrapping the `interrupt` step in
`try`-`catch`.

```js
import { InterruptError } from '@genkit-ai/flow/experimental';

export const myFlow = onScheduledFlow(
  { name: 'myFlow', input: z.void(), output: z.boolean() },
  async () => {
    var hoomanSaid;
    try {
      hoomanSaid = await interrupt(
        'approve-by-hooman',
        z.object({ approved: z.boolean() })
      );
    } catch (e) {
      // Must rethrow
      if (e instanceof InterruptError) {
        throw e;
      }
      // Handle other errors
    }

    return hoomanSaid.approved;
  }
);
```

### sleep

Use the `sleep()` method to interrupt a flow and automatically resume it after a
specified number of seconds.

```js
export const myFlow = onScheduledFlow({ name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const something = await run("do-something", async () => {...});

    await sleep("wait-a-few-hours", 60 * 60 * 2);

    const somethingElse = await run("do-something-else", async () => {...});

    return output;
  }
)
```

`sleep` interrupts the flow by throwing an `InterruptError`, so you need to be
careful to rethrow the error when wrapping the `sleep` step in `try`-`catch`.

### poll

Important: Not fully implemented yet; for reference only.

Basic polling. Periodically invokes the provided function until it returns
`true`.

```js
export const myFlow = onScheduledFlow({ name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const workId = await run("start-something",
      async () => startSomething(input));

    await poll({
      name: "wait-for-something-to-complete",
      pollPeriodSeconds: 10,
      backoff: ...
    }, async () => isThatSomethingElseComplete(workId))

    return await run("do-something-else", async () => {...});
  }
)
```

`poll` interrupts the flow by throwing an `InterruptError`, so you need to be
careful to rethrow the error when wrapping the `poll` step in `try`-`catch`.

Polling is done by reenqueuing the task in the queue (as per the polling
configuration) and `poll` will continue interrupting execution until the
function returns `true`.

### waitFor

`waitFor` is a convenient version of `poll` that allows waiting for other flows to
complete.

```js
export const myFlow = onScheduledFlow(
  { name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const otherFlowOp = await scheduleFlow(otherFlow, input);

    const [op] = await waitFor('wait-for-other-action', otherFlow, [
      otherFlowOp.name,
    ]);

    return op.result.response;
  }
);
```

## Getting results

Use `getFlowState()` to retrieve a flow's current state:

```javascript
import { runFlow, getFlowState } from '@genkit-ai/flow/experimental';

const operation = await scheduleFlow(jokeFlow, 'banana');
console.log('Operation', operation);
console.log('state', await getFlowState(jokeFlow, operation.name));
```
