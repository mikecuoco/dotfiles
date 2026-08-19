#!/usr/bin/env bash
# Dirty-destination behaviour comparison.
#
# Clean-install parity is the easy half. What actually differentiates the two
# implementations is what happens when the destination already has content:
# app-managed config that must survive, and unmanaged files that must not be
# silently destroyed.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE=codeocean

seed() {
    local d="$1"
    mkdir -p "$d/.codex"
    # App-managed Codex config: comments and key order must survive.
    cat > "$d/.codex/config.toml" <<'EOF'
# Written by Codex itself -- do not lose this comment.
model = "gpt-5"

[history]
persistence = "save-all"
EOF
    # App-managed Claude config with an unrelated key.
    printf '{\n  "userID": "abc123",\n  "numStartups": 47\n}\n' > "$d/.claude.json"
    # Unmanaged dotfile that the installer wants to own.
    printf 'PRECIOUS USER CONTENT\n' > "$d/.gitconfig"
}

apply_old() { (cd "$REPO" && uv run dotfiles install --home "$1" --profile "$PROFILE" --quiet) >/dev/null 2>&1; }
apply_new() {
    local d="$1" ws; ws="$(mktemp -d)"
    chezmoi execute-template --init --promptString "profile=$PROFILE" \
        < "$REPO/home/.chezmoi.toml.tmpl" > "$ws/chezmoi.toml"
    chezmoi --source "$REPO" --destination "$d" --config "$ws/chezmoi.toml" \
            --persistent-state "$ws/state.boltdb" --cache "$ws/cache" apply >/dev/null 2>&1
    echo "$ws"   # caller may re-apply with the same workspace
}

report() {
    local label="$1" d="$2"
    echo "──────── $label ────────"
    echo "  [.codex/config.toml] app comment survived: $(grep -qF 'do not lose this comment' "$d/.codex/config.toml" && echo YES || echo 'NO  <-- DATA LOSS')"
    echo "  [.codex/config.toml] app key model= survived: $(grep -qE '^model = "gpt-5"' "$d/.codex/config.toml" && echo YES || echo 'NO  <-- DATA LOSS')"
    echo "  [.codex/config.toml] [history] table survived: $(grep -qF '[history]' "$d/.codex/config.toml" && echo YES || echo 'NO  <-- DATA LOSS')"
    echo "  [.codex/config.toml] managed block present:   $(grep -qF 'dotfiles managed Codex preferences' "$d/.codex/config.toml" && echo YES || echo NO)"
    echo "  [.codex/config.toml] valid TOML:              $(python3 -c "
import sys
try: import tomllib
except ModuleNotFoundError: import tomli as tomllib
tomllib.load(open('$d/.codex/config.toml','rb')); print('YES')
" 2>/dev/null || echo 'NO  <-- BROKEN')"
    echo "  [.claude.json] unrelated key userID survived: $(grep -q 'abc123' "$d/.claude.json" && echo YES || echo 'NO  <-- DATA LOSS')"
    echo "  [.claude.json] managed key set:               $(grep -q 'hasCompletedOnboarding' "$d/.claude.json" && echo YES || echo NO)"
    local bk; bk=$(find "$d" -maxdepth 1 -name '.gitconfig*backup*' | head -1)
    echo "  [.gitconfig] overwritten by dotfiles:         $([ -L "$d/.gitconfig" ] && echo YES || echo NO)"
    echo "  [.gitconfig] original preserved as backup:    $([ -n "$bk" ] && echo "YES ($(basename "$bk"))" || echo 'NO  <-- ORIGINAL LOST')"
    echo
}

O="$(mktemp -d)"; seed "$O"; apply_old "$O"; report "LEGACY installer" "$O"
N="$(mktemp -d)"; seed "$N"; WS=$(apply_new "$N"); report "CHEZMOI" "$N"

echo "──────── idempotency on dirty destination (chezmoi, 2nd apply) ────────"
before=$(shasum -a256 "$N/.codex/config.toml" | cut -d' ' -f1)
chezmoi --source "$REPO" --destination "$N" --config "$WS/chezmoi.toml" \
        --persistent-state "$WS/state.boltdb" --cache "$WS/cache" apply >/dev/null 2>&1
after=$(shasum -a256 "$N/.codex/config.toml" | cut -d' ' -f1)
[ "$before" = "$after" ] && echo "  ✓ config.toml stable across re-apply (no marker-block accretion)" \
                         || echo "  ✗ config.toml changed on re-apply"
echo "  managed-block count: $(grep -c 'dotfiles managed Codex preferences >>>' "$N/.codex/config.toml") (expect 1)"
echo
echo "──────── resulting .codex/config.toml (chezmoi) ────────"
sed 's/^/  /' "$N/.codex/config.toml" | head -35
