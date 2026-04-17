#!/usr/bin/env bash
# OpenBrain Apple Reminders MCP launcher.
# Uses mcp-server-apple-events (EventKit — Reminders.app does not need to be open).
# macOS will prompt for Reminders access on first run; grant it in
# System Settings > Privacy & Security > Reminders.
set -euo pipefail
# shellcheck source=_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

exec npx -y mcp-server-apple-events
