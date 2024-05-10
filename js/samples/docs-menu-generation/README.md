## Build it

```
pnpm build
```

or if you need to, build everything:

```
cd </path/to/genkit>; pnpm run setup; cd -
```

where `</path/to/genkit>` is the top level of the genkit repo.

## Run the flows via cli

```
genkit flow:run menuStreamingFlow '"astronauts"'
genkit flow:run menuHistoryFlow '"cats"'
genkit flow:run menuImageFlow '{"imageUrl": "https://raw.githubusercontent.com/firebase/genkit/main/js/samples/docs-menu-generation/menu.jpeg", "subject": "tiger"}'
```

## Run the flow in the Developer UI

```
genkit start
```

Click on `menuHistoryFlow`, `menuStreamingFlow`, or `menuImageFlow`
in the lefthand navigation panel to run the new flows.
