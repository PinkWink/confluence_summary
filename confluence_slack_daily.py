#!/usr/bin/env python3
"""
Confluence Daily Summary to Slack.
Runs daily at 9 AM KST: summarizes activity from previous day 9:00 AM to today 8:59 AM (KST).
- DM to yourself: excludes your own updates
- Team channel: includes all updates (yours included)
"""

import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, timezone
import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "confluence_token.txt")
SLACK_TOKEN_FILE = os.path.join(SCRIPT_DIR, "slack_token.txt")

SLACK_USER_ID = ""  # Your Slack user ID (e.g., "U04V2BC9KNW")
MY_NAME = ""  # Your Confluence display name (e.g., "John Doe")
CHANNEL_MEMBER = ""  # Target Slack channel ID (e.g., "C05BG4PUDMF")

KST = timezone(timedelta(hours=9))
UTC = timezone.utc


def load_confluence_config():
    config = {}
    with open(TOKEN_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                config[key] = value
    return config


def load_slack_token():
    with open(SLACK_TOKEN_FILE, "r") as f:
        return f.read().strip()


def get_updates_in_range(start_kst, end_kst, exclude_my_updates=True):
    """Query Confluence activity in the given KST time range.
    exclude_my_updates=True excludes your own edits, False includes all."""
    config = load_confluence_config()
    base_url = config["CONFLUENCE_URL"]
    auth = HTTPBasicAuth(config["CONFLUENCE_EMAIL"], config["CONFLUENCE_API_TOKEN"])

    # KST -> UTC for CQL query
    start_utc = start_kst.astimezone(UTC)
    end_utc = end_kst.astimezone(UTC)

    start_str = start_utc.strftime("%Y-%m-%d %H:%M")
    end_str = end_utc.strftime("%Y-%m-%d %H:%M")

    cql = f'lastModified >= "{start_str}" and lastModified < "{end_str}" order by lastModified asc'
    params = {
        "cql": cql,
        "limit": 200,
        "expand": "space,history,history.lastUpdated,version,ancestors",
    }

    resp = requests.get(f"{base_url}/wiki/rest/api/content/search", auth=auth, params=params)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for r in data.get("results", []):
        title = r.get("title", "")
        if r.get("type") == "attachment" or title.endswith((".png", ".jpg", ".gif")):
            continue

        space_name = r.get("space", {}).get("name", "?")
        space_key = r.get("space", {}).get("key", "?")
        version = r.get("version", {}).get("number", 1)
        updated_by = r.get("version", {}).get("by", {}).get("displayName", "?")
        created_by = r.get("history", {}).get("createdBy", {}).get("displayName", "?")
        last_updated_raw = r.get("version", {}).get("when", "?")[:19]

        try:
            utc_dt = datetime.strptime(last_updated_raw, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
            kst_dt = utc_dt.astimezone(KST)
            last_updated = kst_dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            last_updated = last_updated_raw

        page_url = f"{base_url}/wiki{r.get('_links', {}).get('webui', '')}"

        # Exclude own edits (optional)
        if exclude_my_updates and updated_by == MY_NAME:
            continue

        status = "New" if version == 1 else f"Updated (v{version})"

        results.append({
            "space_name": space_name,
            "space_key": space_key,
            "title": title,
            "status": status,
            "created_by": created_by,
            "updated_by": updated_by,
            "last_updated": last_updated,
            "url": page_url,
            "version": version,
        })

    return results


def generate_html(results, period_label, exclude_mine=True):
    """Generate an HTML summary file."""
    desc = "updated by others" if exclude_mine else "all updates"
    if not results:
        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>Confluence Summary - {period_label}</title></head>
<body style="font-family:sans-serif;background:#f5f7fa;padding:20px;">
<h1>Confluence Daily Summary - {period_label}</h1>
<p>No pages were {desc} during this period.</p>
</body></html>"""

    by_space = {}
    for r in results:
        key = f"{r['space_name']} ({r['space_key']})"
        by_space.setdefault(key, []).append(r)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Confluence Daily Summary - {period_label}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f7fa;
            color: #333;
            max-width: 960px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        .summary {{
            background: #eef6fb;
            border-radius: 6px;
            padding: 12px 18px;
            margin-bottom: 24px;
            font-size: 1.05em;
        }}
        .space-group {{
            background: #ffffff;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        .space-header {{
            background: #3498db;
            color: white;
            padding: 10px 18px;
            font-weight: 600;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #ecf0f1;
            text-align: left;
            padding: 8px 12px;
            font-size: 0.9em;
            color: #555;
        }}
        td {{
            padding: 8px 12px;
            border-top: 1px solid #eee;
        }}
        .badge-new {{
            background: #27ae60;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
        }}
        .badge-update {{
            background: #e67e22;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
        }}
        a {{
            color: #2980b9;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <h1>Confluence Daily Summary - {period_label}</h1>
    <div class="summary">Total <strong>{len(results)}</strong> pages {desc}.</div>
"""

    for space, pages in by_space.items():
        html += f"""    <div class="space-group">
        <div class="space-header">{space} ({len(pages)} pages)</div>
        <table>
            <tr><th>Status</th><th>Title</th><th>Author</th><th>Updated By</th><th>Time</th></tr>
"""
        for p in pages:
            badge_class = "badge-new" if p["version"] == 1 else "badge-update"
            time_str = p["last_updated"][11:] if "T" in p["last_updated"] else p["last_updated"]
            html += f"""            <tr>
                <td><span class="{badge_class}">{p['status']}</span></td>
                <td><a href="{p['url']}">{p['title']}</a></td>
                <td>{p['created_by']}</td>
                <td>{p['updated_by']}</td>
                <td>{time_str}</td>
            </tr>
"""
        html += """        </table>
    </div>
"""

    html += """</body>
</html>"""
    return html


def build_greeting_text(period_label, total_count, exclude_mine=True):
    """Build a short greeting message for the main channel/DM post."""
    desc = "updated by others" if exclude_mine else "all updates"
    if exclude_mine:
        greeting = ":sunrise: Good morning!"
    else:
        greeting = "Good morning! :wave:"

    if total_count == 0:
        return f"{greeting}\n\n*Confluence Daily Summary - {period_label}*\nNo pages were {desc} during this period."

    return (
        f"{greeting}\n"
        f"Here is yesterday's Confluence update summary.\n\n"
        f"*Confluence Daily Summary - {period_label}*\n"
        f"Total *{total_count}* pages {desc}. Please check the thread below for details."
    )


def build_slack_thread_chunks(results, max_chars=3500):
    """Build Slack thread reply text, split by space into chunks under max_chars."""
    if not results:
        return []

    by_space = {}
    for r in results:
        key = f"{r['space_name']} ({r['space_key']})"
        by_space.setdefault(key, []).append(r)

    chunks = []
    current_lines = []
    current_len = 0

    for space, pages in by_space.items():
        space_lines = [f"*{space}* ({len(pages)} pages)"]
        for p in pages:
            time_str = p["last_updated"][11:] if "T" in p["last_updated"] else p["last_updated"]
            emoji = ":new:" if p["version"] == 1 else ":arrows_counterclockwise:"
            space_lines.append(f"  {emoji} <{p['url']}|{p['title']}>")
            space_lines.append(f"      {p['status']} | Author: {p['created_by']} | Updated by: {p['updated_by']} | {time_str}")
        space_lines.append("")

        space_text = "\n".join(space_lines)
        space_len = len(space_text)

        if current_len + space_len > max_chars and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_len = 0

        current_lines.extend(space_lines)
        current_len += space_len

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks


def send_slack_dm(text, slack_token):
    """Send a Slack DM. Returns (channel_id, message_ts)."""
    resp = requests.post(
        "https://slack.com/api/conversations.open",
        headers={"Authorization": f"Bearer {slack_token}", "Content-Type": "application/json"},
        json={"users": SLACK_USER_ID},
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"conversations.open failed: {data.get('error')}")
    channel_id = data["channel"]["id"]

    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {slack_token}", "Content-Type": "application/json"},
        json={"channel": channel_id, "text": text, "mrkdwn": True},
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"chat.postMessage failed: {data.get('error')}")

    return channel_id, data["ts"]


def upload_file_to_thread(channel_id, thread_ts, file_path, slack_token):
    """Upload a file to a Slack thread (using files.uploadV2 API)."""
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    headers = {"Authorization": f"Bearer {slack_token}"}

    # Step 1: Get upload URL
    resp = requests.get(
        "https://slack.com/api/files.getUploadURLExternal",
        headers=headers,
        params={"filename": filename, "length": file_size},
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"files.getUploadURLExternal failed: {data.get('error')}")

    upload_url = data["upload_url"]
    file_id = data["file_id"]

    # Step 2: Upload file
    with open(file_path, "rb") as f:
        resp = requests.post(upload_url, files={"file": (filename, f, "text/html")})
        resp.raise_for_status()

    # Step 3: Complete upload and share to channel/thread
    resp = requests.post(
        "https://slack.com/api/files.completeUploadExternal",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "files": [{"id": file_id, "title": filename}],
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "initial_comment": "Detailed HTML summary file attached.",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"files.completeUploadExternal failed: {data.get('error')}")

    return data


def send_slack_channel(text, channel_id, slack_token):
    """Send a message to a Slack channel. Returns (channel_id, message_ts)."""
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {slack_token}", "Content-Type": "application/json"},
        json={"channel": channel_id, "text": text, "mrkdwn": True},
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"chat.postMessage failed: {data.get('error')}")

    return channel_id, data["ts"]


def send_slack_thread_reply(channel_id, thread_ts, text, slack_token):
    """Send a thread reply in Slack."""
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {slack_token}", "Content-Type": "application/json"},
        json={"channel": channel_id, "thread_ts": thread_ts, "text": text, "mrkdwn": True},
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"chat.postMessage (thread) failed: {data.get('error')}")
    return data["ts"]


def main():
    now_kst = datetime.now(KST)

    # Query range: previous day 09:00 KST ~ today 08:59 KST
    today_9am = now_kst.replace(hour=9, minute=0, second=0, microsecond=0)
    start_kst = today_9am - timedelta(days=1)
    end_kst = now_kst.replace(hour=8, minute=59, second=59, microsecond=0)

    start_label = start_kst.strftime("%m/%d %H:%M")
    end_label = end_kst.strftime("%m/%d %H:%M")
    period_label = f"{start_label} ~ {end_label}"
    date_str = start_kst.strftime("%Y-%m-%d")

    print(f"[{now_kst.strftime('%Y-%m-%d %H:%M:%S')}] Confluence daily summary started")
    print(f"  Range: {period_label} (KST)")

    slack_token = load_slack_token()

    # === 1. DM (excluding own updates) ===
    results_dm = get_updates_in_range(start_kst, end_kst, exclude_my_updates=True)
    print(f"  DM results: {len(results_dm)} pages (excluding own)")

    html_dm = generate_html(results_dm, period_label, exclude_mine=True)
    html_dm_filename = f"daily_summary_{date_str}.html"
    html_dm_path = os.path.join(SCRIPT_DIR, html_dm_filename)
    with open(html_dm_path, "w", encoding="utf-8") as f:
        f.write(html_dm)
    print(f"  DM HTML saved: {html_dm_path}")

    # DM: Send greeting as main message
    greeting_dm = build_greeting_text(period_label, len(results_dm), exclude_mine=True)
    dm_channel_id, dm_msg_ts = send_slack_dm(greeting_dm, slack_token)
    print(f"  Slack DM greeting sent (channel: {dm_channel_id})")

    # DM: Send details as thread replies (split into chunks)
    dm_chunks = build_slack_thread_chunks(results_dm)
    for i, chunk in enumerate(dm_chunks, 1):
        send_slack_thread_reply(dm_channel_id, dm_msg_ts, chunk, slack_token)
        print(f"  DM thread reply {i}/{len(dm_chunks)} sent")

    # DM: Attach HTML in thread
    upload_file_to_thread(dm_channel_id, dm_msg_ts, html_dm_path, slack_token)
    print(f"  DM HTML thread attached")

    # === 2. Team channel (all updates including own) ===
    results_all = get_updates_in_range(start_kst, end_kst, exclude_my_updates=False)
    print(f"  Channel results: {len(results_all)} pages (all)")

    html_all = generate_html(results_all, period_label, exclude_mine=False)
    html_all_filename = f"daily_summary_{date_str}_all.html"
    html_all_path = os.path.join(SCRIPT_DIR, html_all_filename)
    with open(html_all_path, "w", encoding="utf-8") as f:
        f.write(html_all)
    print(f"  Channel HTML saved: {html_all_path}")

    # Channel: Send greeting as main message
    greeting_ch = build_greeting_text(period_label, len(results_all), exclude_mine=False)
    ch_channel_id, ch_msg_ts = send_slack_channel(greeting_ch, CHANNEL_MEMBER, slack_token)
    print(f"  Team channel greeting sent (channel: {ch_channel_id})")

    # Channel: Send details as thread replies (split into chunks)
    ch_chunks = build_slack_thread_chunks(results_all)
    for i, chunk in enumerate(ch_chunks, 1):
        send_slack_thread_reply(ch_channel_id, ch_msg_ts, chunk, slack_token)
        print(f"  Channel thread reply {i}/{len(ch_chunks)} sent")

    # Channel: Attach HTML in thread
    upload_file_to_thread(ch_channel_id, ch_msg_ts, html_all_path, slack_token)
    print(f"  Channel HTML thread attached")

    print(f"[{datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}] Done!")


if __name__ == "__main__":
    main()
