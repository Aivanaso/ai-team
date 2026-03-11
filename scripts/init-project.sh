#!/usr/bin/env bash
#
# init-project.sh — Bootstrap .ai-team/ directory in a target project.
#
# Usage:
#   ./init-project.sh [target-directory]
#
# If no target directory is given, uses the current working directory.

set -euo pipefail

TARGET="${1:-.}"
AI_TEAM_DIR="$TARGET/.ai-team"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[ai-team]${NC} $1"; }
warn() { echo -e "${YELLOW}[ai-team]${NC} $1"; }

# Check if already initialized
if [ -d "$AI_TEAM_DIR" ]; then
    warn ".ai-team/ already exists in $TARGET"
    echo "  Run '/ai-team init' inside Claude Code to re-detect your stack."
    exit 0
fi

info "Initializing .ai-team/ in $TARGET"

# Create directory structure
mkdir -p "$AI_TEAM_DIR/specs"
mkdir -p "$AI_TEAM_DIR/changes/archive"
mkdir -p "$AI_TEAM_DIR/explorations"

info "Created directory structure"

# Create .gitignore for .ai-team/
cat > "$AI_TEAM_DIR/.gitignore" << 'EOF'
# ai-team .gitignore
#
# Specs and archive are committed (living documentation).
# Active changes are ignored (work in progress).

# Ignore active changes (work in progress)
/changes/*
# But keep the archive (completed changes)
!/changes/archive/

# Ignore explorations (ephemeral research)
/explorations/
EOF

info "Created .ai-team/.gitignore"

# Create placeholder files
touch "$AI_TEAM_DIR/specs/.gitkeep"
touch "$AI_TEAM_DIR/changes/archive/.gitkeep"

info "Initialization complete!"
echo ""
echo "  Next steps:"
echo "  1. Open the project in Claude Code"
echo "  2. Run '/ai-team init' to detect your stack"
echo "  3. Review the generated config.yaml"
echo ""
echo "  Directory: $AI_TEAM_DIR"
