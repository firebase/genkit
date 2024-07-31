# No new actions at runtime error

Defining new action at runtime is not alowed.

✅ DO:

```ts
const prompt = defineDotprompt({...})

const flow = defineFlow({...}, async (input) => {
  await prompt.generate(...);
})
```

❌ DON'T:

```ts
const flow = defineFlow({...}, async (input) => {
  const prompt = defineDotprompt({...})
  prompt.generate(...);
})
```
