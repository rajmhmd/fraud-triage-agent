#!/usr/bin/env bash
# One-time AWS setup: least-privilege IAM user for the hackathon agent.
# Usage: ./infra/setup.sh            (run with an admin profile, e.g. AWS_PROFILE=admin)
set -euo pipefail

USER_NAME="fraud-triage-agent-dev"
POLICY_NAME="FraudTriageAgentPolicy"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

sed "s/ACCOUNT_ID/${ACCOUNT_ID}/" infra/iam-policy.json > /tmp/fraud-agent-policy.json

aws iam create-user --user-name "$USER_NAME" >/dev/null 2>&1 || echo "user exists"
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"
aws iam create-policy --policy-name "$POLICY_NAME" \
  --policy-document file:///tmp/fraud-agent-policy.json >/dev/null 2>&1 \
  || aws iam create-policy-version --policy-arn "$POLICY_ARN" \
       --policy-document file:///tmp/fraud-agent-policy.json --set-as-default >/dev/null
aws iam attach-user-policy --user-name "$USER_NAME" --policy-arn "$POLICY_ARN"

echo "Create an access key and store it as profile 'hackathon':"
echo "  aws iam create-access-key --user-name $USER_NAME"
echo "  aws configure --profile hackathon"
echo "Delete the key after the hackathon:  aws iam delete-access-key --user-name $USER_NAME --access-key-id <id>"
