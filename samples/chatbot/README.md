# Chatbot

This is a simple chatbot with two LLMs.


Prerequisite
 * install Genkit (`npm i -g genkit`)
 * Google Cloud project with Vertex AI API enabled (https://pantheon.corp.google.com/apis/library/aiplatform.googleapis.com)
 * gcloud CLI installed (https://cloud.google.com/sdk/docs/install-sdk)

The sample is using Vertex AI, so you'll need to auth:

```bash
gcloud auth login
gcloud auth application-default login --project YOUR_PROJECT
```

```bash
npm run setup
npm start
```

Point your browser to http://localhost:4200/
Inspect runs in http://localhost:4000/