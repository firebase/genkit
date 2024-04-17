# Evaluating evaluators

## Build it

```
pnpm build
```

or if you need to, build everything:

```
cd ../../../; pnpm build; pnpm pack:all; cd -
```

## Evaluate an evaluator

```
genkit eval:run datasets/maliciousness_dataset.json --evaluators=ragas/maliciousness
```

## See your results

```
genkit start
```

Navigate to the `Evaluate` page
