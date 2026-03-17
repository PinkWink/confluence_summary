#!/bin/bash
# Confluence daily summary -> Slack cron script
# Runs daily at 9 AM KST: summarizes previous day 9:00 ~ today 8:59

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/confluence_cron.log"

echo "[$(date)] Confluence daily summary started" >> "$LOG_FILE"
/usr/bin/python3 "$SCRIPT_DIR/confluence_slack_daily.py" >> "$LOG_FILE" 2>&1
echo "[$(date)] Confluence daily summary completed" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
