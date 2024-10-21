
# Firebase Genkit Plugin

The Firebase plugin for Genkit allows flows to integrate seamlessly with Firebase services, such as Firestore and Firebase Authentication.

This plugin includes initialization for Firebase, a retriever for Firestore, and Firebase Authentication integration for enhanced flow security.

## Prerequisites

Before using this plugin, ensure you have the following prerequisites:

1. **Google Cloud Account**: Sign up for a Google Cloud account if you don’t already have one [here](https://cloud.google.com/gcp).
   
2. **Google Cloud SDK**: Ensure that you have the [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install) installed on your local machine.

3. **Firebase Project**: Create a Firebase project or use an existing one. This project should have Firestore and Firebase Authentication enabled.
   
4. **APIs to Enable**:
   - [Firestore API](https://console.cloud.google.com/apis/library/firestore.googleapis.com)
   - [Firebase Authentication API](https://console.cloud.google.com/apis/library/identitytoolkit.googleapis.com)

   You can enable these APIs from the [API Dashboard](https://console.cloud.google.com/apis/dashboard) of your Google Cloud project.

5. **Firebase CLI**: To locally run or interact with Firebase, ensure you have the Firebase CLI installed.

## Setup Instructions

### Firebase Initialization

To initialize Firebase in your Genkit project, first, import the `firebase` package:

```go
import "github.com/firebase/genkit/go/plugins/firebase"
```

### Configuration

You need to provide the Firebase configuration in the form of a `FirebasePluginConfig` struct. This example assumes that you are loading the project ID and Firestore collection from environment variables:

```go
// Load project ID and Firestore collection from environment variables
projectID := os.Getenv("FIREBASE_PROJECT_ID")
collectionName := os.Getenv("FIRESTORE_COLLECTION")

firebaseConfig := &firebase.FirebasePluginConfig{
    App: firebaseApp, // Pass the pre-initialized Firebase app
    Retrievers: []firebase.RetrieverOptions{
        {
            Name:           "example-retriever",
            Client:         firestoreClient,
            Collection:     collectionName,
            Embedder:       embedder,
            VectorField:    "embedding",
            ContentField:   "text",
            MetadataFields: []string{"metadata"},
            Limit:          10,
            DistanceMeasure: firestore.DistanceMeasureEuclidean,
            VectorType:      firebase.Vector64,
        },
    },
}
```

### Initialize Firebase

To initialize Firebase with the configuration, call the `Init` function. This ensures that the Firebase App is only initialized once:

```go
ctx := context.Background()
err := firebase.Init(ctx, firebaseConfig)
if err != nil {
    log.Fatalf("Error initializing Firebase: %v", err)
}
```

Once initialized, the Firebase app can be accessed using the `App` function:

```go
app, err := firebase.App(ctx)
if err != nil {
    log.Fatalf("Error getting Firebase app: %v", err)
}
```

### Firestore Retriever

The Firebase plugin provides a Firestore retriever that can be used to query documents in a Firestore collection based on vector similarity.

1. **Options Configuration**:
   You need to configure `RetrieverOptions`, which include:

   - **Client**: The Firestore client.
   - **Collection**: The Firestore collection you want to query.
   - **Embedder**: The AI embedder to convert documents into embeddings.
   - **VectorField**: The Firestore field containing the vector embeddings.
   - **ContentField**: The field containing the text of the document.
   - **MetadataFields**: A list of fields to include in the document metadata.

```go
retrieverOptions := firebase.RetrieverOptions{
    Name:           "example-retriever",
    Client:         firestoreClient,
    Collection:     collectionName,
    Embedder:       embedder,
    VectorField:    "embedding",
    ContentField:   "text",
    MetadataFields: []string{"metadata"},
    Limit:          10,
    DistanceMeasure: firestore.DistanceMeasureEuclidean,
    VectorType:      firebase.Vector64,
}
```

2. **Define the Retriever**:

```go
retriever, err := firebase.DefineFirestoreRetriever(retrieverOptions)
if err != nil {
    log.Fatalf("Error defining Firestore retriever: %v", err)
}
```

3. **Use the Retriever**:

To perform a retrieval based on a query document:

```go
req := &ai.RetrieverRequest{
    Document: ai.DocumentFromText("Query text", nil),
}

resp, err := retriever.Retrieve(ctx, req)
if err != nil {
    log.Fatalf("Error retrieving documents: %v", err)
}

for _, doc := range resp.Documents {
    log.Printf("Retrieved document: %s", doc.Content[0].Text)
}
```

### Firebase Authentication

The Firebase plugin integrates Firebase Authentication to provide authorization and access control in Genkit flows.

1. **Creating an Auth Object**:
   Use the `NewAuth` function to create an auth object, specifying whether authentication is required and the policy for checking the context:

```go
auth, err := firebase.NewAuth(ctx, nil, true)
if err != nil {
    log.Fatalf("Error initializing Firebase Auth: %v", err)
}
```

2. **Providing Authentication Context**:
   To use authentication, the `ProvideAuthContext` function extracts the authentication header from a request, verifies the token, and provides the auth context:

```go
ctx, err := auth.ProvideAuthContext(ctx, "Bearer your-id-token")
if err != nil {
    log.Fatalf("Error providing auth context: %v", err)
}
```

3. **Checking Authorization Policy**:
   The `CheckAuthPolicy` function ensures that the current auth context satisfies any policies you’ve defined for your flow:

```go
err := auth.CheckAuthPolicy(ctx, inputData)
if err != nil {
    log.Fatalf("Authorization check failed: %v", err)
}
```

## Local Testing

When testing flows locally, ensure that the Google Cloud credentials are available to the Firebase SDK. Use the following command to authenticate:

```bash
gcloud auth application-default login
```

This will provide your local environment with the necessary credentials to interact with Firebase services.

## Conclusion

The Firebase Genkit Plugin simplifies the integration of Firebase services, including Firestore and Firebase Authentication, into your Genkit flows. With features like Firestore vector queries and flow-level authentication, it provides powerful tools for building intelligent, secure applications.
