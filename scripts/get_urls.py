#!/usr/bin/env python3
import argparse
import sys
import fnmatch
import requests
import os
from datetime import datetime, timedelta, timezone
from usp.tree import sitemap_tree_for_homepage


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--feed-url", required=True)
    p.add_argument("--since", type=int, required=True)
    p.add_argument("--since-unit", choices=["minutes", "hours", "days", "weeks"], required=True)
    p.add_argument("--exclude-urls", default="", help="Newline separated glob patterns")
    p.add_argument("--filter-urls", default="", help="Newline separated substrings")
    return p.parse_args()


def parse_since(since: int, unit: str) -> datetime:
    now = datetime.now(timezone.utc)
    delta_map = {"minutes": "minutes", "hours": "hours", "days": "days", "weeks": "weeks"}
    return now - timedelta(**{delta_map[unit]: since})


def fetch_feed(url: str):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def extract_urls(root_url: str, since_ago: datetime):
    """
    Fetch and parse sitemap(s) or RSS feeds, returning URLs modified since `since_ago`,
    sorted from freshest to oldest.
    """
    tree = sitemap_tree_for_homepage(root_url)
    results = []

    for page in tree.all_pages():
        url = page.url
        lastmod = page.lastmod  # this may be None if not available

        if lastmod:
            try:
                lm = datetime.fromisoformat(lastmod.strip().replace("Z", "+00:00"))
            except Exception:
                continue

            if lm > since_ago:
                results.append((lm, url))

    # sort newest -> oldest
    results.sort(key=lambda tup: tup[0], reverse=True)

    return [url for _, url in results]


def should_exclude(url: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(url, pat):
            return True
    return False


def should_filter(url: str, filters: list[str]) -> bool:
    if not filters:
        return True
    return any(f in url for f in filters)


def gha_output(name: str, value: str):
    """Append a multi-line output to GITHUB_OUTPUT file."""
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return  # running locally, just ignore
    with open(path, "a") as f:
        f.write(f"{name}<<EOF\n{value}\nEOF\n")


def main():
    args = parse_args()
    since_ago = parse_since(args.since, args.since_unit)
    xml = fetch_feed(args.feed_url)
    candidates = set(extract_urls(xml, since_ago))

    exclude_patterns = [p.strip() for p in args.exclude_urls.splitlines() if p.strip()]
    filter_patterns = [p.strip() for p in args.filter_urls.splitlines() if p.strip()]

    processed = []
    for url in sorted(candidates):
        if should_exclude(url, exclude_patterns):
            print(f"Excluding URL: {url}", file=sys.stderr)
            continue
        if not should_filter(url, filter_patterns):
            print(f"Skipping (no filter match): {url}", file=sys.stderr)
            continue
        print(f"Processing URL: {url}", file=sys.stderr)
        processed.append(url)

    # Output both lists for GitHub Actions
    gha_output("latest-urls", "\n".join(sorted(candidates)))
    gha_output("processed-urls", "\n".join(processed))


if __name__ == "__main__":
    main()
