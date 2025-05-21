# Error Types

Genkit knows about two specialized types: `GenkitError` and `UserFacingError`.
`GenkitError` is intended for use by Genkit itself or Genkit plugins.
`UserFacingError` is intended for [`ContextProviders`](../deploy-node.md) and
your code. The separation between these two error types helps you better understand
where your error is coming from.

Genkit plugins for web hosting (e.g. [`@genkit-ai/express`](https://js.api.genkit.dev/modules/_genkit-ai_express.html) or [`@genkit-ai/next`](https://js.api.genkit.dev/modules/_genkit-ai_next.html))
SHOULD capture all other Error types and instead report them as an internal error in the response.
This adds a layer of security to your application by ensuring that internal details of your application
do not leak to attackers.
