# Flow Authentication

Genkit supports flow-level authentication, allowing you to secure your flows and ensure that only authorized users can execute them. This is particularly useful when deploying flows as HTTP endpoints.

## Configuring Flow Authentication

To add authentication to a flow, you can use the `WithFlowAuth` option when defining the flow. This option takes an implementation of the `FlowAuth` interface, which provides methods for handling authentication and authorization.

Here's an example of how to define a flow with authentication:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="auth" adjust_indentation="auto" %}
```

In this example, we're using the Firebase auth plugin to handle authentication. The `policy` function defines the authorization logic, checking if the user ID in the auth context matches the input user ID.

## Using the Firebase Auth Plugin

The Firebase auth plugin provides an easy way to integrate Firebase Authentication with your Genkit flows. Here's how to use it:

1. Import the Firebase plugin:

   ```golang
   import "github.com/firebase/genkit/go/plugins/firebase"
   ```

2. Create a Firebase auth provider:

   ```golang
   {% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="auth-create" adjust_indentation="auto" %}
   ```

   The `NewAuth` function takes three arguments:

   - `ctx`: The context for Firebase initialization.
   - `policy`: A function that defines your authorization logic.
   - `required`: A boolean indicating whether authentication is required for direct calls.

3. Use the auth provider when defining your flow:

   ```golang
   {% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="auth-define" adjust_indentation="auto" %}
   ```

## Handling Authentication in HTTP Requests

When your flow is deployed as an HTTP endpoint, the Firebase auth plugin will automatically handle authentication for incoming requests. It expects a Bearer token in the Authorization header of the HTTP request.

## Running Authenticated Flows Locally

When running authenticated flows locally or from within other flows, you can provide local authentication context using the `WithLocalAuth` option:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="auth-run" adjust_indentation="auto" %}
```

This allows you to test authenticated flows without needing to provide a valid Firebase token.
