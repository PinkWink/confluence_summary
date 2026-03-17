# Confluence Daily Summary to Slack

Automatically summarizes daily Confluence activity and delivers it to Slack — both as a personal DM and a team channel message.

## Features

- **Personal DM**: Sends a summary of pages created/updated by others (excludes your own edits)
- **Team Channel**: Sends a full summary including all updates (yours included) with a friendly greeting
- **HTML Report**: Generates a styled HTML summary file and attaches it as a thread reply
- **Cron Ready**: Includes a cron wrapper script for scheduled daily execution

## Setup

### 1. Confluence API Token

Copy the example and fill in your credentials:

```bash
cp confluence_token.txt.example confluence_token.txt
```

Edit `confluence_token.txt`:
```
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token
```

Generate your API token at: https://id.atlassian.com/manage-profile/security/api-tokens

### 2. Slack Bot Token

Copy the example and add your bot token:

```bash
cp slack_token.txt.example slack_token.txt
```

Your Slack bot needs these OAuth scopes:
- `chat:write` — Send messages
- `files:write` — Upload files
- `files:read` — Read files
- `im:write` — Open DM conversations

### 3. Configure the Script

Edit `confluence_slack_daily.py` and set these constants:

```python
SLACK_USER_ID = "U04XXXXXXXX"   # Your Slack user ID
MY_NAME = "Your Name"            # Your Confluence display name
CHANNEL_MEMBER = "C05XXXXXXXX"   # Target Slack channel ID
```

### 4. Install Dependencies

```bash
pip install requests
```

### 5. Schedule with Cron

```bash
chmod +x confluence_cron.sh

# Edit crontab
crontab -e

# Add this line to run daily at 9 AM
0 9 * * * /path/to/confluence_cron.sh
```

## Usage

### Automated (via cron)

The script runs daily at 9 AM and summarizes activity from the previous day 9:00 AM to today 8:59 AM (KST).

### Manual Run

```bash
python3 confluence_slack_daily.py
```

### CLI Tool (standalone query)

Query a specific date without sending to Slack:

```bash
# Console output
python3 confluence_daily_summary.py --date 2025-03-13 --my-name "Your Name"

# Generate HTML report
python3 confluence_daily_summary.py --date 2025-03-13 --my-name "Your Name" --html
```

## File Structure

```
├── confluence_slack_daily.py      # Main script (Slack DM + channel)
├── confluence_daily_summary.py    # CLI tool for manual queries
├── confluence_cron.sh             # Cron wrapper script
├── confluence_token.txt.example   # Confluence config template
├── slack_token.txt.example        # Slack token template
├── .gitignore                     # Excludes tokens and generated files
└── README.md
```

## How It Works

1. Queries the Confluence REST API using CQL for pages modified in the target time range
2. Filters out attachment pages and image files
3. Converts timestamps from UTC to KST
4. **DM**: Excludes pages where you are the last editor
5. **Channel**: Includes all pages with a greeting message
6. Sends text summary to Slack, then uploads the HTML report as a thread reply

## License

MIT
