#!/usr/bin/env bash
#
# sdd-workflow installer
#
# Installs the propose / implement / archive commands into the two supported
# agent CLIs:
#
#   Claude Code (Anthropic)  ->  ~/.claude/commands/*.md   (full file, YAML frontmatter kept)
#   Codex (OpenAI/GPT)       ->  ~/.codex/prompts/*.md     (YAML frontmatter stripped)
#
# Both tools invoke the same slash commands: /propose, /implement, /archive.
#
# Usage:
#   ./install.sh                 install into both tools
#   ./install.sh --claude-only   install into Claude Code only
#   ./install.sh --codex-only    install into Codex only
#   ./install.sh --force         overwrite existing files (a .bak backup is kept)
#   ./install.sh --help          show this help
#
# Override target directories with env vars:
#   CLAUDE_COMMANDS_DIR=/path CODEX_PROMPTS_DIR=/path ./install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/commands"

CLAUDE_DIR="${CLAUDE_COMMANDS_DIR:-$HOME/.claude/commands}"
CODEX_DIR="${CODEX_PROMPTS_DIR:-$HOME/.codex/prompts}"

COMMANDS=(propose implement archive)

DO_CLAUDE=1
DO_CODEX=1
FORCE=0

usage() {
  sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

for arg in "$@"; do
  case "$arg" in
    --claude-only) DO_CODEX=0 ;;
    --codex-only)  DO_CLAUDE=0 ;;
    --force)       FORCE=1 ;;
    -h|--help)     usage; exit 0 ;;
    *) echo "unknown option: $arg" >&2; echo "run with --help" >&2; exit 2 ;;
  esac
done

# Strip a leading YAML frontmatter block (--- ... ---) from stdin.
strip_frontmatter() {
  awk '
    NR==1 && $0 ~ /^---[[:space:]]*$/ { infm=1; next }
    infm && $0 ~ /^---[[:space:]]*$/ { infm=0; skip_blanks=1; next }
    infm { next }
    skip_blanks && $0 ~ /^[[:space:]]*$/ { next }
    { skip_blanks=0; print }
  '
}

# Write $2 (content on stdin) to file $1, honoring FORCE and keeping a backup.
write_file() {
  local dest="$1"
  mkdir -p "$(dirname "$dest")"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ "$FORCE" != "1" ]; then
      echo "  skip (exists): $dest"
      echo "                 use --force to overwrite"
      cat >/dev/null   # drain stdin so the pipe doesn't error
      return
    fi
    cp -P "$dest" "$dest.bak"
    rm -f "$dest"
    echo "  backup:  $dest.bak"
  fi
  cat >"$dest"
  echo "  install: $dest"
}

if [ "$DO_CLAUDE" = "1" ]; then
  echo "Claude Code -> $CLAUDE_DIR"
  for c in "${COMMANDS[@]}"; do
    cat "$SRC_DIR/$c.md" | write_file "$CLAUDE_DIR/$c.md"
  done
fi

if [ "$DO_CODEX" = "1" ]; then
  echo "Codex       -> $CODEX_DIR"
  for c in "${COMMANDS[@]}"; do
    strip_frontmatter <"$SRC_DIR/$c.md" | write_file "$CODEX_DIR/$c.md"
  done
fi

echo "done. invoke with /propose, /implement, /archive"
