#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from functools import lru_cache

import requests
from bs4 import BeautifulSoup


@lru_cache(maxsize=128)
def fetch_post(url):
    """Fetch and parse a URL, returning (resp, soup). Caches by URL."""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return resp, soup


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--urls", required=True)
    p.add_argument("--limit", type=int, required=True)
    p.add_argument("--failure-strategy", choices=["ignore", "error"], default="ignore")
    p.add_argument("--dry-run", default=False, action="store_true")
    p.add_argument("--message", default="{url}")
    return p.parse_args()


def post_webmention_to_endpoint(source, endpoint, target):
    """Send webmention to a specific endpoint."""
    data = {"source": source, "target": target}
    r = requests.post(endpoint, data=data, timeout=10)
    if r.status_code in (200, 201, 202):
        return True, f"Webmention sent via {endpoint}"
    else:
        return False, f"Webmention failed: {r.status_code} {r.text}"


def send_webmention(source, target):
    """Send a webmention from source to target by discovering endpoint. Returns (success, message)."""
    try:
        _, soup = fetch_post(target)
        endpoint = None
        for tag in soup.find_all(["link", "a"], rel=True):
            rels = tag.get("rel")
            if isinstance(rels, str):
                rels = rels.split()
            if rels and any(r.lower() == "webmention" for r in rels):
                endpoint = tag.get("href")
                if endpoint:
                    break
        if not endpoint:
            return False, f"No webmention endpoint found for {target}"
        endpoint = requests.compat.urljoin(target, endpoint)
        return post_webmention_to_endpoint(source, endpoint, target)
    except Exception as e:
        return False, f"Webmention error for {target}: {e}"


def notify_webmention_hosts(source_url, targets, endpoint=None, dry_run=False):
    """Send webmentions to a list of targets (shoot and forget).

    If endpoint is provided, send to that endpoint (e.g., Brid.gy).
    Otherwise, discover endpoint from each target.
    """
    for target in targets:
        print(f"🌐 Notifying webmention target: source={source_url} target={target}")
        if dry_run:
            print(f"✅ Would send webmention: source={source_url} target={target}")
            continue
        # Only check that source is deployed (fetchable)
        try:
            fetch_post(source_url)
        except Exception as e:
            print(
                f"⚠️ Could not fetch source {source_url} before notifying {target}: {e}"
            )
            continue
        if endpoint:
            success, msg = post_webmention_to_endpoint(source_url, endpoint, target)
        else:
            success, msg = send_webmention(source_url, target)
        if success:
            print(f"✅ {msg}")
        else:
            print(f"⚠️ {msg}")


def send_webmentions_to_external_links(source_url, dry_run=False):
    """Scan source post for external links in e-content and send webmentions to them."""
    try:
        _, soup = fetch_post(source_url)
        # Find e-content (IndieWeb microformat)
        e_content = soup.find(class_="e-content")
        if not e_content:
            print(
                f"ℹ️ No e-content found in {source_url}, skipping dynamic webmentions."
            )
            return
        # Find all external links
        links = set()
        for a in e_content.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and not href.startswith(source_url):
                links.add(href)
        if not links:
            print(f"ℹ️ No external links found in e-content of {source_url}.")
            return
        for target in sorted(links):
            print(
                f"🌐 Sending webmention to external link: source={source_url} target={target}"
            )
            if dry_run:
                print(f"✅ Would send webmention: source={source_url} target={target}")
                continue
            success, msg = send_webmention(source_url, target)
            if success:
                print(f"✅ {msg}")
            else:
                print(f"⚠️ {msg}")
    except Exception as e:
        print(f"⚠️ Error scanning {source_url} for dynamic webmentions: {e}")


def extract_description(url):
    try:
        _, soup = fetch_post(url)
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"]
    except Exception as e:
        print(f"⚠️ Could not fetch description from {url}: {e}")
    return ""


def extract_og_tags(url):
    try:
        _, soup = fetch_post(url)
        og_tags = set()
        for tag in soup.find_all("meta"):
            if tag.get("property", "").startswith("article:tag"):
                og_tags.add(tag.get("content", ""))
        og_tags = {t for t in og_tags if t}  # remove empty tags
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
            normalized_tags = {re.sub("[^0-9a-zA-Z]+", "", t) for t in tags}
            hashtags = " ".join(sorted({f"#{t}" for t in normalized_tags if t}))
            message = re.sub(r"\{ *tags *\}", hashtags, message)
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

    # Parse webmention configuration
    webmention_endpoint = os.getenv("WEBMENTION_ENDPOINT", "").strip()
    webmention_target_hosts = (
        os.getenv("WEBMENTION_TARGET_HOSTS", "").replace(",", " ").split()
    )
    webmention_target_hosts = [h.strip() for h in webmention_target_hosts if h.strip()]

    scan_content_enabled = (
        os.getenv("WEBMENTION_SCAN_CONTENT", "false").lower() == "true"
    )

    # Check if social networks are configured
    test_cmd = build_crosspost_cmd(args.message, "https://example.com")
    social_networks_enabled = len(test_cmd) > 2  # more than ["npx", "crosspost", url]

    # Check if webmentions are configured
    webmentions_enabled = bool(webmention_target_hosts) or scan_content_enabled

    # Abort only if neither social networks nor webmentions are configured
    if not social_networks_enabled and not webmentions_enabled:
        print("❌ No social networks or webmentions configured. Aborting.")
        sys.exit(1)

    for url in urls:
        # Crosspost to social networks (if configured)
        if social_networks_enabled:
            cmd = build_crosspost_cmd(args.message, url)
            if args.dry_run:
                print(f"✅ Would post {url} with command: {' '.join(cmd)}")
            else:
                print(f"🚀 Posting {url} ...")
                try:
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"⚠️ Failed to post {url}: {e}")
                    if failure_strategy == "fail":
                        sys.exit(1)
                    else:
                        # Continue with webmentions even if crosspost fails
                        pass

        # Send webmentions (if configured)
        if webmentions_enabled:
            if args.dry_run:
                # Shoot-and-forget webmentions
                if webmention_target_hosts:
                    notify_webmention_hosts(
                        url,
                        webmention_target_hosts,
                        endpoint=webmention_endpoint,
                        dry_run=True,
                    )
                # Dynamic webmentions (only if enabled)
                if scan_content_enabled:
                    send_webmentions_to_external_links(url, dry_run=True)
            else:
                # Shoot-and-forget webmentions
                if webmention_target_hosts:
                    notify_webmention_hosts(
                        url,
                        webmention_target_hosts,
                        endpoint=webmention_endpoint,
                        dry_run=False,
                    )
                # Dynamic webmentions (scan e-content for external links, only if enabled)
                if scan_content_enabled:
                    send_webmentions_to_external_links(url, dry_run=False)


if __name__ == "__main__":
    main()
