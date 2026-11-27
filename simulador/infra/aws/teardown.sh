#!/usr/bin/env bash
# Deletes everything deploy.sh created: the stacks 'copa' (both instances and the
# database, VPC, API Gateway and key) and 'copa-ecr' (images and the artifacts
# bucket, emptied first), and the secrets in SSM. Asks for confirmation first.
#
#   simulador/infra/aws/teardown.sh --profile <aws-profile> [--region us-east-2] [--account <id>]
#   simulador/infra/aws/teardown.sh <aws-profile>
#
# Runs on Linux, WSL, macOS and Git Bash on Windows.
set -euo pipefail

# shellcheck source=common.sh
. "$(dirname "$0")/common.sh"  # options (profile, region, account) and portability helpers

account="$(aws_ sts get-caller-identity --query Account --output text)"
if [ -n "$EXPECTED_ACCOUNT" ] && [ "$account" != "$EXPECTED_ACCOUNT" ]; then
    echo "The profile '$PROFILE' resolves to account $account, expected $EXPECTED_ACCOUNT. Aborting." >&2
    exit 1
fi
echo "This deletes, in $REGION (profile $PROFILE, account $account):"
echo "the stacks 'copa' and 'copa-ecr' (instances and the database, API, key, images, MongoDB packages)"
echo "and the SSM secrets /copa-simulador/origin-secret and /copa-simulador/mongo-password."
read -r -p "Type 'delete copa' to confirm: " answer
[ "$answer" = "delete copa" ] || { echo "Cancelled."; exit 1; }

echo "Deleting copa..."
aws_ cloudformation delete-stack --stack-name copa
aws_ cloudformation wait stack-delete-complete --stack-name copa

bucket="$(aws_ cloudformation describe-stacks --stack-name copa-ecr \
    --query "Stacks[0].Outputs[?OutputKey=='ArtifactsBucket'].OutputValue" --output text 2>/dev/null || true)"
if [ -n "$bucket" ] && [ "$bucket" != "None" ]; then
    echo "Emptying s3://$bucket (CloudFormation can't delete a non-empty bucket)..."
    aws_ s3 rm "s3://${bucket:?}" --recursive --only-show-errors
fi
echo "Deleting copa-ecr..."
aws_ cloudformation delete-stack --stack-name copa-ecr
aws_ cloudformation wait stack-delete-complete --stack-name copa-ecr

for parameter in /copa-simulador/origin-secret /copa-simulador/mongo-password; do
    aws_ ssm delete-parameter --name "$parameter" 2>/dev/null || true
done
echo "Done: nothing from this project is left in $REGION."
