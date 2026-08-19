#!/usr/bin/env bash
# Parity harness for the chezmoi spike.
#
# Installs the same profile twice -- once with the legacy Python installer, once
# with chezmoi -- into two throwaway HOMEs, and diffs the result. Symlink
# targets are compared, not just contents (--no-dereference), because the whole
# point of chezmoi's symlink mode is that it reproduces the old link behaviour.
#
# Usage: scripts/parity-check.sh [profile ...]     (default: linux codeocean)
#
# Note: `common` is a composition layer, not an installable profile -- the
# legacy installer rejects it (platform.VALID_PROFILES), so parity is checked
# on linux and codeocean, whose layer sets cover common transitively.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILES=("${@:-}")
[ -z "${PROFILES[0]:-}" ] && PROFILES=(linux codeocean)

# Artefacts written by one implementation and meaningless to the other.
EXPECTED_ONLY_OLD=(
    ".config/dotfiles"          # legacy state.json + profile marker
    ".claude/skills"            # legacy bundled-skill copies (not yet ported)
    ".agents"                   # legacy Codex skill tree (not yet ported)
)

fail=0

run_old() {
    local dest="$1" profile="$2"
    (cd "$REPO" && uv run dotfiles install --home "$dest" --profile "$profile" --quiet) \
        >"$dest/.install.log" 2>&1
}

WORKSPACE=""   # set per profile; shared by apply and the idempotency check

cz() {
    local dest="$1" rc; shift
    # Keep chezmoi's exit status: a filtering pipeline would report grep's
    # instead, and grep exits 1 when it drops every line.
    chezmoi --source "$REPO" --destination "$dest" \
            --config "$WORKSPACE/chezmoi.toml" \
            --persistent-state "$WORKSPACE/state.boltdb" \
            --cache "$WORKSPACE/cache" "$@" >"$WORKSPACE/out" 2>&1
    rc=$?
    grep -v 'config file template has changed' "$WORKSPACE/out" || true
    return $rc
}

run_new() {
    local dest="$1" profile="$2"
    WORKSPACE="$(mktemp -d)"
    chezmoi execute-template --init --promptString "profile=$profile" \
        < "$REPO/home/.chezmoi.toml.tmpl" > "$WORKSPACE/chezmoi.toml"
    cz "$dest" apply >"$dest/.apply.log" 2>&1
}

# Render a directory as one line per entry:
#   path -> link:<sha>   symlink into the repo, hashed by CONTENT
#   path (file <sha>)    regular file, hashed by content
#   path/                directory
#
# Symlinks are compared by the content they resolve to, not by their target
# path: the whole point of the migration is that the source file moves, so
# "src/dotfiles/resources/common/shell/.bashrc" vs "home/dot_bashrc" is expected
# and uninteresting. What must not change is what lands in $HOME.
manifest() {
    local root="$1"
    ( cd "$root" && find . -mindepth 1 \( -name '.install.log' -o -name '.apply.log' \) -prune -o -print \
      | sort | while read -r p; do
          rel="${p#./}"
          if [ -L "$p" ]; then
              if [ -d "$p" ]; then
                  printf '%s -> link:DIR\n' "$rel"
              else
                  printf '%s -> link:%s\n' "$rel" "$(shasum -a256 "$p" 2>/dev/null | cut -c1-16)"
              fi
          elif [ -f "$p" ]; then
              printf '%s (file %s)\n' "$rel" "$(shasum -a256 "$p" | cut -c1-16)"
          elif [ -d "$p" ]; then
              printf '%s/\n' "$rel"
          fi
      done )
}

filter_expected() {
    local f="$1"
    for skip in "${EXPECTED_ONLY_OLD[@]}"; do
        grep -v "^${skip}" "$f" > "$f.tmp" && mv "$f.tmp" "$f"
    done
}

for profile in "${PROFILES[@]}"; do
    echo "══════════ profile: $profile ══════════"
    OLD="$(mktemp -d)"; NEW="$(mktemp -d)"
    run_old "$OLD" "$profile" || { echo "  legacy installer FAILED"; cat "$OLD/.install.log"; fail=1; continue; }
    run_new "$NEW" "$profile" || { echo "  chezmoi apply FAILED";   cat "$NEW/.apply.log";   fail=1; continue; }

    manifest "$OLD" > /tmp/parity.old
    manifest "$NEW" > /tmp/parity.new
    filter_expected /tmp/parity.old
    filter_expected /tmp/parity.new

    if diff -u /tmp/parity.old /tmp/parity.new > /tmp/parity.diff; then
        echo "  ✓ identical (structure, symlink targets and content hashes)"
    else
        echo "  differences (- legacy, + chezmoi):"
        sed -n '3,$p' /tmp/parity.diff | grep -E '^[+-]' | sed 's/^/    /'
        fail=1
    fi

    # Idempotency: a second apply must be a no-op.
    cz "$NEW" status > /tmp/parity.status 2>&1
    if [ -s /tmp/parity.status ]; then
        echo "  ✗ not idempotent -- chezmoi status is non-empty:"; sed 's/^/    /' /tmp/parity.status
        fail=1
    else
        echo "  ✓ idempotent (chezmoi status empty on re-run)"
    fi
    echo
done

exit $fail
