# Vertex AI Vector Search Firestore

An example demonstrating the use Vector Search API with Firestore retriever for Vertex AI

## Setup environment

1. Install [GCP CLI](https://cloud.google.com/sdk/docs/install).
2. Run the following code to connect to VertexAI.
```bash
gcloud auth application-default login` 
```
3. Set the following env vars to run the sample
```
export LOCATION=''
export PROJECT_ID=''
export FIRESTORE_COLLECTION=''
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=''
export VECTOR_SEARCH_INDEX_ENDPOINT_ID=''
export VECTOR_SEARCH_INDEX_ID=''
export VECTOR_SEARCH_PUBLIC_DOMAIN_NAME=''
```
4. Run the sample.

## Run the sample

```bash
genkit start -- uv run src/sample.py
```
