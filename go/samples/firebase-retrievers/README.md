
# Genkit Firestore Example

This sample demonstrates how to index and retrieve documents using Firestore and Genkit. The documents contain text about famous films, and users can query the indexed documents to retrieve information based on their input.

Currently the sample uses a mock embedder for simplicity. In your applications you will want to use an actual embedder from genkit.

## Prerequisites

Before running the sample, ensure you have the following:

1. **Google Cloud Project**: You must have a Google Cloud project with Firestore enabled.
2. **Genkit**: Installed and set up in your local environment.
3. **Authentication & Credentials**: Ensure you are authenticated with your Google Cloud project using the following command:
   ```bash
   gcloud auth application-default login
   ```
4. **Firestore Composite Index**: You need to create a composite vector index in Firestore for the `embedding` field. You can do this by running the following `curl` command:

   ```bash
   curl -X POST      "https://firestore.googleapis.com/v1/projects/<YOUR_PROJECT_ID>/databases/(default)/collectionGroups/<YOUR_COLLECTION>/indexes"      -H "Authorization: Bearer $(gcloud auth print-access-token)"      -H "Content-Type: application/json"      -d '{
       "fields": [
         {
           "fieldPath": "embedding",
           "vectorConfig": {
             "dimension": 3,
             "flat": {}
           }
         }
       ],
       "queryScope": "COLLECTION"
     }'
   ```

   Replace `<YOUR_PROJECT_ID>` and `<YOUR_COLLECTION>` with your actual project and collection names.

## Environment Variables

You need to set the following environment variables before running the project:

- `FIREBASE_PROJECT_ID`: The ID of your Google Cloud project.
- `FIRESTORE_COLLECTION`: The name of the Firestore collection to use for storing and retrieving documents.

You can set these variables by running:

```bash
export FIREBASE_PROJECT_ID=your-project-id
export FIRESTORE_COLLECTION=your-collection-name
```

## Running the Project

Once the environment is set up, follow these steps:

1. **Start Genkit**: 
   Run the following command to start the Genkit server:
   
   ```bash
   genkit start
   ```

2. **Index Documents**:
   To index the 10 documents with text about famous films, run the following Genkit flow:

   ```bash
   curl -X POST http://localhost:4000/api/runAction -H "Content-Type: application/json" -d '{"key":"/flow/flow-index-documents"}'
   ```

   This will insert 10 documents into the Firestore collection.

3. **Retrieve Documents**:
   To query the indexed documents, run the following Genkit flow and pass your query as input:

   ```bash
   curl -X POST http://localhost:4000/api/runAction -H "Content-Type: application/json" -d '{"key":"/flow/flow-retrieve-documents", "input": "crime film"}'
   ```

   You can replace `"crime film"` with any other query related to the indexed film documents.

## Troubleshooting

1. **Firestore Composite Index**: Ensure the Firestore composite index for the `embedding` field is correctly set up, otherwise queries may fail.
2. **Environment Variables**: Make sure that the `FIREBASE_PROJECT_ID` and `FIRESTORE_COLLECTION` environment variables are correctly exported.

## License

```
Copyright 2024 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
