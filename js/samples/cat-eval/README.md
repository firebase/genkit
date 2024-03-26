# Evaluating pdfQA with cat facts

## Build it

```
npm run build
```

or if you need to, build everything:

```
cd ../../../;npm run build:all;npm run pack:all;cd -
```

## Run setup

```
genkit flow:run setup
```

or add more pdfs to the index if you want:

```
genkit flow:run setup '[\"./docs/Cat.pdf\"]'
```

## Evaluate it

```
genkit eval:flow pdfQA --input eval/cat_questions.json
```

## See your results

```
genkit start
```

Navigate to the `Evaluate` page
