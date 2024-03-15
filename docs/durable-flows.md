
# EXPERIMENTAL: Durable flows

IMPORTANT: this feature is experimental, subject to change and removal.

Schedulable flows (a.k.a. durable flows, persisted flows) are an advanced feature of flow which allows interrupting and resuming flow execution, as well as scheduling executions.
Schedulable flows do not support streaming, because they are specifically designed for long-running background operations.


```javascript
import { onScheduledFlow } from '@genkit-ai/plugin-firebase/functions/experimental';

export const jokeFlow = onScheduledFlow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
  async (subject) => {
    // ....
  }
);
```


To enable that behaviour flow states are persisted in the flow state store which can be implemented by pluging.

You can use the configuration to specify which persistence implementation to use when running on non-dev environment. 

```javascript
configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
  ],
  flowStateStore: 'firebase',
  //...
});
```

### Scheduled invocation

```javascript
const operation = await scheduleFlow(jokeFlow, 'banana');
```

this will schedule the flow to be executed at a later time. In this case the later time is almost immediately, but it still guaranteed to be invoked asynchronously via the scheduler.

It is guaranteed that the returned operation will not be complete (`done=false`) and you will have to use some kind of polling to wait for the flow to complete.

You can schedule the flow to run with a delay (specified in seconds).

```javascript
const operation = await scheduleFlow(jokeFlow, 'banana', 10);
```


## Steps

Steps of a flow are wrapper functions that offer specific functionality but universally all steps have built-in memoization -- results of execution of each step are memoized and if this step is executed again memoized value will be returned immediately. Universal memoization is a core/critical feature because each flow instance can be run more than once for the following reasons:
* flows are built on top of cloud task queues which offer "deliver at least once" guarantee
* some features (see below: interrupt, sleep, waitFor or various error retry feature) rely on the ability of the flow to be "interrupted" and then re-run again.

All logic that has side-effects or is expensive to perform must be defined as a step within a flow to avoid unnecessary/undesiriable repeated execution. 

### run

This is the simplest way to define a step. Step has a name and function. Memoization uses the run step name as a key.

```javascript
export const myFlow = onScheduledFlow({ name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const output = await run("step-name", async () => {
      return await doSomething(input)
    })
    return output;
  }
)
```

It's allowed (although not recommended) to use the same name more than once:

```javascript
export const myFlow = onScheduledFlow({ name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const output1 = await run("same-name", async () => {
      return await doSomething1(input)
    })
    const output2 = await run("same-name", async () => {
      return await doSomething2(input)
    })

    return output1 + output2;
  }
)
```

Retry behavior can be specified on the run step. In case of an error thrown within the step function and framework can retry executing this step as per the provided retry configuration.  By default there's no retry -- if an error occurs, the whole flow execution will result in an error.

```javascript
export const myFlow = onScheduledFlow({ name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const output = await run({
      name: "step-name",
      retryConfig: {
        maxAttempts: 3,
        minBackoffSeconds: 10,
      }
    }, async () => {
      return await doSomething(input)
    })
    return output;
  }
)
```

### runAction
Action is a self-describing function. It exposes metadata (self-describing): name, description and input/output zod schema. Action is a shared type across the Genkit framework -- many AI primitives are implemented as actions.

The Action type is defined like this:

```javascript
export interface ActionMetadata<I extends z.ZodType, O extends z.ZodType> {
  name: string,
  description?: string,
  inputSchema?: I,
  outputSchema?: O,
}

export type Action<I extends z.ZodType, O extends z.ZodType> = 
  ((input: z.infer<I>) => Promise<z.infer<O>>) & 
  { __action: ActionMetadata<I, O> }

A helper action factory method is provided and you can build action factories like this:
const greet = (greeting) => action(
  { name: "greet", input: z.string(), output: z.string() },
  async (name) => {
     return `${greeting}, ${name}!`
  })
```

runAction is a wrapper around run step to make it easier to work with actions. Because actions already have all the necessary metadata it can be omitted during step definition.

```javascript
export const greetingFlow = onScheduledFlow({ name: 'greetingFlow', input: z.string(), output: z.string() },
  async (name) => {
    const frenchGreeting = greet("Bonjour")
    const greeting = await runAction(frenchGreeting, name)

    return greeting;
  }
)
```

retry can also be configured for runAction in the same way as for run.

### interrupt

interrupt step can be used to interrupt the flow and request external input. 

```javascript
export const myFlow = onScheduledFlow({ name: 'myFlow', input: z.void(), output: z.boolean() },
  async () => {
    const hoomanSaid = await interrupt("approve-by-hooman", 
      z.object({ approved: z.boolean() }))

    return hoomanSaid.approved;
  }
);

// resume interrupted flow
import { resumeFlow } from "@genkit-ai/flow/experimental"
await resumeFlow(myFlow, flowId, {
  approve: false
})
```

interrupt will "interrupt" the flow by throwing an InterruptError, so need to be careful with wrapping the interrupt step in try-catch.

```javascript
import { InterruptError } from "@genkit-ai/flow/experimental"

export const myFlow = onScheduledFlow({ name: 'myFlow', input: z.void(), output: z.boolean() },
  async () => {
    var hoomanSaid
    try {
      hoomanSaid = await interrupt(
        "approve-by-hooman", z.object({ approved: z.boolean() }))
    } catch (e) {
      // must rethrow
      if (e instanceof InterruptError) {
        throw e;
      }
      // do handling of other errors
    }

    return hoomanSaid.approved;
  }
)
```

### sleep

sleep method can be used to interrupt and automatically resume it after the specified number of seconds. 

```javascript
export const myFlow = onScheduledFlow({ name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const something = await run("do-something", async () => {...});

    await sleep("wait-a-few-hours", 60 * 60 * 2);

    const somethingElse = await run("do-something-else", async () => {...});

    return output;
  }
)
```

sleep has similar considerations to interrupt. See above.

### poll

**IMPORTANT:** not fully implemented yet, for reference only

Basic polling. Will periodically invoke the provided function until it returns true.

```javascript
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

poll has similar considerations to interrupt. See above.

Polling is done by reenqueuing the task in the queue (as per the polling configuration) and poll will continue interrupting the execution until the function returns true.

### waitFor

waitFor is a convenient version of poll that allows waiting for other flows to complete. 

```javascript
export const myFlow = onScheduledFlow({ name: 'myFlow', input: z.string(), output: z.string() },
  async (input) => {
    const otherFlowOp = await scheduleFlow(otherFlow, input)

    const [op] = await waitFor("wait-for-other-action", otherFlow, [otherFlowOp.name])
    
    return op.result.response;
  }
)
```

## Getting results

`getFlowState` can also be used to retrieve the current state:

```javascript
import { runFlow, getFlowState } from "@genkit-ai/flow/experimental"

const operation = await scheduleFlow(jokeFlow, 'banana');
console.log('Operation', operation);
console.log('state', await getFlowState(jokeFlow, operation.name));
```
