#!/usr/bin/env bash
#
# Push the changed frontend files from THIS local machine to the EC2 instance,
# overwriting the remote copies. Run it from your local "demo/" project root:
#
#     bash deploy_to_ec2.sh            # copy the files
#     bash deploy_to_ec2.sh --build    # copy, then run "npm run build" on EC2
#     bash deploy_to_ec2.sh --dry-run  # show what WOULD be copied, change nothing
#
# You do NOT need to SSH in first — this script does the copy over SSH for you.
#
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# 1) EDIT THESE for your instance (fill in once).
# ─────────────────────────────────────────────────────────────────────────────
EC2_USER="ubuntu"                                   # ec2-user for Amazon Linux, ubuntu for Ubuntu
EC2_HOST="54.252.207.144"               # e.g. 13.234.56.78  or  ec2-...compute.amazonaws.com
SSH_KEY="$HOME/Downloads/alexa-key.pem"                  # path to your .pem key
REMOTE_DIR="/home/ubuntu/hackon_project/demo"      # the demo/ project root ON the EC2 box
# ─────────────────────────────────────────────────────────────────────────────

# The files this feature touches (paths are relative to the demo/ project root).
FILES=(
  "src/data/csvPredict.js"
  "src/data/sampleCsv.js"
  "src/ui/LearningPanel.js"
  "src/main.js"
  "src/data/ApiProvider.js"
  "src/data/DataLayer.js"
  "src/simulation/EventScheduler.js"
  "src/styles/panels.css"
)

# ─── sanity checks ───────────────────────────────────────────────────────────
cd "$(dirname "$0")"   # run from the project root (where this script lives)

if [ ! -f package.json ] || [ ! -d src ]; then
  echo "ERROR: run this from the demo/ project root (package.json + src/ must be here)." >&2
  exit 1
fi
if [ "$EC2_HOST" = "YOUR_EC2_PUBLIC_IP_OR_DNS" ]; then
  echo "ERROR: edit EC2_HOST / SSH_KEY / REMOTE_DIR at the top of this script first." >&2
  exit 1
fi
if [ ! -f "$SSH_KEY" ]; then
  echo "ERROR: SSH key not found: $SSH_KEY" >&2
  exit 1
fi
chmod 600 "$SSH_KEY" 2>/dev/null || true

# Verify the local files exist before touching the remote.
for f in "${FILES[@]}"; do
  [ -f "$f" ] || { echo "ERROR: local file missing: $f" >&2; exit 1; }
done

DRY=0
BUILD=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --build)   BUILD=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)
TARGET="${EC2_USER}@${EC2_HOST}"

echo "==> Target: ${TARGET}:${REMOTE_DIR}"
echo "==> Files:  ${#FILES[@]}"

# ─── copy ────────────────────────────────────────────────────────────────────
if command -v rsync >/dev/null 2>&1; then
  RSYNC_FLAGS=(-avR)                 # -R keeps the src/... directory structure
  [ "$DRY" -eq 1 ] && RSYNC_FLAGS+=(--dry-run)
  echo "==> Copying with rsync${DRY:+ (dry-run)}..."
  rsync "${RSYNC_FLAGS[@]}" -e "ssh ${SSH_OPTS[*]}" "${FILES[@]}" "${TARGET}:${REMOTE_DIR}/"
else
  echo "==> rsync not found, using scp..."
  for f in "${FILES[@]}"; do
    remote_path="${REMOTE_DIR}/${f}"
    if [ "$DRY" -eq 1 ]; then
      echo "    would copy  $f  ->  ${remote_path}"
    else
      # Ensure the remote subdirectory exists, then copy.
      ssh "${SSH_OPTS[@]}" "$TARGET" "mkdir -p \"$(dirname "$remote_path")\""
      scp "${SSH_OPTS[@]}" "$f" "${TARGET}:${remote_path}"
      echo "    copied  $f"
    fi
  done
fi

[ "$DRY" -eq 1 ] && { echo "==> Dry run complete. Nothing was changed."; exit 0; }

# ─── optional remote rebuild ─────────────────────────────────────────────────
if [ "$BUILD" -eq 1 ]; then
  echo "==> Building on EC2 (npm run build)..."
  ssh "${SSH_OPTS[@]}" "$TARGET" "cd \"$REMOTE_DIR\" && npm run build"
  echo "==> Remote build done. Serve the dist/ directory."
else
  echo "==> Files copied. To rebuild on EC2:"
  echo "      ssh -i \"$SSH_KEY\" ${TARGET} 'cd \"$REMOTE_DIR\" && npm run build'"
  echo "    (or re-run this script with --build)"
fi
