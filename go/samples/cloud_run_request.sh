#!/bin/sh

# This script makes a request to a sample application deployed
# to cloud run.
# Run it from this directory.
#
# For example, after deploying the coffee-shop example (see
# cloud_run_deploy.sh):
#
#    cloud_run_request.sh coffee-shop simpleGreeting '{"customerName": "Pat"}'   
#
# will request the genkit-coffee-shop Cloud Run service to invoke the simpleGreeting flow
# with the third argument as input.

if [ $# -ne 3 ]; then 
  echo >&2 "usage: $0 SAMPLE FLOW INPUT"
  exit 1
fi

sample=$1
flow=$2
input=$3

if [ ! -d "$sample" ]; then
  echo >&2 "$sample is not a subdirectory of the samples directory."
  exit 1
fi 

if [ -z "$GCLOUD_PROJECT" ]; then
  echo >&2 "Set GCLOUD_PROJECT to your project name."
  exit 1
fi

token=$(gcloud auth print-identity-token)
if [ -z "$token" ]; then
  echo >&2 "could not obtain identity token; have you logged in with 'gcloud auth'?"
  exit 1
fi

url=$(gcloud run services describe genkit-${sample} --format 'value(status.url)')
if [ -z "$url}" ]; then
  echo >&2 "could not get URL of Cloud Run service genkit-${sample}; are you sure it is deployed?"
  exit 1
fi

curl -H "Content-Type: application/json" \
  -H "Authorization: Bearer $token" \
  -d  "$input" \
  "$url/$flow"
