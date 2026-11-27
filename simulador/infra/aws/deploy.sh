#!/usr/bin/env bash
# Deploys the Simulador de Campeonato API to AWS (see README.md in this folder).
#
#   simulador/infra/aws/deploy.sh --profile <aws-profile> [--region us-east-2] [--account <id>]
#   simulador/infra/aws/deploy.sh <aws-profile>
#
# Runs on Linux, WSL, macOS and Git Bash on Windows.
#
# 1. registry + artifacts stack, 2. build + push the `aws` image, 3. MongoDB packages,
# 4. secrets, 5. main stack (API instance, database instance, API Gateway),
# 6. wait for the API, 7. print the URL.
# Safe to re-run: every step is idempotent; a re-run ships the current code.
set -euo pipefail

# shellcheck source=common.sh
. "$(dirname "$0")/common.sh"  # options (profile, region, account) and portability helpers

HERE="$(native_dir "$(dirname "$0")")"
ROOT="$(native_dir "$HERE/../../..")"
ECR_STACK=copa-ecr
STACK=copa
CSV=jogadores_copa_america_2024_filtrado.csv
ORIGIN_PARAMETER=/copa-simulador/origin-secret
MONGO_PASSWORD_PARAMETER=/copa-simulador/mongo-password
# Pinned MongoDB packages for Amazon Linux 2023, with the SHA-256 from the repo's
# metadata: the database instance has no internet and installs exactly these.
MONGODB_REPO=https://repo.mongodb.org/yum/amazon/2023/mongodb-org/8.0/x86_64/RPMS
MONGODB_RPMS=(
    "mongodb-org-server-8.0.38-1.amzn2023.x86_64.rpm 9d6ff498cf3d88c99eb0e337844b360ce80c968fdebd3a5319a2b7e775770698"
    "mongodb-mongosh-2.14.3.x86_64.rpm ec75e10e1fb0bde71383c4cff066280c3eec3d8cafbd3640be1b2ad48803e9bc"
)

step() { printf '\n== %s\n' "$*"; }
output() { aws_ cloudformation describe-stacks --stack-name "$1" --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text; }

step "Checking the AWS identity"
account="$(aws_ sts get-caller-identity --query Account --output text)"
if [ -n "$EXPECTED_ACCOUNT" ] && [ "$account" != "$EXPECTED_ACCOUNT" ]; then
    echo "The profile '$PROFILE' resolves to account $account, expected $EXPECTED_ACCOUNT. Aborting." >&2
    exit 1
fi
echo "profile $PROFILE, account $account, region $REGION"

step "Registry stack ($ECR_STACK)"
aws_ cloudformation deploy --stack-name "$ECR_STACK" --template-file "$HERE/ecr.yaml" --no-fail-on-empty-changeset
repository="$(output "$ECR_STACK" RepositoryUri)"
bucket="$(output "$ECR_STACK" ArtifactsBucket)"

step "MongoDB packages in s3://$bucket/mongodb/ (downloaded and checked once)"
for entry in "${MONGODB_RPMS[@]}"; do
    read -r rpm sha256 <<<"$entry"
    if aws_ s3api head-object --bucket "$bucket" --key "mongodb/$rpm" >/dev/null 2>&1; then
        echo "$rpm: already there"
        continue
    fi
    rpm_dir="$(new_tmp_dir)"
    curl -sSfL --max-time 600 -o "$(native_path "$rpm_dir/$rpm")" "$MONGODB_REPO/$rpm"
    actual="$(sha256_of "$rpm_dir/$rpm")"
    if [ "$actual" != "$sha256" ]; then
        rm -f "${rpm_dir:?}/${rpm:?}"; rmdir "${rpm_dir:?}"
        echo "$rpm: checksum mismatch ($actual), refusing to upload" >&2
        exit 1
    fi
    aws_ s3 cp "$(native_path "$rpm_dir/$rpm")" "s3://$bucket/mongodb/$rpm" --only-show-errors
    rm -f "${rpm_dir:?}/${rpm:?}"; rmdir "${rpm_dir:?}"
    echo "$rpm: checksum ok, uploaded"
done

step "Building and pushing the image"
tag="$(git -C "$ROOT" rev-parse --short HEAD)"
if [ -n "$(git -C "$ROOT" status --porcelain -- simulador pipeline-dados/artefatos/$CSV)" ]; then
    tag="$tag-dirty-$(date +%Y%m%d%H%M%S)"  # uncommitted changes: never reuse a commit's tag
fi
image="$repository:$tag"
docker build --platform linux/amd64 -f "$ROOT/simulador/server/Dockerfile" --target aws \
    --build-context data="$ROOT/pipeline-dados/artefatos" -t "$image" "$ROOT/simulador"
# A throwaway Docker config for the login: Docker Desktop's credential store (on
# Windows, and in WSL through desktop.exe) rejects ECR tokens (too long), and the
# token (valid 12 h) shouldn't outlive the push.
tmp_dir="$(new_tmp_dir)"
# Native form (C:/... on Windows): docker.exe can't find /tmp/... and would silently
# fall back to the default config and its credential store.
docker_config="$(native_path "$tmp_dir")"
cleanup_docker_config() { rm -f "${tmp_dir:?}/config.json"; rmdir "${tmp_dir:?}" 2>/dev/null || true; }
trap cleanup_docker_config EXIT
# An `auths` entry is required: with none, Docker auto-detects the credential store anyway.
echo "{\"auths\": {\"${repository%%/*}\": {}}}" > "$tmp_dir/config.json"
aws_ ecr get-login-password | DOCKER_CONFIG="$docker_config" docker login --username AWS --password-stdin "${repository%%/*}"
DOCKER_CONFIG="$docker_config" docker push "$image"
cleanup_docker_config

step "Origin secret (created once in SSM, never printed)"
# API Gateway sends it in X-Origin-Verify and the API refuses requests without it,
# so the instance's public address is useless without the API key.
if ! aws_ ssm get-parameter --name "$ORIGIN_PARAMETER" >/dev/null 2>&1; then
    aws_ ssm put-parameter --name "$ORIGIN_PARAMETER" --type SecureString --tier Standard \
        --value "$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')" >/dev/null
    echo "created $ORIGIN_PARAMETER"
fi
origin_secret="$(aws_ ssm get-parameter --name "$ORIGIN_PARAMETER" --with-decryption --query Parameter.Value --output text)"

step "MongoDB password (created once in SSM, never printed)"
# The API instance reads it from SSM; the database instance, which has no internet
# (so no SSM), from the private bucket through the S3 gateway endpoint.
if ! aws_ ssm get-parameter --name "$MONGO_PASSWORD_PARAMETER" >/dev/null 2>&1; then
    aws_ ssm put-parameter --name "$MONGO_PASSWORD_PARAMETER" --type SecureString --tier Standard \
        --value "$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')" >/dev/null
    echo "created $MONGO_PASSWORD_PARAMETER"
fi
aws_ ssm get-parameter --name "$MONGO_PASSWORD_PARAMETER" --with-decryption --query Parameter.Value --output text \
    | tr -d '\r\n' | aws_ s3 cp - "s3://$bucket/secrets/mongo-password" --only-show-errors

step "Main stack ($STACK) - the first deploy takes ~5-10 min"
instance_before="$(output "$STACK" InstanceId 2>/dev/null || true)"
aws_ cloudformation deploy --stack-name "$STACK" --template-file "$HERE/copa.yaml" \
    --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset \
    --parameter-overrides ImageUri="$image" ArtifactsBucket="$bucket" OriginSecret="$origin_secret" \
        OriginSecretParameter="$ORIGIN_PARAMETER" MongoPasswordParameter="$MONGO_PASSWORD_PARAMETER"
instance="$(output "$STACK" InstanceId)"

# Same API instance as before: ship the image through SSM. A new instance runs
# run.sh on its own first boot; running it twice at once would fight over containers.
if [ -n "$instance_before" ] && [ "$instance_before" = "$instance" ]; then
    step "Shipping the image to the running instance (through SSM; the database stays)"
    command_id="$(aws_ ssm send-command --instance-ids "$instance" --document-name AWS-RunShellScript \
        --parameters "commands=[\"/opt/copa/set-image.sh $image\"]" --query Command.CommandId --output text)"
    aws_ ssm wait command-executed --command-id "$command_id" --instance-id "$instance" || true
    status="$(aws_ ssm get-command-invocation --command-id "$command_id" --instance-id "$instance" --query Status --output text)"
    aws_ ssm get-command-invocation --command-id "$command_id" --instance-id "$instance" --query StandardOutputContent --output text | tail -5
    [ "$status" = "Success" ] || { echo "Updating the instance failed ($status)." >&2; exit 1; }
fi

step "Waiting for the API to answer through API Gateway (first boot: Docker, images, seed)"
url="$(output "$STACK" InvokeUrl)"
key="$(aws_ apigateway get-api-key --api-key "$(output "$STACK" ApiKeyId)" --include-value --query value --output text)"
for attempt in $(seq 1 60); do
    if curl -sf -H "x-api-key: $key" "$url/meta" >/dev/null; then
        echo "up: $(curl -s -H "x-api-key: $key" "$url/meta")"
        break
    fi
    [ "$attempt" -eq 60 ] && { echo "The API did not answer within 15 minutes; see /var/log/copa-bootstrap.log on $instance (via SSM)." >&2; exit 1; }
    sleep 15
done

step "Done"
echo "Base URL : $url"
echo "API key  : aws apigateway get-api-key --api-key $(output "$STACK" ApiKeyId) --include-value --query value --output text --profile $PROFILE --region $REGION"
echo "Image    : $image"
