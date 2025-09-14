#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--urls", required=True)
    p.add_argument("--limit", type=int, required=True)
    p.add_argument("--failure-strategy",
                   choices=["ignore", "error"], default="ignore")
    p.add_argument("--dry-run", default=False, action="store_true")
    p.add_argument("--message", default="{url}")
    return p.parse_args()


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

    cmd.append(message.format(url=url))

    return cmd


def main():
    args = parse_args()
    limit = int(os.getenv("INPUT_LIMIT", "0")) or None
    failure_strategy = os.getenv("INPUT_FAILURE_STRATEGY", "fail").lower()

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
