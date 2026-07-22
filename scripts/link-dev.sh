#!/usr/bin/env bash
#
# link-dev.sh — AUTHOR / CONTRIBUTOR DEV TOOL. This is NOT an end-user installer.
#
# Symlinks this repo's canonical skill (skills/sdd-workflow) into a tool's
# user-level skills directory so that edits to the repo take effect live while
# developing the skill. End users should install via their tool's native skill
# installer or a cross-agent skills manager (see README) — not this script.
#
# Usage:
#   scripts/link-dev.sh                 link into both Claude Code and Codex
#   scripts/link-dev.sh --claude-only   link into Claude Code only
#   scripts/link-dev.sh --codex-only    link into Codex only
#   scripts/link-dev.sh --unlink        remove dev links that this repo created
#   scripts/link-dev.sh --help
#
# Target dirs (override for hermetic testing or a verified Codex skill root):
#   Claude Code : ${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}
#   Codex       : ${CODEX_SKILLS_DIR:-${CODEX_HOME:-$HOME/.codex}/skills}
#
# Safety: only ever creates a symlink at a *non-existing* destination, and only
# ever removes a symlink that resolves to THIS repo's canonical skill. Any other
# existing file / directory / symlink is left untouched and reported.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CANONICAL="$(cd "$SCRIPT_DIR/../skills/sdd-workflow" && pwd -P)"
SKILL_NAME="sdd-workflow"

CLAUDE_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
CODEX_DIR="${CODEX_SKILLS_DIR:-${CODEX_HOME:-$HOME/.codex}/skills}"

DO_CLAUDE=1
DO_CODEX=1
MODE=link

usage() {
  cat <<'EOF'
link-dev.sh — AUTHOR / CONTRIBUTOR DEV TOOL (not an end-user installer)

Symlinks this repo's skills/sdd-workflow into a tool's user-level skills dir
for live development. End users: install via your tool's native skill
installer instead (see README).

Options:
  (none)          link into both Claude Code and Codex
  --claude-only   link into Claude Code only
  --codex-only    link into Codex only
  --unlink        remove dev links that resolve to this repo
  -h, --help      show this help

Target dirs (env-overridable, e.g. for hermetic testing):
  Claude Code : ${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}
  Codex       : ${CODEX_SKILLS_DIR:-${CODEX_HOME:-$HOME/.codex}/skills}
EOF
}

for arg in "$@"; do
  case "$arg" in
    --claude-only) DO_CODEX=0 ;;
    --codex-only)  DO_CLAUDE=0 ;;
    --unlink)      MODE=unlink ;;
    -h|--help)     usage; exit 0 ;;
    *) echo "unknown option: $arg" >&2; echo "run with --help" >&2; exit 2 ;;
  esac
done

# Resolve a path to its physical location, or print nothing if it doesn't resolve.
resolve() { (cd "$1" 2>/dev/null && pwd -P) || true; }

do_link() {
  local dest="$1" tool="$2"
  if [ -L "$dest" ]; then
    if [ "$(resolve "$dest")" = "$CANONICAL" ]; then
      echo "  [$tool] already linked: $dest"
      return 0
    fi
    echo "  [$tool] STOP: $dest is a symlink elsewhere ($(readlink "$dest")); not touching" >&2
    return 1
  fi
  if [ -e "$dest" ]; then
    echo "  [$tool] STOP: $dest already exists and is not our symlink; not overwriting" >&2
    return 1
  fi
  mkdir -p "$(dirname "$dest")"
  ln -s "$CANONICAL" "$dest"
  echo "  [$tool] linked: $dest -> $CANONICAL"
}

do_unlink() {
  local dest="$1" tool="$2"
  if [ -L "$dest" ] && [ "$(resolve "$dest")" = "$CANONICAL" ]; then
    rm "$dest"
    echo "  [$tool] unlinked: $dest"
    return 0
  fi
  if [ -L "$dest" ]; then
    echo "  [$tool] skip: $dest is a symlink elsewhere; not touching"
  elif [ -e "$dest" ]; then
    echo "  [$tool] skip: $dest is a real file/dir; not touching"
  else
    echo "  [$tool] nothing to unlink: $dest"
  fi
}

echo "link-dev.sh (author dev tool) — mode: $MODE"
echo "canonical skill: $CANONICAL"

rc=0
if [ "$DO_CLAUDE" = 1 ]; then
  if [ "$MODE" = link ]; then do_link "$CLAUDE_DIR/$SKILL_NAME" "claude" || rc=1
  else do_unlink "$CLAUDE_DIR/$SKILL_NAME" "claude"; fi
fi
if [ "$DO_CODEX" = 1 ]; then
  if [ "$MODE" = link ]; then do_link "$CODEX_DIR/$SKILL_NAME" "codex" || rc=1
  else do_unlink "$CODEX_DIR/$SKILL_NAME" "codex"; fi
fi
exit $rc
