# Shared by deploy.sh and teardown.sh (sourced, not run). Parses the options and
# hides the differences between Linux/WSL/macOS and Git Bash on Windows.
#
#   <script> --profile <name> [--region <region>] [--account <id>]
#   <script> <profile>                      (the profile as the only argument)

usage() {
    cat >&2 <<EOF
Usage: $(basename "$0") --profile <aws-profile> [--region <region>] [--account <account-id>]
       $(basename "$0") <aws-profile>

  --profile  AWS CLI profile to use (required; 'default' is refused)
  --region   AWS region (default: us-east-2)
  --account  if given, abort unless the profile resolves to this account
EOF
    printf '%s' "${USAGE_EXTRA:-}" >&2  # options of the calling script
    exit 2
}

PROFILE=""
REGION="us-east-2"
EXPECTED_ACCOUNT=""
while [ $# -gt 0 ]; do
    case "$1" in
        --profile) [ $# -ge 2 ] || usage; PROFILE="$2"; shift 2 ;;
        --profile=*) PROFILE="${1#*=}"; shift ;;
        --region) [ $# -ge 2 ] || usage; REGION="$2"; shift 2 ;;
        --region=*) REGION="${1#*=}"; shift ;;
        --account) [ $# -ge 2 ] || usage; EXPECTED_ACCOUNT="$2"; shift 2 ;;
        --account=*) EXPECTED_ACCOUNT="${1#*=}"; shift ;;
        -h|--help) usage ;;
        -*) echo "Unknown option: $1" >&2; usage ;;
        *) [ -z "$PROFILE" ] || usage; PROFILE="$1"; shift ;;
    esac
done
if [ -z "$PROFILE" ]; then
    echo "An AWS profile is required." >&2
    usage
fi
# Project rule: never the default profile - a forgotten argument must not silently
# deploy (or delete) with whatever credentials happen to be the default.
if [ "$PROFILE" = "default" ]; then
    echo "Refusing the 'default' profile: pass the project's profile explicitly." >&2
    exit 2
fi

# The flags beat any AWS_* credentials in the environment; the export covers anything
# else that reads the profile from the environment.
export AWS_PROFILE="$PROFILE"
aws_() { aws --profile "$PROFILE" --region "$REGION" "$@"; }

# Git Bash on Windows runs Windows programs (aws.exe, docker.exe, curl.exe) that can't
# read /c/... or /tmp/... paths, so paths handed to them must be C:/...; and its
# automatic path conversion would mangle container paths (/app/data/...), so it's off.
case "${OSTYPE:-}" in
    msys*|cygwin*) ON_WINDOWS=1; export MSYS_NO_PATHCONV=1 ;;
    *) ON_WINDOWS=0 ;;
esac
native_path() { if [ "$ON_WINDOWS" = 1 ]; then cygpath -m "$1"; else printf '%s' "$1"; fi; }
# Absolute path of a directory, in the form native programs understand.
native_dir() { (cd "$1" && if [ "$ON_WINDOWS" = 1 ]; then pwd -W; else pwd; fi); }

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    else shasum -a 256 "$1" | cut -d' ' -f1; fi  # macOS
}

# Temporary folders: always created by mktemp with a known name, and removed file by
# file and then with rmdir (which refuses a non-empty folder), so a wrong path can
# never delete anything else.
new_tmp_dir() {
    local dir
    dir="$(mktemp -d "${TMPDIR:-/tmp}/copa.XXXXXX")" || { echo "mktemp failed" >&2; exit 1; }
    case "$dir" in */copa.??????) ;; *) echo "unexpected temporary folder '$dir'" >&2; exit 1 ;; esac
    printf '%s' "$dir"
}
