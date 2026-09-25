#!/usr/bin/env bash
# Install these skills and their shared references into ~/.claude/.
#
#   ./install.sh            install everything, skipping anything already present
#   ./install.sh --force    overwrite existing copies (the old copy is moved to *.bak-<timestamp>)
#   ./install.sh --list     show what would be installed, change nothing
#
# Set CLAUDE_HOME to install somewhere other than ~/.claude.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_HOME:-$HOME/.claude}"
MODE="install"
case "${1:-}" in
  --force) MODE="force" ;;
  --list)  MODE="list" ;;
  "")      ;;
  *) echo "usage: $0 [--force|--list]" >&2; exit 1 ;;
esac

STAMP="$(date +%Y%m%d-%H%M%S)"
installed=0; skipped=0

# place <source path in repo> <destination path under $DEST>
place() {
  local src="$REPO/$1" dst="$DEST/$2"
  if [[ "$MODE" == "list" ]]; then
    echo "  $1  ->  $dst"; return
  fi
  if [[ -e "$dst" || -L "$dst" ]]; then
    if [[ "$MODE" != "force" ]]; then
      echo "  skip    $dst (exists; use --force to replace)"
      skipped=$((skipped + 1)); return
    fi
    mv "$dst" "$dst.bak-$STAMP"
    echo "  backup  $dst -> $dst.bak-$STAMP"
  fi
  mkdir -p "$(dirname "$dst")"
  if [[ -d "$src" ]]; then
    rsync -a --exclude .claude --exclude __pycache__ --exclude .DS_Store "$src/" "$dst/"
  else
    cp "$src" "$dst"
  fi
  echo "  add     $dst"
  installed=$((installed + 1))
}

echo "Installing into $DEST"
echo
echo "Skills:"
for dir in "$REPO"/skills/*/; do
  name="$(basename "$dir")"
  place "skills/$name" "skills/$name"
done

echo
echo "Shared references:"
place "references/latex_toolkit/tikz_rules.md"     "references/latex_toolkit/tikz_rules.md"
place "references/latex_toolkit/themes/neutral"   "references/latex_toolkit/themes/neutral"
place "references/rhetoric_of_decks"              "references/rhetoric_of_decks"
place "references/referee2_persona.md"            "references/referee2_persona.md"
place "references/voice/register-check.md"        "references/voice/register-check.md"
place "references/voice/voice-profile.template.md" "references/voice/voice-profile.template.md"

[[ "$MODE" == "list" ]] && exit 0

echo
echo "Done: $installed added, $skipped skipped."

echo
echo "Checking external tools:"
check() {
  if command -v "$1" >/dev/null 2>&1; then echo "  ok       $1"
  else echo "  MISSING  $1  ($2)"; fi
}
check python3   "needed by split-pdf and build-style-guide"
check pdftotext "needed by discussion-init and build-style-guide; macOS: brew install poppler"
check pdfinfo   "needed by discussion-init; comes with poppler"
check pdflatex  "needed by beautiful_deck; macOS: install MacTeX"
if python3 -c "import PyPDF2" >/dev/null 2>&1; then
  echo "  ok       PyPDF2"
else
  echo "  MISSING  PyPDF2  (needed by split-pdf; pip install PyPDF2)"
fi

echo
echo "Restart Claude Code (or open a new session) to pick up the new skills."
