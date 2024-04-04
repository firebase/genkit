# Dev tooling: local flow runner, playgrounds

You can run Genkit's developer tooling locally using the Genkit CLI:

```posix-terminal
genkit start
```

You can run flows:

```posix-terminal
genkit flow:run myFlow {"input":"value"}
```

Or resume flows:

```posix-terminal
genkit flow:resume myFlow FLOW_ID {"resume":"value"}
```
