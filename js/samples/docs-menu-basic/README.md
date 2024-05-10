## Build it

```
pnpm build
```

or if you need to, build everything:

```
cd </path/to/genkit>; pnpm run setup; cd -
```

where `</path/to/genkit>` is the top level of the genkit repo

## Run the flow via cli

```
genkit flow:run menuSuggestionFlow '"astronauts"'
```

## Run the flow in the Developer UI

```
genkit start
```

Click on menuSuggestionFlow in the lefthand navigation panel to playground the new flow.
