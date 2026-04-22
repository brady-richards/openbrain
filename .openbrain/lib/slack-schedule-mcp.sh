#!/usr/bin/env bash
# OpenBrain Slack Schedule MCP launcher.
# Exposes chat.scheduleMessage as an MCP tool.
# Usage: slack-schedule-mcp.sh <slug>
set -euo pipefail
# shellcheck source=_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

SLUG="${1:?usage: slack-schedule-mcp.sh <slug>}"

TOKEN_VAR="SLACK_TOKEN_$(echo "$SLUG" | tr '[:lower:]-' '[:upper:]_')"
TOKEN_VALUE="${!TOKEN_VAR:-}"

[[ -n "$TOKEN_VALUE" ]] || die "$TOKEN_VAR not set in $ENV_FILE (run bootstrap/lib/add-slack-workspace.sh $SLUG)"

export SLACK_MCP_XOXP_TOKEN="$TOKEN_VALUE"

SERVER_JS="$(dirname "${BASH_SOURCE[0]}")/slack-schedule-server.js"
[[ -f "$SERVER_JS" ]] || die "slack-schedule-server.js not found at $SERVER_JS — run bootstrap/lib/register-mcps.sh"

exec node "$SERVER_JS"
