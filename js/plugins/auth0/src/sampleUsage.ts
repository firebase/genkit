

// Example usage to trigger the flow
await runFlow(
  yourAuthFlow,
  "your input string",
  {
    withLocalAuthContext: "your-auth0-access-token"
  }
);

// You will wrap this around an HTTP endpoint of your choice (e.g. express endpoint)
// And then parse the eader to grab the Authorization token and pass that in to this method