#!/usr/bin/env python3
"""
Confluence daily activity summary (CLI tool).
Lists pages created or updated by others in a given date range.
Your own edits (by display name) are excluded, but pages you authored
that others updated are still included.
"""

import requests
from requests.auth import HTTPBasicAuth
import argparse
from datetime import datetime, timedelta, timezone
import os

TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "confluence_token.txt")


def load_config():
    config = {}
    with open(TOKEN_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                config[key] = value
    return config


def get_daily_updates(target_date, my_name="Your Name"):
    config = load_config()
    base_url = config["CONFLUENCE_URL"]
    auth = HTTPBasicAuth(config["CONFLUENCE_EMAIL"], config["CONFLUENCE_API_TOKEN"])

    next_date = (datetime.strptime(target_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    cql = f'lastModified >= "{target_date}" and lastModified < "{next_date}" order by lastModified asc'
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
        if r.get("type") == "attachment" or title.endswith(".png") or title.endswith(".jpg") or title.endswith(".gif"):
            continue

        space_name = r.get("space", {}).get("name", "?")
        space_key = r.get("space", {}).get("key", "?")
        version = r.get("version", {}).get("number", 1)
        updated_by = r.get("version", {}).get("by", {}).get("displayName", "?")
        created_by = r.get("history", {}).get("createdBy", {}).get("displayName", "?")
        last_updated_raw = r.get("version", {}).get("when", "?")[:19]
        try:
            utc_dt = datetime.strptime(last_updated_raw, "%Y-%m-%dT%H:%M:%S")
            kst_dt = utc_dt.replace(tzinfo=timezone.utc) + timedelta(hours=9)
            last_updated = kst_dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            last_updated = last_updated_raw
        page_url = f"{base_url}/wiki{r.get('_links', {}).get('webui', '')}"

        if updated_by == my_name:
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


def print_results(results, target_date):
    if not results:
        print(f"\nNo pages were updated by others on {target_date}.")
        return

    print(f"\n{'='*70}")
    print(f"  Confluence Activity Summary for {target_date}")
    print(f"  (Total: {len(results)} pages)")
    print(f"{'='*70}\n")

    by_space = {}
    for r in results:
        key = f"{r['space_name']} ({r['space_key']})"
        by_space.setdefault(key, []).append(r)

    for space, pages in by_space.items():
        print(f"  {space}")
        print(f"{'─'*50}")
        for p in pages:
            print(f"  [{p['status']}] {p['title']}")
            print(f"    Author: {p['created_by']} | Updated by: {p['updated_by']} | {p['last_updated']}")
            print(f"    {p['url']}")
            print()


def generate_html(results, target_date):
    if not results:
        return f"<p>No pages were updated by others on {target_date}.</p>"

    by_space = {}
    for r in results:
        key = f"{r['space_name']} ({r['space_key']})"
        by_space.setdefault(key, []).append(r)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Confluence Daily Summary - {target_date}</title>
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
    <h1>Confluence Daily Summary - {target_date}</h1>
    <div class="summary">Total <strong>{len(results)}</strong> pages were updated by others.</div>
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Confluence daily activity summary (others' updates)")
    parser.add_argument("--date", default=None, help="Target date (YYYY-MM-DD). Default: yesterday")
    parser.add_argument("--my-name", default="Your Name", help="Your Confluence display name")
    parser.add_argument("--html", action="store_true", help="Generate HTML output")
    parser.add_argument("--output", default=None, help="HTML output file path")
    args = parser.parse_args()

    if args.date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date = args.date

    results = get_daily_updates(target_date, args.my_name)
    print_results(results, target_date)

    if args.html:
        html_content = generate_html(results, target_date)
        output_path = args.output or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"daily_summary_{target_date}.html"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\nHTML file saved: {output_path}")
