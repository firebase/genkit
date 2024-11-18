# Genkit

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://firebase.google.com/docs/genkit).

License: Apache 2.0

## Troubleshooting

### Telemetry upload reliability in Firebase Functions / Cloud Run

When Genkit is hosted in Google Cloud Run (including Firebase Functions), telemetry data upload may be less reliable as the container switches to the "idle" [lifecycle state](https://cloud.google.com/blog/topics/developers-practitioners/lifecycle-container-cloud-run). If higher reliability is important to you, consider changing [CPU allocation](https://cloud.google.com/run/docs/configuring/cpu-allocation) to "always allocated" in the Google Cloud Console. Note that this impacts pricing.
