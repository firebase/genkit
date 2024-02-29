# Contributing to Genkit

## Build it

```
npm i
npm run build:all
```

This will build all packages in this repository. This is recommended the first time you check out a fresh repo or pull new revisions.

## Pack it

Pack packages for testing/distribution.

Assuming you built everything previously....

```
npm run pack:all
```

this will produce tarballs in the `dist` folder. Also `genkit-dist.zip` -- a zip of all the package tarballs.

## Link it

You will need the genkit CLI to run samples and the Dev UI

```
cd  genkit-tools
npm link
```

## Run it

In the `genkit/samples` folder you will find some samples. They might contain instructions for how to run them and what setup is necessary.

Here's one that requires no setup:

```
cd genkit/samples/flows-sample1
genkit flow:run basic "\"hello\""
```

Run the DevUI

```
cd genkit/samples/flows-sample1
genkit start
```

Point your browser to http://localhost:4000

## Code it

FYI: `genkit` and `genkit-tools` are in two separate workspaces.

As you make changes you may want to build an test things by running samples.
You can reduce the scope of what you're building b

```
npm run build:genkit 
npm run build:genkit-tools
```

But you can also go into specific package that you changed and run

```
npm run build
```

If you are going to be coding for a while then do

```
npm run build:watch
```

in the package that you're editing.

## Send it

Once done coding you will want to send a PR. Always do things in a separate branch (by convention name the branch `your_name-feature-something`).

Before sending the PR alwaya run

```
npm run format
npm run build:all
```


