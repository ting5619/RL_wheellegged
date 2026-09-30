#!/usr/bin/env bash
# Fetch the pinned MIT-licensed SCUT task source used by play_scut_policy.py.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
reference_dir="$project_root/references/scut_wheeled-legged_RL"
reference_sha=b8ff79f3df855faf9dc92f4a282bd80c42649466
if [[ ! -e "$reference_dir" ]]; then
    mkdir -p -- "$project_root/references"
    git clone --no-checkout --filter=blob:none https://github.com/scutrobotlab/wheeled-legged_RL.git "$reference_dir"
    git -C "$reference_dir" checkout --detach "$reference_sha"
fi
# Refuse to replace an existing checkout, its changes, or a partial clone.
if [[ ! -d "$reference_dir/.git" ]] || [[ "$(git -C "$reference_dir" rev-parse HEAD)" != "$reference_sha" ]]; then
    echo "SCUT checkout is missing or at a different commit: $reference_dir" >&2
    echo "Preserve existing work and inspect it before retrying; no files were replaced." >&2
    exit 1
fi
git -C "$reference_dir" diff --exit-code HEAD --
echo "SCUT task source verified: $reference_sha"
