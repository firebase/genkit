# Vertex AI - Vector Search Firestore

An example demonstrating the use Vector Search API with Firestore retriever for Vertex AI

## Setup environment

1. Install [GCP CLI](https://cloud.google.com/sdk/docs/install).
2. Run the following code to connect to VertexAI.
```bash
gcloud auth application-default login
```
3. Set the following env vars to run the sample
```
export LOCATION=''
export PROJECT_ID=''
export FIRESTORE_COLLECTION=''
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=''
export VECTOR_SEARCH_INDEX_ENDPOINT_PATH=''
export VECTOR_SEARCH_API_ENDPOINT=''
```
4. Run the sample.

## Env vars definition
| Variable                            | Definition                                                                                                |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `LOCATION`                          | The Google Cloud region or multi-region where your resources (e.g., Vertex AI Index, Firestore database) are located. Example: `us-central1`. |
| `PROJECT_ID`                        | The name or unique identifier for your Google Cloud Project.                                                      |
| `FIRESTORE_COLLECTION`              | The name of the Firestore collection used, for example, to store metadata associated with your vectors or the source documents. |
| `VECTOR_SEARCH_DEPLOYED_INDEX_ID`   | The ID of your deployed Vertex AI Vector Search index that you want to query.                               |
| `VECTOR_SEARCH_INDEX_ENDPOINT_PATH` | The full storage path of the Vertex AI Vector Search Index Endpoint. Example: `projects/YOUR_PROJECT_ID/locations/YOUR_LOCATION/indexEndpoints/YOUR_INDEX_ENDPOINT_ID`. |
| `VECTOR_SEARCH_API_ENDPOINT`        | The regional API endpoint for making calls to the Vertex AI Vector Search service. Example: `YOUR_LOCATION-aiplatform.googleapis.com`. |

## Run the sample

```bash
genkit start -- uv run src/sample.py
```
