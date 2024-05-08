# Evaluating pdfQA with cat facts

## Build it

```
pnpm build
```

or if you need to, build everything:

```
cd ../../../; pnpm build; pnpm pack:all; cd -
```

## Run setup

This will add the GenkitGrubPub.pdf to your index

```
genkit flow:run setup
```

or add more pdfs to the index if you want:

```
genkit flow:run setup '["./path/to/your/file.pdf"]'
```

## Run the flow via cli

```
genkit flow:run menuQA '"What burgers are on the menu?"'
```

## Run the flow in the Developer UI

```
genkit start
```

Click on the menuQA flow in the lefthand navigation panel to playground the new flow.
