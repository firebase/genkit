# Dev tooling: local flow runner, playgrounds

You can run Genkit's developer tooling locally using the Genkit CLI:

```
npx genkit start
```

You can run flows

```
npx genkit flow:run myFlow {"input":"value"}
```

or resume flows

```
npx genkit flow:resume myFlow FLOW_ID {"resume":"value"}
```