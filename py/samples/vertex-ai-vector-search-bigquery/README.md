# Vertex AI - Vector Search BigQuery

An example demonstrating the use Vector Search API with BigQuery retriever for Vertex AI

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
export BIGQUERY_DATASET_NAME=''
export BIGQUERY_TABLE_NAME=''
export VECTOR_SEARCH_DEPLOYED_INDEX_ID=''
export VECTOR_SEARCH_INDEX_ENDPOINT_PATH=''
export VECTOR_SEARCH_API_ENDPOINT=''
```
4. Run the sample.

## Env vars definition
| Variable                            | Definition                                                                                                |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `LOCATION`                          | The Google Cloud region or multi-region where your resources (e.g., Vertex AI Index, BigQuery dataset) are located. Example: `us-central1`. |
| `PROJECT_ID`                        | The name or unique identifier for your Google Cloud Project.                                                      |
| `BIGQUERY_DATASET_NAME`             | The name of the BigQuery dataset that contains your source data or will store results.                     |
| `BIGQUERY_TABLE_NAME`               | The name of the specific table within the BigQuery dataset.                                                 |
| `VECTOR_SEARCH_DEPLOYED_INDEX_ID`   | The ID of your deployed Vertex AI Vector Search index that you want to query. Numeric identifier.                             |
| `VECTOR_SEARCH_INDEX_ENDPOINT_PATH` | The full storage path of the Vertex AI Vector Search Index Endpoint. Example: `projects/YOUR_PROJECT_ID/locations/YOUR_LOCATION/indexEndpoints/YOUR_INDEX_ENDPOINT_ID`. |
| `VECTOR_SEARCH_API_ENDPOINT`        | The regional API endpoint for making calls to the Vertex AI Vector Search service. Example: `YOUR_LOCATION-aiplatform.googleapis.com`. |

## Run the sample

```bash
genkit start -- uv run src/sample.py
```

## Set up env for sample
In the file `setup_env.py` you will find some code that will help you to create the bigquery dataset, table with the expected schema, encode the content of the table and push this to the VertexAI Vector Search index. 
This index must be created with update method set as `stream`. VertexAI Index is expected to be already created. 
