#!/usr/bin/env bash
# OpenBrain iMessage MCP launcher.
# Uses imessage-mcp (https://github.com/anipotts/imessage-mcp) — reads
# ~/Library/Messages/chat.db directly via SQLite (read-only).
#
# Requires Full Disk Access for the terminal / Claude Code process:
#   System Settings → Privacy & Security → Full Disk Access → add Terminal (or Claude Code)
set -euo pipefail
# shellcheck source=_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

exec npx -y imessage-mcp
