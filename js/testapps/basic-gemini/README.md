# Basic Gemini Project

This project demonstrates the integration of Genkit with GoogleAI and VertexAI to generate dynamic content through flows and tools. The specific focus is a simple app that generates a joke based on a user-provided subject.

## Features

- Uses `genkit` to define and run flows.
- Integrates `GoogleAI` and `VertexAI` plugins for enhanced AI capabilities.
- Demonstrates `jokeSubjectGenerator` as a tool and `jokeFlow` as a flow.

## Setup

### Prerequisites

- **Node.js** v20 or later
- **pnpm** package manager
- **Google Cloud SDK** installed and initialized

### Environment Variables

Ensure the following environment variables are set:

- **`GOOGLE_APPLICATION_CREDENTIALS`**: Path to the service account key JSON file.
- **`GOOGLE_PROJECT_ID`**: Your Google Cloud project ID.
- **`GOOGLE_API_KEY`**: Your API key for GoogleAI.

To set these variables, run:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_PROJECT_ID="your-google-project-id"
export GOOGLE_API_KEY="your-google-api-key"
```

### Google Cloud Initialization

1. Authenticate and set up your project:
   ```bash
   gcloud auth login
   gcloud config set project [YOUR_PROJECT_ID]
   ```
2. Ensure the necessary roles are assigned to your service account:
   - Vertex AI User
   - Storage Object Viewer

### Install Dependencies

Run the following command in the project root:

```bash
pnpm install
```

## Running the Project

The project requires running two terminals:

1. **Terminal 1**: Start the development server with hot-reloading:

   ```bash
   pnpm genkit:dev
   ```

2. **Terminal 2**: You can either:
   - Run the flow directly:
     ```bash
     genkit flow:run jokeFlow
     ```
   - Start the Genkit UI for visual execution:
     ```bash
     genkit ui:start
     ```

## Logic and Purpose

This app serves as a demonstration of Genkit's capability to define tools and flows with integrated AI models. The `jokeFlow` takes a user input via the `jokeSubjectGenerator` tool and uses `gemini15Flash` to produce a joke.

### Code Overview

#### `jokeSubjectGenerator`

- **Purpose**: Generates a joke subject, either provided by the user or defaults to "banana".
- **Input**: `string` (e.g., "apple").
- **Output**: `string` (same as input).

#### `jokeFlow`

- **Purpose**: Uses `jokeSubjectGenerator` and AI to generate a joke.
- **Input**: User provides a subject through the UI.
- **Output**: A joke about the subject.

### Example

- **Input**: "cat"
- **Output**: "Why did the cat sit on the computer? Because it wanted to keep an eye on the mouse!"

## Notes

- Adjust the temperature in the `config` for creativity levels.
- Ensure all environment variables are correctly set for smooth execution.
