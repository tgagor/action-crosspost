#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys

import requests
from bs4 import BeautifulSoup


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--urls", required=True)
    p.add_argument("--limit", type=int, required=True)
    p.add_argument("--failure-strategy", choices=["ignore", "error"], default="ignore")
    p.add_argument("--dry-run", default=False, action="store_true")
    p.add_argument("--message", default="{url}")
    return p.parse_args()


def extract_description(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"]
    except Exception as e:
        print(f"⚠️ Could not fetch description from {url}: {e}")
    return ""


def extract_og_tags(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        og_tags = set()
        for tag in soup.find_all("meta"):
            if tag.get("property", "").startswith("article:tag"):
                og_tags.add(tag.get("content", ""))
        og_tags = {t.lower() for t in og_tags if t}
        return og_tags
    except Exception as e:
        print(f"⚠️ Could not fetch OG tags from {url}: {e}")
    return {}


def message_needs_description(message):
    # Matches {description} with optional spaces inside the braces
    return re.search(r"\{ *description *\}", message) is not None


def message_needs_tags(message):
    # Matches {tags} with optional spaces inside the braces
    return re.search(r"\{ *tags *\}", message) is not None


def build_crosspost_cmd(message, url):
    cmd = ["npx", "crosspost"]

    # Twitter
    if (
        os.getenv("TWITTER_ACCESS_TOKEN_KEY")
        and os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    ) or (
        os.getenv("TWITTER_API_CONSUMER_KEY")
        and os.getenv("TWITTER_API_CONSUMER_SECRET")
    ):
        cmd.append("--twitter")

    # Mastodon
    if os.getenv("MASTODON_HOST") and os.getenv("MASTODON_ACCESS_TOKEN"):
        cmd.append("--mastodon")

    # Bluesky
    if (
        os.getenv("BLUESKY_HOST")
        and os.getenv("BLUESKY_IDENTIFIER")
        and os.getenv("BLUESKY_PASSWORD")
    ):
        cmd.append("--bluesky")

    # LinkedIn
    if os.getenv("LINKEDIN_ACCESS_TOKEN"):
        cmd.append("--linkedin")

    # Discord (bot)
    if os.getenv("DISCORD_BOT_TOKEN") and os.getenv("DISCORD_CHANNEL_ID"):
        cmd.append("--discord")

    # Discord (webhook)
    if os.getenv("DISCORD_WEBHOOK_URL"):
        cmd.append("--discord-webhook")

    # Dev.to
    if os.getenv("DEVTO_API_KEY"):
        cmd.append("--devto")

    # Telegram
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        cmd.append("--telegram")

    # Slack
    if os.getenv("SLACK_TOKEN") and os.getenv("SLACK_CHANNEL"):
        cmd.append("--slack")

    # Prepare description if needed
    description = ""
    if message_needs_description(message):
        description = extract_description(url)

    # Prepare og tags if needed
    if message_needs_tags(message):
        tags = extract_og_tags(url)
        if tags:
            # Format as hashtags
            tags = " ".join(sorted({f"#{t}" for t in tags if t}))
            message = re.sub(r"\{ *tags *\}", tags, message)
        else:
            message = re.sub(r"\{ *tags *\}", "", message)

    # Format message with url and description
    formatted_message = message.format(url=url, description=description)
    cmd.append(formatted_message)

    return cmd


def main():
    args = parse_args()
    limit = int(os.getenv("LIMIT", "0")) or None
    failure_strategy = os.getenv("FAILURE_STRATEGY", "ignore").lower()

    urls = args.urls.splitlines()
    if limit:
        urls = urls[:limit]

    # dry run: check if at least one network is configured
    test_cmd = build_crosspost_cmd(args.message, "https://example.com")
    if len(test_cmd) == 2:  # only ["npx", "crosspost", url]
        print("❌ No social network credentials provided. Aborting.")
        sys.exit(1)

    for url in urls:
        cmd = build_crosspost_cmd(args.message, url)
        if args.dry_run:
            print(f"✅ Would post {url} with command: {' '.join(cmd)}")
            continue
        print(f"🚀 Posting {url} ...")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to post {url}: {e}")
            if failure_strategy == "fail":
                sys.exit(1)
            else:
                continue


if __name__ == "__main__":
    main()
