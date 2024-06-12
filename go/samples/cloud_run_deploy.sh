#!/bin/sh

# This script deploys a sample to Cloud Run.
# Run it from this directory (go/samples).
# For example
#
#    cloud_run_deploy.sh coffee-shop
#
# will deploy the coffee-shop sample as a Cloud Run service
# named genkit-coffee-shop.

sample="$1"

if [ -z "$sample" ]; then
  echo >&2 "usage: $0 SAMPLE"
  exit 1
fi

if [ ! -d "$sample" ]; then
  echo >&2 "$sample is not a subdirectory of the samples directory."
  exit 1
fi 

if [ -z "$GCLOUD_PROJECT" ]; then
  echo >&2 "Set GCLOUD_PROJECT to your project name."
  exit 1
fi

repo_root=$(git rev-parse --show-toplevel)
if [ -z "repo_root" ]; then
  echo >&2 "Could not determine git repo root directory; are you in a git repo?"
  exit 1
fi

location=${GCLOUD_LOCATION:-us-central1}

image=${location}-docker.pkg.dev/$GCLOUD_PROJECT/cloud-run-source-deploy/genkit-${sample}

gcloud --project "$GCLOUD_PROJECT" builds submit \
  --pack image=${image},env=GOOGLE_BUILDABLE=./samples/${sample} \
  "${repo_root}/go"
