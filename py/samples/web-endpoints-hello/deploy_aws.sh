#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

# Deploy to AWS App Runner
# ========================
#
# Builds a container image, pushes it to Amazon ECR, and deploys it to
# AWS App Runner. App Runner auto-scales and sets PORT automatically.
#
# Prerequisites (auto-detected and installed interactively):
#   - AWS CLI v2
#   - Podman or Docker
#   - GEMINI_API_KEY set in your environment
#
# Usage:
#   ./deploy_aws.sh                              # Interactive setup
#   ./deploy_aws.sh --region=us-east-1           # Explicit region
#   ./deploy_aws.sh --service=my-genkit-app      # Custom service name

set -euo pipefail

cd "$(dirname "$0")"
source "$(dirname "$0")/scripts/_common.sh"

SERVICE_NAME="${SERVICE_NAME:-genkit-asgi}"
REGION="${REGION:-us-east-1}"

# Parse arguments.
for arg in "$@"; do
  case "$arg" in
    --service=*) SERVICE_NAME="${arg#*=}" ;;
    --region=*) REGION="${arg#*=}" ;;
    --help|-h)
      echo "Usage: ./deploy_aws.sh [--service=NAME] [--region=REGION]"
      echo ""
      echo "Environment variables:"
      echo "  GEMINI_API_KEY    Required. Your Gemini API key."
      echo "  REGION            AWS region (default: us-east-1)."
      echo ""
      echo "Options:"
      echo "  --service=NAME    App Runner service name (default: genkit-asgi)."
      echo "  --region=REGION   AWS region (e.g. us-east-1, eu-west-1)."
      exit 0
      ;;
  esac
done

# ── Prerequisites ──────────────────────────────────────────────────────

# 1. Check AWS CLI is installed.
check_aws_installed || exit 1

# 2. Check authentication.
check_aws_auth || exit 1

# 3. Check GEMINI_API_KEY (interactive prompt if missing).
check_env_var "GEMINI_API_KEY" "https://aistudio.google.com/apikey" || exit 1

# 4. Detect container runtime (podman preferred, docker fallback).
if command -v podman &> /dev/null; then
  CONTAINER_CMD="podman"
elif command -v docker &> /dev/null; then
  CONTAINER_CMD="docker"
else
  echo -e "${RED}Error: podman or docker is required${NC}"
  exit 1
fi

# ── Get AWS account info ──────────────────────────────────────────────

ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${SERVICE_NAME}"

echo "🚀 Deploying ${SERVICE_NAME} to AWS App Runner (${REGION})..."
echo "   Account: ${ACCOUNT_ID}"
echo "   ECR:     ${ECR_REPO}"
echo ""

# ── Create ECR repository if needed ───────────────────────────────────

if ! aws ecr describe-repositories --repository-names "${SERVICE_NAME}" \
     --region "${REGION}" &> /dev/null; then
  echo "📦 Creating ECR repository: ${SERVICE_NAME}..."
  aws ecr create-repository \
    --repository-name "${SERVICE_NAME}" \
    --region "${REGION}" \
    --image-scanning-configuration scanOnPush=true
fi

# ── Build and push container ──────────────────────────────────────────

echo "🏗️  Building container image..."
$CONTAINER_CMD build -f Containerfile -t "${SERVICE_NAME}" .

echo "🔑 Authenticating with ECR..."
aws ecr get-login-password --region "${REGION}" | \
  $CONTAINER_CMD login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

$CONTAINER_CMD tag "${SERVICE_NAME}" "${ECR_REPO}:latest"

echo "⬆️  Pushing image to ECR..."
$CONTAINER_CMD push "${ECR_REPO}:latest"

# ── Deploy to App Runner ──────────────────────────────────────────────

echo ""
echo "🚀 Deploying to App Runner..."

# Check if service exists.
if aws apprunner list-services --region "${REGION}" \
   --query "ServiceSummaryList[?ServiceName=='${SERVICE_NAME}'].ServiceArn" \
   --output text 2>/dev/null | grep -q "arn:"; then
  # Update existing service.
  SERVICE_ARN=$(aws apprunner list-services --region "${REGION}" \
    --query "ServiceSummaryList[?ServiceName=='${SERVICE_NAME}'].ServiceArn" \
    --output text)
  echo "   Updating existing service..."
  aws apprunner update-service \
    --service-arn "${SERVICE_ARN}" \
    --source-configuration "{
      \"ImageRepository\": {
        \"ImageIdentifier\": \"${ECR_REPO}:latest\",
        \"ImageRepositoryType\": \"ECR\",
        \"ImageConfiguration\": {
          \"Port\": \"8080\",
          \"RuntimeEnvironmentVariables\": {
            \"GEMINI_API_KEY\": \"${GEMINI_API_KEY}\",
            \"PORT\": \"8080\"
          }
        }
      },
      \"AutoDeploymentsEnabled\": false
    }" \
    --region "${REGION}" > /dev/null
else
  # Create new service.
  echo "   Creating new App Runner service..."
  # App Runner needs an access role for ECR.
  ROLE_ARN=$(aws iam list-roles \
    --query "Roles[?RoleName=='AppRunnerECRAccessRole'].Arn" \
    --output text 2>/dev/null || echo "")

  if [[ -z "$ROLE_ARN" || "$ROLE_ARN" == "None" ]]; then
    echo "   Creating AppRunnerECRAccessRole IAM role..."
    aws iam create-role \
      --role-name AppRunnerECRAccessRole \
      --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
          "Effect": "Allow",
          "Principal": {"Service": "build.apprunner.amazonaws.com"},
          "Action": "sts:AssumeRole"
        }]
      }' > /dev/null
    aws iam attach-role-policy \
      --role-name AppRunnerECRAccessRole \
      --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
    ROLE_ARN=$(aws iam get-role --role-name AppRunnerECRAccessRole \
      --query "Role.Arn" --output text)
    echo "   Waiting for role to propagate..."
    sleep 10
  fi

  aws apprunner create-service \
    --service-name "${SERVICE_NAME}" \
    --source-configuration "{
      \"AuthenticationConfiguration\": {
        \"AccessRoleArn\": \"${ROLE_ARN}\"
      },
      \"ImageRepository\": {
        \"ImageIdentifier\": \"${ECR_REPO}:latest\",
        \"ImageRepositoryType\": \"ECR\",
        \"ImageConfiguration\": {
          \"Port\": \"8080\",
          \"RuntimeEnvironmentVariables\": {
            \"GEMINI_API_KEY\": \"${GEMINI_API_KEY}\",
            \"PORT\": \"8080\"
          }
        }
      },
      \"AutoDeploymentsEnabled\": false
    }" \
    --instance-configuration "{
      \"Cpu\": \"1 vCPU\",
      \"Memory\": \"2 GB\"
    }" \
    --health-check-configuration "{
      \"Protocol\": \"HTTP\",
      \"Path\": \"/health\",
      \"Interval\": 10,
      \"Timeout\": 5,
      \"HealthyThreshold\": 1,
      \"UnhealthyThreshold\": 5
    }" \
    --region "${REGION}" > /dev/null
fi

echo ""
echo "✅ Deployed! Get the URL with:"
echo "   aws apprunner list-services --region ${REGION} --query \"ServiceSummaryList[?ServiceName=='${SERVICE_NAME}'].ServiceUrl\" --output text"
echo ""
echo "   Logs: aws apprunner list-operations --service-arn \$(aws apprunner list-services --region ${REGION} --query \"ServiceSummaryList[?ServiceName=='${SERVICE_NAME}'].ServiceArn\" --output text)"
