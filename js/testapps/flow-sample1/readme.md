# Flow Sample 1

A basic example project showcasing various Genkit flows.

## Project Setup

### Installation

Ensure you have `pnpm` installed and run the following:

```bash
pnpm install
```

### Build and Run

To build and run the project, use:

```bash
pnpm build-and-run
```

This compiles the TypeScript source code and runs the `index.js` file in the `lib` directory.

---

## Available Flows

### Basic Flow

A simple flow that demonstrates the use of `run`.

#### Command:

```bash
genkit flow:run basic '"test input"'
```

#### Expected Output:

```text
"foo: subject: test input"
```

---

### Parent Flow

A flow that runs the `basic` flow and returns its output as a JSON string.

#### Command:

```bash
genkit flow:run parent
```

#### Expected Output:

```text
"\"foo: subject: foo\""
```

---

### Streamy Flow

A streaming flow that emits incremental data based on the input number.

#### Command:

```bash
genkit flow:run streamy 5
```

#### Expected Output:

```text
done: 5, streamed: 5 times
```

The streamed content will also show intermediate outputs for each count.

---

### StreamyThrowy Flow

Similar to `streamy`, but throws an error when the count reaches 3.

#### Command:

```bash
genkit flow:run streamyThrowy 5
```

#### Expected Output:

Throws an error at count 3.

---

### Throwy Flow

Demonstrates error handling by throwing an error when a subject is provided.

#### Command:

```bash
genkit flow:run throwy '"test input"'
```

#### Expected Output:

Throws an error with the message:

```text
test input
```

---

### Throwy2 Flow

Throws an error within the `run` function based on input.

#### Command:

```bash
genkit flow:run throwy2 '"test input"'
```

#### Expected Output:

Throws an error with the message:

```text
test input
```

---

### FlowMultiStepCaughtError

A multi-step flow that catches errors and continues execution.

#### Command:

```bash
genkit flow:run flowMultiStepCaughtError '"input data"'
```

#### Expected Output:

```text
"input data, Step 1, , Step 3"
```

A string indicating that Step 2 had an error, but the process continued.

---

### MultiSteps Flow

A flow demonstrating chaining multiple steps.

#### Command:

```bash
genkit flow:run multiSteps '"sample input"'
```

#### Expected Output:

```text
42
```

---

### LargeSteps Flow

Processes large chunks of data across multiple steps.

#### Command:

```bash
genkit flow:run largeSteps
```

#### Expected Output:

```text
"Finished processing large data."
```

---

## Running the Developer UI

To visualize flows in the Developer UI, start the server:

```bash
genkit start
```

Open your browser and navigate to `http://localhost:4000`.

---

## Notes

- This project requires `Node.js` version 20 or later.
- All flows are designed for demonstration and testing purposes.
